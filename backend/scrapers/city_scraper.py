"""Scraper for City of Rochester website."""
from typing import Dict, List
from datetime import datetime
from loguru import logger
from .base_scraper import BaseScraper


class CityNewsScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            name="City of Rochester News",
            base_url="https://www.cityofrochester.gov"
        )
    
    def scrape(self) -> List[Dict]:
        """Scrape news from City of Rochester."""
        news_items = []
        
        # Scrape news page
        news_url = f"{self.base_url}/news"
        soup = self.fetch_page(news_url)
        
        if not soup:
            logger.warning("Failed to fetch news page")
            return news_items
        
        # Find news articles
        articles = soup.find_all('article', limit=20)
        
        logger.info(f"Found {len(articles)} news articles")
        
        for article in articles:
            try:
                item = self._parse_news_article(article)
                if item:
                    news_items.append(item)
            except Exception as e:
                logger.error(f"Error parsing article: {e}")
                continue
        
        return news_items
    
    def _parse_news_article(self, article) -> Dict:
        """Parse individual news article."""
        # Find title
        title_tag = article.find('h2') or article.find('h3') or article.find('a')
        title = title_tag.get_text(strip=True) if title_tag else "No Title"
        
        # Find link
        link_tag = article.find('a', href=True)
        url = link_tag['href'] if link_tag else ""
        if url and not url.startswith('http'):
            url = f"{self.base_url}{url}"
        
        # Find description
        desc_tag = article.find('p') or article.find('div', class_='description')
        description = desc_tag.get_text(strip=True) if desc_tag else ""
        
        # Find date
        date_tag = article.find('time') or article.find('span', class_='date')
        date_str = date_tag.get_text(strip=True) if date_tag else ""
        
        # Find image
        img_tag = article.find('img')
        image_url = img_tag.get('src', '') if img_tag else ""
        if image_url and not image_url.startswith('http'):
            image_url = f"{self.base_url}{image_url}"
        
        return {
            'source': 'cityofrochester',
            'category': 'news',
            'type': 'news',
            'title': title,
            'description': description,
            'content_full': description,
            'url': url,
            'image_url': image_url,
            'date_published': date_str,
            'scraped_at': datetime.now().isoformat(),
            'metadata': {
                'department': 'Communications',
                'tags': ['news', 'rochester', 'city']
            }
        }


class CityEventsScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            name="City of Rochester Events",
            base_url="https://www.cityofrochester.gov"
        )
    
    def scrape(self) -> List[Dict]:
        """Scrape events from City of Rochester."""
        events = []
        
        events_url = f"{self.base_url}/events"
        soup = self.fetch_page(events_url)
        
        if not soup:
            logger.warning("Failed to fetch events page")
            return events
        
        # Find event items
        event_items = soup.find_all('article', limit=30)
        
        logger.info(f"Found {len(event_items)} events")
        
        for event in event_items:
            try:
                item = self._parse_event(event)
                if item:
                    events.append(item)
            except Exception as e:
                logger.error(f"Error parsing event: {e}")
                continue
        
        return events
    
    def _parse_event(self, event) -> Dict:
        """Parse individual event."""
        title_tag = event.find('h2') or event.find('h3') or event.find('a')
        title = title_tag.get_text(strip=True) if title_tag else "No Title"
        
        link_tag = event.find('a', href=True)
        url = link_tag['href'] if link_tag else ""
        if url and not url.startswith('http'):
            url = f"{self.base_url}{url}"
        
        desc_tag = event.find('p')
        description = desc_tag.get_text(strip=True) if desc_tag else ""
        
        # Date and time
        date_tag = event.find('time') or event.find('span', class_='date')
        date_str = date_tag.get('datetime', '') or date_tag.get_text(strip=True) if date_tag else ""
        
        # Location
        location_tag = event.find('span', class_='location') or event.find('address')
        location = location_tag.get_text(strip=True) if location_tag else "Rochester, NY"
        
        return {
            'source': 'cityofrochester',
            'category': 'events',
            'type': 'event',
            'title': title,
            'description': description,
            'content_full': description,
            'date_start': date_str,
            'location': location,
            'url': url,
            'scraped_at': datetime.now().isoformat(),
            'metadata': {
                'tags': ['event', 'rochester', 'city']
            }
        }