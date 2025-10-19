"""Full website crawler for City of Rochester."""
from typing import Dict, List, Set
from datetime import datetime
from loguru import logger
from urllib.parse import urljoin, urlparse
from .base_scraper import BaseScraper
import re
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.database.db_manager import save_scraped_data_to_db


class FullSiteScraper(BaseScraper):
    """Crawls entire cityofrochester.gov website and extracts all content."""
    
    def __init__(self, max_pages: int = 200, seed_urls: List[str] = None):
        super().__init__(
            name="City of Rochester Full Site Crawler",
            base_url="https://www.cityofrochester.gov"
        )
        self.max_pages = max_pages
        self.visited_urls: Set[str] = set()
        # --- NEW: Use seed URLs if provided ---
        self.to_visit: List[str] = seed_urls if seed_urls else [self.base_url]
        self.all_content: List[Dict] = []
        
    def scrape(self) -> List[Dict]:
        """Crawl the entire website."""
        logger.info(f"Starting full site crawl of {self.base_url}")
        logger.info(f"Max pages to crawl: {self.max_pages}")
        
        while self.to_visit and len(self.visited_urls) < self.max_pages:
            current_url = self.to_visit.pop(0)
            
            # Skip if already visited
            if current_url in self.visited_urls:
                continue
                
            # Only crawl cityofrochester.gov pages
            if not self._is_valid_url(current_url):
                continue
            
            logger.info(f"Crawling ({len(self.visited_urls) + 1}/{self.max_pages}): {current_url}")
            
            # Fetch and parse page
            soup = self.fetch_page(current_url, delay=1.5)
            if not soup:
                self.visited_urls.add(current_url)
                continue
            
            # Extract content from this page
            page_content = self._extract_page_content(current_url, soup)
            if page_content:
                self.all_content.append(page_content)
            
            # Find all links on this page
            new_links = self._extract_links(current_url, soup)
            for link in new_links:
                if link not in self.visited_urls and link not in self.to_visit:
                    self.to_visit.append(link)
            
            # Mark as visited
            self.visited_urls.add(current_url)
        
        logger.info(f"Crawl complete! Visited {len(self.visited_urls)} pages")
        logger.info(f"Extracted {len(self.all_content)} content items")
        
        # Save to database
        logger.info("Saving scraped content to database...")
        saved_count = save_scraped_data_to_db(self.all_content)
        logger.info(f"✅ Saved {saved_count} items to database")
        
        return self.all_content
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL should be crawled."""
        parsed = urlparse(url)
        
        # Must be cityofrochester.gov
        if 'cityofrochester.gov' not in parsed.netloc:
            return False
        
        # Skip files
        skip_extensions = ['.pdf', '.jpg', '.png', '.gif', '.zip', '.doc', '.xls']
        if any(url.lower().endswith(ext) for ext in skip_extensions):
            return False
        
        # Skip admin/login pages
        skip_paths = ['/user/', '/admin/', '/login', '/logout']
        if any(skip in url.lower() for skip in skip_paths):
            return False
        
        return True
    
    def _extract_links(self, current_url: str, soup) -> List[str]:
        """Extract all valid links from a page."""
        links = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            
            # Convert relative URLs to absolute
            absolute_url = urljoin(current_url, href)
            
            # Remove fragments (#section)
            absolute_url = absolute_url.split('#')[0]
            
            # Remove query parameters for duplicate prevention
            absolute_url = absolute_url.split('?')[0]
            
            if self._is_valid_url(absolute_url):
                links.append(absolute_url)
        
        return links
    
    def _extract_page_content(self, url: str, soup) -> Dict:
        """Extract all meaningful content from a page."""
        
        # Try to find the main content area
        main_content = (
            soup.find('main') or 
            soup.find('article') or 
            soup.find('div', {'id': 'content'}) or
            soup.find('div', {'class': 'content'}) or
            soup.body
        )
        
        if not main_content:
            return None
        
        # Extract title
        title = self._extract_title(soup)
        
        # Extract all text content
        text_content = self._extract_text(main_content)
        
        # Skip if no meaningful content
        if len(text_content) < 100:
            return None
        
        # Determine category based on URL
        category = self._determine_category(url)
        
        # Extract metadata
        metadata = self._extract_metadata(soup, url)
        
        return {
            'source': 'cityofrochester',
            'category': category,
            'type': 'page',
            'title': title,
            'url': url,
            'content_full': text_content,
            'description': text_content[:300] + '...' if len(text_content) > 300 else text_content,
            'scraped_at': datetime.now().isoformat(),
            'meta_data': metadata
        }
    
    def _extract_title(self, soup) -> str:
        """Extract page title."""
        # Try multiple strategies
        title = None
        
        # Strategy 1: <h1> tag
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)
        
        # Strategy 2: <title> tag
        if not title or len(title) < 3:
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
                # Remove site name if present
                title = title.split('|')[0].strip()
        
        return title or "Untitled Page"
    
    def _extract_text(self, element) -> str:
        """Extract clean text from HTML element."""
        # Remove script and style elements
        for script in element(['script', 'style', 'nav', 'footer', 'header']):
            script.decompose()
        
        # Get text
        text = element.get_text(separator=' ', strip=True)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _determine_category(self, url: str) -> str:
        """Determine content category from URL."""
        url_lower = url.lower()
        
        if '/news' in url_lower:
            return 'news'
        elif '/events' in url_lower:
            return 'events'
        elif '/departments' in url_lower:
            return 'departments'
        elif '/services' in url_lower or '/permits' in url_lower or '/licenses' in url_lower:
            return 'services'
        elif '/meetings' in url_lower or '/council' in url_lower:
            return 'government'
        elif '/jobs' in url_lower or '/employment' in url_lower:
            return 'employment'
        elif '/parks' in url_lower or '/recreation' in url_lower:
            return 'recreation'
        elif '/business' in url_lower:
            return 'business'
        else:
            return 'general'
    
    def _extract_metadata(self, soup, url: str) -> Dict:
        """Extract metadata from page."""
        metadata = {
            'url_path': urlparse(url).path,
            'tags': []
        }
        
        # Extract meta description
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            metadata['meta_description'] = meta_desc['content']
        
        # Extract keywords
        meta_keywords = soup.find('meta', {'name': 'keywords'})
        if meta_keywords and meta_keywords.get('content'):
            metadata['tags'] = [k.strip() for k in meta_keywords['content'].split(',')]
        
        # Add URL-based tags
        path_parts = urlparse(url).path.split('/')
        metadata['tags'].extend([p for p in path_parts if p and len(p) > 2])
        
        return metadata