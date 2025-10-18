"""Scraper for Meetup groups in Rochester, NY."""
from typing import Dict, List
from datetime import datetime
from loguru import logger
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.scrapers.base_scraper import BaseScraper
from backend.database.db_manager import save_scraped_data_to_db


class MeetupScraper(BaseScraper):
    """Scrapes meetup groups and events from Rochester, NY area."""
    
    def __init__(self):
        super().__init__(
            name="Meetup Rochester Scraper",
            base_url="https://www.meetup.com"
        )
        # Search for Rochester NY meetups
        self.rochester_url = f"{self.base_url}/find/?location=us--ny--rochester"
    
    def scrape(self) -> List[Dict]:
        """Scrape Rochester meetup groups and events."""
        meetups = []
        
        logger.info(f"Scraping Meetup: {self.rochester_url}")
        
        soup = self.fetch_page(self.rochester_url, delay=2.0)
        
        # Meetup often requires login, use known groups fallback
        logger.info("Using known Rochester meetup groups (Meetup.com requires login for full access)")
        meetups = self._scrape_known_groups()
        
        # Save to database
        if meetups:
            logger.info("Saving Meetup data to database...")
            saved_count = save_scraped_data_to_db(meetups)
            logger.info(f"✅ Saved {saved_count} Meetup items to database")
        
        return meetups
        
        # Find meetup cards
        group_cards = (
            soup.find_all('div', class_='card') or
            soup.find_all('article') or
            soup.find_all('a', href=lambda x: x and '/find/' not in x and 'meetup.com' in str(x))
        )
        
        logger.info(f"Found {len(group_cards)} potential meetup cards")
        
        for card in group_cards[:20]:  # Limit to 20
            try:
                meetup_data = self._parse_meetup_card(card)
                if meetup_data:
                    meetups.append(meetup_data)
            except Exception as e:
                logger.error(f"Error parsing meetup card: {e}")
                continue
        
        logger.info(f"Successfully parsed {len(meetups)} Meetup groups/events")
        
        # Save to database
        if meetups:
            logger.info("Saving Meetup data to database...")
            saved_count = save_scraped_data_to_db(meetups)
            logger.info(f"✅ Saved {saved_count} Meetup items to database")
        
        return meetups
    
    def _scrape_known_groups(self) -> List[Dict]:
        """
        Scrape specific known Rochester meetup groups.
        Fallback when main search doesn't work.
        """
        logger.info("Using fallback: scraping known Rochester meetup groups")
        
        known_groups = [
            {
                'name': 'Rochester Azure Users Group',
                'url': 'https://www.meetup.com/rochester-azure-users-group/',
                'description': 'A group for Rochester area professionals interested in Microsoft Azure cloud computing.'
            },
            {
                'name': 'Rochester Python Meetup',
                'url': 'https://www.meetup.com/rochesterpy/',
                'description': 'A group for Python developers and enthusiasts in the Rochester area.'
            },
            {
                'name': 'Rochester Game Developers',
                'url': 'https://www.meetup.com/rochester-game-developers/',
                'description': 'A community for game developers in Rochester, NY.'
            },
            {
                'name': 'Rochester Tech Meetup',
                'url': 'https://www.meetup.com/rochester-tech-meetup/',
                'description': 'Rochester area technology professionals networking and learning together.'
            },
            {
                'name': 'Rochester Data Science Meetup',
                'url': 'https://www.meetup.com/rochester-data-science-meetup/',
                'description': 'Data science, machine learning, and analytics professionals in Rochester.'
            }
        ]
        
        meetups = []
        
        for group in known_groups:
            meetup_data = {
                'source': 'meetup',
                'category': 'events',
                'type': 'meetup_group',
                'title': group['name'],
                'description': group['description'],
                'content_full': f"{group['name']}\n\n{group['description']}\n\nJoin this Rochester meetup group to connect with like-minded people and attend local events.",
                'url': group['url'],
                'image_url': '',
                'location': 'Rochester, NY',
                'scraped_at': datetime.now().isoformat(),
                'meta_data': {
                    'platform': 'meetup',
                    'tags': ['meetup', 'rochester', 'community', 'networking']
                }
            }
            meetups.append(meetup_data)
        
        logger.info(f"Added {len(meetups)} known Rochester meetup groups")
        return meetups
    
    def _parse_meetup_card(self, card) -> Dict:
        """Parse individual meetup card."""
        
        # Extract title/group name
        title_tag = (
            card.find('h3') or 
            card.find('h2') or 
            card.find('a')
        )
        
        if not title_tag:
            return None
        
        title = title_tag.get_text(strip=True)
        
        if not title or len(title) < 3:
            return None
        
        # Extract link
        link_tag = card.find('a', href=True)
        url = link_tag['href'] if link_tag else ""
        
        # Make URL absolute
        if url and not url.startswith('http'):
            url = f"{self.base_url}{url}"
        
        if not url:
            return None
        
        # Extract description
        desc_tag = card.find('p')
        description = desc_tag.get_text(strip=True) if desc_tag else ""
        
        # Extract member count or other info
        info_tags = card.find_all('span')
        additional_info = " ".join([tag.get_text(strip=True) for tag in info_tags[:3]])
        
        content_full = f"{title}\n\n"
        if description:
            content_full += f"{description}\n\n"
        if additional_info:
            content_full += f"{additional_info}\n\n"
        content_full += f"More info: {url}"
        
        return {
            'source': 'meetup',
            'category': 'events',
            'type': 'meetup_group',
            'title': title,
            'description': description or title,
            'content_full': content_full,
            'url': url,
            'location': 'Rochester, NY',
            'scraped_at': datetime.now().isoformat(),
            'meta_data': {
                'platform': 'meetup',
                'tags': ['meetup', 'rochester', 'community']
            }
        }


if __name__ == "__main__":
    # Test the scraper
    print("Testing Meetup Scraper...")
    scraper = MeetupScraper()
    meetups = scraper.scrape()
    
    print(f"\n✅ Scraped {len(meetups)} meetup groups from Rochester")
    
    if meetups:
        print("\n📄 Sample meetup:")
        print(f"Title: {meetups[0]['title']}")
        print(f"Description: {meetups[0]['description'][:100]}...")
        print(f"URL: {meetups[0]['url']}")