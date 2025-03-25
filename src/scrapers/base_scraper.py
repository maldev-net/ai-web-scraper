from abc import ABC, abstractmethod
from typing import List, Optional
from playwright.async_api import Page
from src.models.business import Business
import logging

class BaseScraper(ABC):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def scrape(self, page: Page, search_params: dict) -> List[Business]:
        """Main scraping method to be implemented by each scraper"""
        pass
    
    async def safe_get_text(self, page: Page, selector: str) -> Optional[str]:
        """Safely extract text from an element"""
        try:
            element = await page.query_selector(selector)
            if element:
                return await element.text_content()
            return None
        except Exception as e:
            self.logger.error(f"Error extracting text from {selector}: {e}")
            return None
            
    async def safe_get_attribute(self, page: Page, selector: str, attribute: str) -> Optional[str]:
        """Safely get attribute from an element"""
        try:
            element = await page.query_selector(selector)
            if element:
                return await element.get_attribute(attribute)
            return None
        except Exception as e:
            self.logger.error(f"Error getting attribute {attribute} from {selector}: {e}")
            return None 