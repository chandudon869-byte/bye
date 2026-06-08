from abc import ABC, abstractmethod
import requests
from bs4 import BeautifulSoup
import cloudscraper
import logging

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Base scraper class with common functionality"""
    
    def __init__(self):
        self.scraper = cloudscraper.create_scraper()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    
    @abstractmethod
    def scrape(self):
        """Main scraping method to be implemented"""
        pass
    
    def fetch_page(self, url):
        """Fetch a page with retry logic"""
        for attempt in range(3):
            try:
                response = self.scraper.get(url, headers=self.headers, timeout=15)
                response.raise_for_status()
                return response
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt == 2:
                    raise
        return None