import asyncio
import logging
from playwright.async_api import async_playwright
from src.scrapers.wko_scraper import WKOScraper
from datetime import datetime
import json
import os
import csv
import aiohttp
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

async def save_results(businesses, filename):
    """Save scraped results to JSON file"""
    output = []
    for business in businesses:
        business_dict = business.__dict__
        # Handle nested dataclass serialization
        if business_dict.get('social_media'):
            business_dict['social_media'] = business_dict['social_media'].__dict__
        if business_dict.get('hours'):
            business_dict['hours'] = [h.__dict__ for h in business_dict['hours']]
        business_dict['last_updated'] = business_dict['last_updated'].isoformat()
        output.append(business_dict)
        
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved JSON results to {filename}")

async def save_as_csv(businesses, filename):
    """Save results as CSV file"""
    fieldnames = [
        'name', 'category', 'description', 'address', 'phone', 'email', 
        'website', 'source', 'last_updated', 'hours', 'social_media'
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for business in businesses:
            # Format hours as string
            hours_str = "; ".join([f"{h.day}: {h.hours}" for h in business.hours]) if business.hours else ""
            
            # Format social media as string
            social_media_str = ", ".join([
                f"{platform}: {url}" 
                for platform, url in business.social_media.__dict__.items() 
                if url
            ])
            
            row = {
                'name': business.name,
                'category': business.category,
                'description': business.description,
                'address': business.address,
                'phone': business.phone,
                'email': business.email,
                'website': business.website,
                'source': business.source,
                'last_updated': business.last_updated.isoformat(),
                'hours': hours_str,
                'social_media': social_media_str
            }
            writer.writerow(row)
    logger.info(f"Saved CSV results to {filename}")

async def main():
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security'
                ]
            )
            
            # Create context with specific settings
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                locale='de-AT',
                ignore_https_errors=True,
                bypass_csp=True
            )
            
            # Set reasonable timeouts
            context.set_default_timeout(60000)  # 1 minute
            page = await context.new_page()
            page.set_default_timeout(60000)  # 1 minute
            
            # Initialize WKO scraper
            wko_scraper = WKOScraper()
            
            # Search parameters
            search_params = {
                "keyword": "Gasthaus",
                "location": "Graz-Stadt (Bezirk)",
                "limit": 1
            }
            
            # Run scraper
            logger.info("Starting WKO scraper...")
            businesses = await wko_scraper.scrape(page, search_params)
            
            if businesses:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Save as JSON
                json_filename = f"data/wko_results_{timestamp}.json"
                await save_results(businesses, json_filename)
                
                # Save as CSV
                csv_filename = f"data/wko_results_{timestamp}.csv"
                await save_as_csv(businesses, csv_filename)
                
                logger.info(f"Saved {len(businesses)} businesses")
            else:
                logger.warning("No businesses found")
            
            await browser.close()
            
    except Exception as e:
        logger.error(f"Error in main: {str(e)}", exc_info=True)
        raise
    finally:
        logger.info("Scraping completed")

if __name__ == "__main__":
    asyncio.run(main())