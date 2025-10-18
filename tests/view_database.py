"""View database contents."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database.db_manager import DatabaseManager

def view_database():
    """Display database contents."""
    db = DatabaseManager()
    
    # Get stats
    stats = db.count_items()
    print("\n" + "="*60)
    print("📊 DATABASE STATISTICS")
    print("="*60)
    print(f"Total items: {stats['total']}")
    print(f"\nBy source:")
    for source, count in stats['by_source'].items():
        print(f"  - {source}: {count}")
    print(f"\nBy category:")
    for category, count in stats['by_category'].items():
        if count > 0:
            print(f"  - {category}: {count}")
    
    # Get all items
    print("\n" + "="*60)
    print("📄 ALL CONTENT ITEMS")
    print("="*60)
    
    items = db.get_all_content(limit=100)
    
    for i, item in enumerate(items, 1):
        print(f"\n{i}. {item.title}")
        print(f"   Category: {item.category}")
        print(f"   Source: {item.source}")
        print(f"   URL: {item.url}")
        print(f"   Content length: {len(item.content_full)} chars")
        print(f"   Scraped: {item.scraped_at}")
    
    # Test search
    print("\n" + "="*60)
    print("🔍 TEST SEARCH: 'mayor'")
    print("="*60)
    
    results = db.search_content('mayor')
    print(f"\nFound {len(results)} results:")
    for item in results:
        print(f"\n- {item.title}")
        print(f"  {item.url}")
    
    db.close()
    print("\n✅ Done!")

if __name__ == "__main__":
    view_database()