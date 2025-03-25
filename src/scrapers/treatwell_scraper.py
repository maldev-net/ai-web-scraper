from src.scrapers.base_scraper import BaseScraper
from src.models.business import Business, BusinessHours, SocialMediaLinks
from playwright.async_api import Page
from typing import List, Optional
from datetime import datetime
import logging
import json

class TreatwellScraper(BaseScraper):
    BASE_URL = "https://www.treatwell.de"
    
    async def scrape(self, page: Page, search_params: dict) -> List[Business]:
        businesses = []
        try:
            # Navigate to main page
            self.logger.info(f"Navigating to {self.BASE_URL}")
            await page.goto(self.BASE_URL, wait_until="networkidle", timeout=60000)
            
            # Wait for page to be fully loaded
            await page.wait_for_load_state("domcontentloaded")
            
            # Debug: Log current URL
            self.logger.info(f"Current URL: {page.url}")
            
            # Accept cookies if present
            try:
                accept_button = await page.wait_for_selector(
                    "button[data-testid='cookie-banner-accept-button']",
                    timeout=5000
                )
                if accept_button:
                    await accept_button.click()
                    self.logger.info("Accepted cookies")
            except Exception:
                self.logger.info("No cookie banner found")
            
            # Try different search input selectors
            search_selectors = [
                "#search-input",
                "input[placeholder*='Suche']",
                "input[placeholder*='search']",
                "input[placeholder*='Search']",
                "[data-testid='search-input']",
                "[data-testid='searchbox-input']",
                "#searchbox-input"
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    self.logger.info(f"Trying search selector: {selector}")
                    search_input = await page.wait_for_selector(selector, timeout=5000)
                    if search_input:
                        self.logger.info(f"Found search input with selector: {selector}")
                        break
                except Exception:
                    continue
            
            if not search_input:
                # Try clicking a search button first
                try:
                    search_button = await page.wait_for_selector(
                        "[data-testid='search-button'], .search-button, button:has-text('Suche')",
                        timeout=5000
                    )
                    if search_button:
                        await search_button.click()
                        self.logger.info("Clicked search button")
                        # Wait for search input to appear
                        await page.wait_for_timeout(1000)
                        for selector in search_selectors:
                            search_input = await page.wait_for_selector(selector, timeout=5000)
                            if search_input:
                                break
                except Exception as e:
                    self.logger.error(f"Error clicking search button: {e}")
            
            if not search_input:
                # Save screenshot and HTML for debugging
                await page.screenshot(path="search_input_not_found.png")
                content = await page.content()
                with open("page_content.html", "w", encoding="utf-8") as f:
                    f.write(content)
                raise Exception("Could not find search input")
            
            # Enter search term
            await search_input.fill(search_params.get("keyword", "Friseur"))
            await page.wait_for_timeout(1000)
            
            # Try different ways to trigger search
            try:
                # First try pressing Enter
                await search_input.press("Enter")
                await page.wait_for_timeout(2000)
                
                # If that doesn't work, try clicking a search submit button
                if not await page.query_selector(".salon-search-result"):
                    submit_button = await page.query_selector(
                        "button[type='submit'], [data-testid='search-submit']"
                    )
                    if submit_button:
                        await submit_button.click()
            except Exception as e:
                self.logger.error(f"Error triggering search: {e}")
            
            # Wait for results with multiple possible selectors
            result_selectors = [
                ".salon-search-result",
                "[data-testid='salon-card']",
                ".venue-card",
                ".search-result-item"
            ]
            
            found_selector = None
            for selector in result_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=10000)
                    found_selector = selector
                    break
                except Exception:
                    continue
            
            if not found_selector:
                raise Exception("No search results found")
            
            # Extract all salon cards
            salon_cards = await page.query_selector_all(found_selector)
            self.logger.info(f"Found {len(salon_cards)} salons")
            
            # Process each salon
            limit = search_params.get("limit", 10)
            for card in salon_cards[:limit]:
                try:
                    business = await self._extract_business_from_card(card)
                    if business and business.validate():
                        businesses.append(business)
                        self.logger.info(f"Successfully scraped business: {business.name}")
                except Exception as e:
                    self.logger.error(f"Error processing salon card: {str(e)}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error scraping Treatwell: {str(e)}")
            # Take error screenshot
            try:
                await page.screenshot(path="error_screenshot.png")
                self.logger.info("Error screenshot saved")
                content = await page.content()
                with open("error_page.html", "w", encoding="utf-8") as f:
                    f.write(content)
                self.logger.info("Error page HTML saved")
            except Exception as screenshot_error:
                self.logger.error(f"Error saving debug info: {screenshot_error}")
            
        return businesses
    
    async def _extract_business_from_card(self, card) -> Optional[Business]:
        try:
            # Extract basic information
            name = await self.safe_get_text(card, ".salon-name")
            if not name:
                return None
                
            # Extract address
            address = await self.safe_get_text(card, ".salon-address")
            
            # Extract rating and reviews
            rating = await self.safe_get_text(card, ".rating-score")
            reviews = await self.safe_get_text(card, ".review-count")
            description = f"Rating: {rating}, Reviews: {reviews}" if rating and reviews else ""
            
            # Extract category/services
            category = await self.safe_get_text(card, ".salon-category") or "Beauty Salon"
            
            # Extract website URL
            website = await self.safe_get_attribute(card, "a.salon-link", "href")
            if website and not website.startswith('http'):
                website = f"{self.BASE_URL}{website}"
            
            # Create business object
            business = Business(
                name=name.strip(),
                category=category.strip(),
                description=description,
                address=address.strip() if address else None,
                phone=None,  # Phone is usually on detail page
                email=None,  # Email is usually not public
                website=website,
                social_media=SocialMediaLinks(),
                source="treatwell.de",
                last_updated=datetime.now()
            )
            
            return business
            
        except Exception as e:
            self.logger.error(f"Error extracting business details: {e}")
            return None 