"""Test the full site crawler."""
import json
import sys
import os

# Add parent directory to path so we can import from backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from loguru import logger
from backend.scrapers.full_site_scraper import FullSiteScraper

# Configure logger
logger.add("logs/crawler_test.log", rotation="10 MB")


def test_full_crawler():
    """Test full site crawler with limited pages."""
    logger.info("="*60)
    logger.info("Testing Full Site Crawler")
    logger.info("="*60)
    
    print("\n🕷️  Starting crawler test...")
    print("This will crawl up to 10 pages from cityofrochester.gov")
    print("It should take about 20-30 seconds...\n")
    
    # Create scraper (limit to 10 pages for testing)
    scraper = FullSiteScraper(max_pages=10)
    
    # Run the crawler
    try:
        content = scraper.scrape()
        
        print("\n" + "="*60)
        print(f"✅ SUCCESS! Crawled {len(content)} pages")
        print("="*60)
        
        # Save to file for inspection
        output_file = 'data/test_crawler_output.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        
        print(f"\n📁 Results saved to: {output_file}")
        
        # Show statistics
        print("\n📊 STATISTICS:")
        print(f"   Total pages crawled: {len(content)}")
        
        # Count by category
        categories = {}
        for item in content:
            cat = item.get('category', 'unknown')
            categories[cat] = categories.get(cat, 0) + 1
        
        print("\n   Pages by category:")
        for cat, count in categories.items():
            print(f"     - {cat}: {count}")
        
        # Show first 3 page titles
        print("\n📄 SAMPLE PAGES CRAWLED:")
        for i, item in enumerate(content[:3], 1):
            print(f"\n   {i}. {item['title']}")
            print(f"      URL: {item['url']}")
            print(f"      Category: {item['category']}")
            print(f"      Content length: {len(item['content_full'])} characters")
            print(f"      Preview: {item['content_full'][:150]}...")
        
        # Show one full example
        if content:
            print("\n" + "="*60)
            print("📝 FULL EXAMPLE (First Page):")
            print("="*60)
            print(json.dumps(content[0], indent=2, ensure_ascii=False))
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        logger.error(f"Crawler test failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_full_crawler()
    
    if success:
        print("\n✅ Test completed successfully!")
        print("\nNext steps:")
        print("  1. Check data/test_crawler_output.json to see the scraped content")
        print("  2. Check logs/crawler_test.log for detailed logs")
        print("  3. If it looks good, we'll increase max_pages and build the database!")
    else:
        print("\n❌ Test failed. Check the error messages above.")