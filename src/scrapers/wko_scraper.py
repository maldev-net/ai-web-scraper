from src.scrapers.base_scraper import BaseScraper
from src.models.business import Business, BusinessHours, SocialMediaLinks
from playwright.async_api import Page
from typing import List, Optional
import logging
from datetime import datetime
from bs4 import BeautifulSoup
import json
import os

class WKOScraper(BaseScraper):
    BASE_URL = "https://firmen.wko.at/SearchSimple.aspx"
    
    # Update the extraction schema with actual selectors from the search results
    EXTRACTION_SCHEMA = {
        "name": "WKO Business Directory",
        "baseSelector": [
            ".firmenlisting-item",  # Main container for each business
            ".search-result-item"
        ],
        "fields": [
            {
                "name": "business_name",
                "selectors": [
                    ".firmenlisting-name",  # e.g., "Gasthaus 'Zur Schmied'n' KG"
                    "h3.firmenlisting-title",
                    "a.firmenlisting-link"
                ],
                "type": "text"
            },
            {
                "name": "category",
                "selectors": [
                    ".firmenlisting-category",  # Business category
                    ".business-type"
                ],
                "type": "text"
            },
            {
                "name": "address",
                "selectors": [
                    ".firmenlisting-address",  # e.g., "St.-Peter-Hauptstraße 225"
                    ".address-line",
                    ".postal-code",  # e.g., "8042"
                    ".city"  # e.g., "Graz"
                ],
                "type": "text"
            },
            {
                "name": "phone",
                "selectors": [
                    ".firmenlisting-phone",  # e.g., "+43 316 821106"
                    "a[href^='tel:']",  # Phone links
                    ".contact-phone"
                ],
                "type": "text"
            },
            {
                "name": "email",
                "selectors": [
                    ".firmenlisting-email",  # e.g., "gasthaus@stainzerbauer.at"
                    "a[href^='mailto:']",  # Email links
                    ".contact-email"
                ],
                "type": "attribute",
                "attribute": "href"
            },
            {
                "name": "website",
                "selectors": [
                    ".firmenlisting-website",  # e.g., "www.stainzerbauer.at"
                    "a.website-link",
                    ".contact-website"
                ],
                "type": "attribute",
                "attribute": "href"
            },
            {
                "name": "description",
                "selectors": [
                    ".firmenlisting-description",
                    ".business-description",
                    ".company-info"
                ],
                "type": "text"
            }
        ]
    }
    
    async def scrape(self, page: Page, search_params: dict) -> List[Business]:
        businesses = []
        try:
            # Navigate to search page and submit form
            self.logger.info(f"Navigating to {self.BASE_URL}")
            await page.goto(self.BASE_URL, wait_until="networkidle", timeout=240000)
            await self._submit_search_form(page, search_params)
            
            # Wait for search results
            await page.wait_for_load_state("networkidle")
            
            # Get all Gasthaus links
            gasthaus_links = await page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('h3.firmenlisting-title a, a.firmenlisting-link'));
                    return links.map(link => ({
                        url: link.href,
                        name: link.textContent.trim()
                    }));
                }
            """)
            
            self.logger.info(f"Found {len(gasthaus_links)} Gasthaus links")
            
            # Process each Gasthaus
            limit = search_params.get("limit", 10)
            for gasthaus in gasthaus_links[:limit]:
                try:
                    self.logger.info(f"Processing Gasthaus: {gasthaus['name']}")
                    
                    # Navigate to Gasthaus detail page
                    await page.goto(gasthaus['url'], wait_until="networkidle", timeout=60000)
                    await page.wait_for_load_state("domcontentloaded")
                    
                    # Extract detailed information
                    business_data = await page.evaluate("""
                        () => {
                            const getData = (selector) => {
                                const element = document.querySelector(selector);
                                return element ? element.textContent.trim() : null;
                            };
                            
                            const getLink = (selector) => {
                                const element = document.querySelector(selector);
                                return element ? element.href : null;
                            };
                            
                            return {
                                name: getData('h1.company-name, .firmenlisting-title, h3'),
                                address: getData('.address, .firmenlisting-address'),
                                postal: getData('.postal-code'),
                                city: getData('.city'),
                                phone: getData('.phone, a[href^="tel:"]'),
                                email: getLink('a[href^="mailto:"]'),
                                website: getLink('.website a, a[href^="http"]:not([href*="wko.at"])'),
                                description: getData('.description, .company-description'),
                                category: getData('.category, .business-type')
                            };
                        }
                    """)
                    
                    # Create business object
                    if business_data.get('name'):
                        address = ", ".join(filter(None, [
                            business_data.get('address'),
                            business_data.get('postal'),
                            business_data.get('city')
                        ]))
                        
                        business = Business(
                            name=business_data['name'],
                            category="Gasthaus",
                            description=business_data.get('description', ''),
                            address=address,
                            phone=business_data.get('phone'),
                            email=business_data.get('email'),
                            website=business_data.get('website'),
                            source=gasthaus['url'],
                            last_updated=datetime.now()
                        )
                        
                        businesses.append(business)
                        self.logger.info(f"Added business: {business.name}")
                        
                        # Take screenshot of detail page
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        await page.screenshot(path=f"screenshots/detail_{timestamp}.png")
                    
                except Exception as e:
                    self.logger.error(f"Error processing Gasthaus {gasthaus['name']}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error during scraping: {e}")
            await page.screenshot(path="error.png")
            
        return businesses

    async def _submit_search_form(self, page: Page, search_params: dict) -> None:
        """Submit the search form using JavaScript"""
        keyword = search_params.get("keyword", "")
        location = search_params.get("location", "")
        
        try:
            self.logger.info(f"Submitting search form with keyword: {keyword}, location: {location}")
            
            # Create screenshots directory if it doesn't exist
            os.makedirs("screenshots", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Wait for initial page load
            await page.wait_for_load_state("domcontentloaded", timeout=60000)
            await page.wait_for_selector("#aspnetForm", timeout=60000)
            
            # Use the exact IDs from the form elements we found
            js_code = """
            (form_data) => {
                const whatInput = document.querySelector('#ctl00_ContentPlaceHolder1_searchBoxLoaderControl_ctl00_txtSuchbegriff');
                const whereInput = document.querySelector('#ctl00_ContentPlaceHolder1_searchBoxLoaderControl_ctl00_txtStandort');
                const submitButton = document.querySelector('#ctl00_ContentPlaceHolder1_searchBoxLoaderControl_ctl00_btnSearch');
                
                if (whatInput && whereInput && submitButton) {
                    // Fill the form
                    whatInput.value = form_data.keyword;
                    whereInput.value = form_data.location;
                    
                    // Dispatch events
                    whatInput.dispatchEvent(new Event('input', { bubbles: true }));
                    whereInput.dispatchEvent(new Event('input', { bubbles: true }));
                    
                    // Submit form
                    submitButton.click();
                    return { success: true };
                }
                
                // Debug info about what was found
                return {
                    success: false,
                    debug: {
                        whatFound: !!whatInput,
                        whereFound: !!whereInput,
                        submitFound: !!submitButton,
                        whatId: '#ctl00_ContentPlaceHolder1_searchBoxLoaderControl_ctl00_txtSuchbegriff',
                        whereId: '#ctl00_ContentPlaceHolder1_searchBoxLoaderControl_ctl00_txtStandort',
                        submitId: '#ctl00_ContentPlaceHolder1_searchBoxLoaderControl_ctl00_btnSearch'
                    }
                };
            }
            """
            
            # Execute JavaScript
            result = await page.evaluate(js_code, {
                "keyword": keyword,
                "location": location
            })
            
            self.logger.info(f"Form submission result: {result}")
            
            if not result.get('success'):
                debug_info = result.get('debug', {})
                self.logger.error(f"Form elements not found. Debug info: {debug_info}")
                
                # Try direct Playwright approach as fallback
                try:
                    self.logger.info("Trying direct Playwright approach...")
                    
                    # Fill keyword
                    await page.fill("#ctl00_ContentPlaceHolder1_searchBoxLoaderControl_ctl00_txtSuchbegriff", keyword)
                    await page.wait_for_timeout(2000)
                    
                    # Fill location
                    await page.fill("#ctl00_ContentPlaceHolder1_searchBoxLoaderControl_ctl00_txtStandort", location)
                    await page.wait_for_timeout(2000)
                    
                    # Click search
                    await page.click("#ctl00_ContentPlaceHolder1_searchBoxLoaderControl_ctl00_btnSearch")
                    
                except Exception as e:
                    self.logger.error(f"Direct Playwright approach failed: {e}")
                    await page.screenshot(path=f"screenshots/form_error_{timestamp}.png")
                    content = await page.content()
                    with open(f"screenshots/form_debug_{timestamp}.html", "w", encoding="utf-8") as f:
                        f.write(content)
                    raise Exception(f"Could not submit form: {debug_info}")
            
            self.logger.info("Search form submitted")
            
            # Wait for navigation and results
            await page.wait_for_load_state("networkidle", timeout=60000)
            await page.screenshot(path=f"screenshots/after_submit_{timestamp}.png")
            
            # Wait for results with multiple possible selectors
            result_selectors = [
                ".SearchResultItem",
                ".firmen-liste > div",
                "[itemtype*='Organization']",
                ".search-results",
                ".Suchergebnis"
            ]
            
            for selector in result_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=30000)
                    self.logger.info(f"Found results with selector: {selector}")
                    return
                except Exception:
                    continue
            
            # If we get here, no results were found
            self.logger.error("No results found after search")
            await page.screenshot(path=f"screenshots/no_results_{timestamp}.png")
            content = await page.content()
            with open(f"screenshots/no_results_{timestamp}.html", "w", encoding="utf-8") as f:
                f.write(content)
            raise Exception("No results found after search")
            
        except Exception as e:
            self.logger.error(f"Error submitting search form: {e}")
            await page.screenshot(path=f"screenshots/error_{timestamp}.png")
            try:
                content = await page.content()
                with open(f"screenshots/error_content_{timestamp}.html", "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as content_error:
                self.logger.error(f"Failed to save error page content: {content_error}")
            raise