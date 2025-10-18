"""Base scraper class with common functionality."""
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from datetime import datetime
import time
from loguru import logger

class BaseScraper:
    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RocBot/1.0 (Rochester Events Aggregator; Educational Project)'
        })
    
    def fetch_page(self, url: str, delay: float = 1.0) -> Optional[BeautifulSoup]:
        """Fetch and parse a webpage."""
        try:
            time.sleep(delay)  # Respectful scraping
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'lxml')
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def scrape(self) -> List[Dict]:
        """Override this method in child classes."""
        raise NotImplementedError