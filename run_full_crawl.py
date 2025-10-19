"""
This script performs a full, deep crawl of the specified websites
and populates the production database. Run this before deploying.
"""
from backend.scrapers.full_site_scraper import FullSiteScraper
from backend.scrapers.eventbrite_scraper import EventbriteScraper
from backend.scrapers.meetup_scraper import MeetupScraper
from backend.database.db_manager import DatabaseManager
from loguru import logger

def run_deep_crawl():
    logger.info("🚀 STARTING DEEP CRAWL AND DATABASE POPULATION 🚀")
    
    # --- City of Rochester Deep Crawl ---
    logger.info("="*50)
    logger.info("Crawling City of Rochester website (up to 200 pages)...")
    
    # IMPORTANT: Seed URLs to ensure critical pages are scraped
    city_seed_urls = [
        "https://www.cityofrochester.gov/",
        "https://www.cityofrochester.gov/departments/neighborhood-and-business-development/business-permits/",
        "https://www.cityofrochester.gov/article.aspx?id=8589934882", # Permits Overview
        "https://www.cityofrochester.gov/departments/city-clerk/licenses/", # Licenses
    ]
    
    city_scraper = FullSiteScraper(max_pages=200, seed_urls=city_seed_urls)
    city_scraper.scrape() # This will now auto-save to the DB
    
    # --- Eventbrite Crawl ---
    logger.info("="*50)
    logger.info("Crawling Eventbrite for events...")
    eventbrite_scraper = EventbriteScraper()
    eventbrite_scraper.scrape()
    
    # --- Meetup Crawl ---
    logger.info("="*50)
    logger.info("Crawling Meetup for groups...")
    meetup_scraper = MeetupScraper()
    meetup_scraper.scrape()
    
    # --- Final Database Stats ---
    logger.info("="*50)
    logger.info("✅ DEEP CRAWL COMPLETE!")
    db = DatabaseManager()
    stats = db.count_items()
    logger.info(f"📊 Final Database Stats: {stats}")
    db.close()

if __name__ == "__main__":
    # WARNING: This will add a lot of data to your database.
    # It can take 5-10 minutes to run.
    confirm = input("This will run a full deep crawl and populate your database. Continue? (y/n): ")
    if confirm.lower() == 'y':
        run_deep_crawl()
    else:
        print("Crawl cancelled.")