"""Scraper for Eventbrite Rochester events."""
from typing import Dict, List
from datetime import datetime
from loguru import logger
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.scrapers.base_scraper import BaseScraper
from backend.database.db_manager import save_scraped_data_to_db


class EventbriteScraper(BaseScraper):
    """Scrapes events from Eventbrite for Rochester, NY."""
    
    def __init__(self):
        super().__init__(
            name="Eventbrite Rochester Scraper",
            base_url="https://www.eventbrite.com"
        )
        self.rochester_url = f"{self.base_url}/d/ny--rochester/events/"
    
    def scrape(self) -> List[Dict]:
        """Scrape Rochester events from Eventbrite."""
        events = []
        
        logger.info(f"Scraping Eventbrite: {self.rochester_url}")
        
        soup = self.fetch_page(self.rochester_url, delay=2.0)
        
        if not soup:
            logger.error("Failed to fetch Eventbrite page")
            return events
        
        # Find event cards
        # Eventbrite uses different class names, we'll try multiple selectors
        event_cards = (
            soup.find_all('div', class_='discover-search-desktop-card') or
            soup.find_all('article') or
            soup.find_all('div', class_='event-card') or
            soup.find_all('a', class_='event-card-link')
        )
        
        logger.info(f"Found {len(event_cards)} potential event cards")
        
        for card in event_cards[:30]:  # Limit to 30 events
            try:
                event_data = self._parse_event_card(card)
                if event_data:
                    events.append(event_data)
            except Exception as e:
                logger.error(f"Error parsing event card: {e}")
                continue
        
        logger.info(f"Successfully parsed {len(events)} Eventbrite events")
        
        # Save to database
        if events:
            logger.info("Saving Eventbrite events to database...")
            saved_count = save_scraped_data_to_db(events)
            logger.info(f"✅ Saved {saved_count} Eventbrite events to database")
        
        return events
    
    def _parse_event_card(self, card) -> Dict:
        """Parse individual event card."""
        
        # Extract title
        title_tag = (
            card.find('h3') or 
            card.find('h2') or 
            card.find('div', class_='event-card__title') or
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
            url = self.rochester_url  # Fallback
        
        # Extract date/time
        date_tag = (
            card.find('time') or
            card.find('div', class_='event-card__date') or
            card.find('p', class_='date')
        )
        date_str = ""
        if date_tag:
            date_str = date_tag.get('datetime', '') or date_tag.get_text(strip=True)
        
        # Extract location
        location_tag = (
            card.find('p', class_='location') or
            card.find('div', class_='event-card__location') or
            card.find('span', class_='location-info')
        )
        location = location_tag.get_text(strip=True) if location_tag else "Rochester, NY"
        
        # Extract description/summary
        desc_tag = card.find('p', class_='summary') or card.find('div', class_='event-card__description')
        description = desc_tag.get_text(strip=True) if desc_tag else ""
        
        # Extract image
        img_tag = card.find('img')
        image_url = ""
        if img_tag:
            image_url = img_tag.get('src', '') or img_tag.get('data-src', '')
        
        # Build full content
        content_full = f"{title}\n\n"
        if description:
            content_full += f"{description}\n\n"
        content_full += f"Date: {date_str}\n"
        content_full += f"Location: {location}\n"
        content_full += f"More info: {url}"
        
        return {
            'source': 'eventbrite',
            'category': 'events',
            'type': 'event',
            'title': title,
            'description': description or title,
            'content_full': content_full,
            'url': url,
            'image_url': image_url,
            'date_start': date_str,
            'location': location,
            'scraped_at': datetime.now().isoformat(),
            'meta_data': {
                'platform': 'eventbrite',
                'tags': ['event', 'rochester', 'eventbrite']
            }
        }


if __name__ == "__main__":
    # Test the scraper
    print("Testing Eventbrite Scraper...")
    scraper = EventbriteScraper()
    events = scraper.scrape()
    
    print(f"\n✅ Scraped {len(events)} events from Eventbrite")
    
    if events:
        print("\n📄 Sample event:")
        print(f"Title: {events[0]['title']}")
        print(f"Date: {events[0]['date_start']}")
        print(f"Location: {events[0]['location']}")
        print(f"URL: {events[0]['url']}")