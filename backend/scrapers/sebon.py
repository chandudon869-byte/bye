from .base import BaseScraper
from bs4 import BeautifulSoup

class SEBONScraper(BaseScraper):
    """Scraper for SEBON IPO pipeline data"""
    
    def scrape(self):
        """Fetch IPO pipeline from SEBON"""
        results = {
            'pipeline': [],
            'approved': []
        }
        
        # SEBON's IPO pipeline page
        urls = [
            'https://sebon.gov.np/public-issues/ipo-pipeline',
            'https://sebon.gov.np/public-issues/ipo-approved'
        ]
        
        for url in urls:
            response = self.fetch_page(url)
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find tables (adjust selectors based on actual HTML)
                tables = soup.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows[1:]:  # Skip header
                        cells = row.find_all('td')
                        if len(cells) >= 2:
                            company = cells[0].get_text(strip=True)
                            if company:
                                item = {
                                    'company': company,
                                    'details': cells[1].get_text(strip=True) if len(cells) > 1 else '',
                                    'approved': 'approved' in url
                                }
                                if item['approved']:
                                    results['approved'].append(item)
                                else:
                                    results['pipeline'].append(item)
        
        return results