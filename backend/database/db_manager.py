"""Database manager - helper functions for CRUD operations."""
from typing import List, Dict, Optional
from sqlalchemy.exc import IntegrityError
from loguru import logger
import sys
import os
import string

from backend.database.models import ContentItem, get_session, init_db


class DatabaseManager:
    """Manages all database operations."""
    
    def __init__(self):
        self.session = get_session()
    
    def save_content_item(self, item_data: Dict) -> Optional[ContentItem]:
        """
        Save a single content item to database.
        Returns the saved item or None if duplicate URL.
        """
        try:
            # Check if URL already exists
            existing = self.session.query(ContentItem).filter_by(url=item_data['url']).first()
            
            if existing:
                logger.info(f"URL already exists, updating: {item_data['url']}")
                # Update existing item
                for key, value in item_data.items():
                    if key != 'scraped_at':  # Don't update scraped_at
                        setattr(existing, key, value)
                self.session.commit()
                return existing
            
            # Create new item
            item = ContentItem(**item_data)
            self.session.add(item)
            self.session.commit()
            logger.info(f"Saved new item: {item.title}")
            return item
            
        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"Database integrity error: {e}")
            return None
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error saving item: {e}")
            return None
    
    def save_multiple(self, items_data: List[Dict]) -> int:
        """
        Save multiple content items.
        Returns count of successfully saved items.
        """
        saved_count = 0
        for item_data in items_data:
            if self.save_content_item(item_data):
                saved_count += 1
        
        logger.info(f"Saved {saved_count}/{len(items_data)} items to database")
        return saved_count
    
    def get_all_content(self, limit: int = 100) -> List[ContentItem]:
        """Get all content items (limited)."""
        return self.session.query(ContentItem).limit(limit).all()
    
    def get_by_category(self, category: str, limit: int = 50) -> List[ContentItem]:
        """Get content items by category."""
        return self.session.query(ContentItem).filter_by(category=category).limit(limit).all()
    
    def get_by_source(self, source: str, limit: int = 100) -> List[ContentItem]:
        """Get content items by source."""
        return self.session.query(ContentItem).filter_by(source=source).limit(limit).all()
    
    def search_content(self, query: str, limit: int = 10) -> List[ContentItem]:
        """
        Improved text search in title and content with keyword extraction.
        """
        query_lower = query.lower()
        
        # Extract important keywords from the query
        # Remove common words and punctuation
        stop_words = {'who', 'is', 'the', 'what', 'are', 'there', 'any', 'how', 'do', 'i', 
                      'in', 'of', 'to', 'a', 'an', 'this', 'that', 'or', 'and'}
        
        # Clean words: remove punctuation
        words = query_lower.split()
        cleaned_words = [word.strip(string.punctuation) for word in words]
        keywords = [word for word in cleaned_words if word not in stop_words and len(word) > 2]
        
        if not keywords:
            # If no keywords, use the full query
            keywords = [query_lower]
        
        logger.info(f"Searching for keywords: {keywords}")
        
        # Build search conditions
        results = []
        for keyword in keywords:
            search_pattern = f"%{keyword}%"
            items = self.session.query(ContentItem).filter(
                (ContentItem.title.ilike(search_pattern)) |
                (ContentItem.content_full.ilike(search_pattern)) |
                (ContentItem.description.ilike(search_pattern))
            ).all()
            
            # Add to results if not already there
            for item in items:
                if item not in results:
                    results.append(item)
        
        # Sort by relevance with improved scoring
        def relevance_score(item):
            score = 0
            title_lower = item.title.lower()
            content_lower = item.content_full.lower()
            
            for keyword in keywords:
                # Title matches = highest priority (100x weight)
                if keyword in title_lower:
                    score += 100
                
                # Exact phrase in content = high priority
                if f" {keyword} " in content_lower:
                    score += 50
                
                # Keyword appears anywhere = base score
                score += content_lower.count(keyword)
            
            # Penalize very long generic pages
            content_length = len(item.content_full)
            if content_length > 5000:
                score = score * 0.5  # 50% penalty
            elif content_length > 10000:
                score = score * 0.3  # 70% penalty
            
            return score
        
        results.sort(key=relevance_score, reverse=True)
        
        logger.info(f"Found {len(results)} results")
        
        return results[:limit]
    
    def get_recent_items(self, limit: int = 20) -> List[ContentItem]:
        """Get most recently scraped items."""
        return self.session.query(ContentItem).order_by(
            ContentItem.scraped_at.desc()
        ).limit(limit).all()
    
    def count_items(self) -> Dict[str, int]:
        """Get statistics about stored content."""
        total = self.session.query(ContentItem).count()
        
        # Count by source
        sources = {}
        for source in ['cityofrochester', 'eventbrite', 'meetup']:
            count = self.session.query(ContentItem).filter_by(source=source).count()
            sources[source] = count
        
        # Count by category
        categories = {}
        for category in ['news', 'events', 'services', 'government', 'departments', 'general']:
            count = self.session.query(ContentItem).filter_by(category=category).count()
            categories[category] = count
        
        return {
            'total': total,
            'by_source': sources,
            'by_category': categories
        }
    
    def close(self):
        """Close database session."""
        self.session.close()


def save_scraped_data_to_db(scraped_items: List[Dict]) -> int:
    """
    Convenience function to save scraped data to database.
    
    Args:
        scraped_items: List of dictionaries from scrapers
    
    Returns:
        Number of items saved
    """
    db = DatabaseManager()
    try:
        count = db.save_multiple(scraped_items)
        return count
    finally:
        db.close()


if __name__ == "__main__":
    # Test database manager
    print("Testing DatabaseManager...")
    
    # Initialize database
    init_db()
    
    # Create test item
    test_item = {
        'source': 'test',
        'category': 'general',
        'type': 'page',
        'title': 'Test Page',
        'description': 'This is a test',
        'content_full': 'Test content for database manager',
        'url': 'https://test.com/test-page',
        'meta_data': {'tags': ['test']}
    }
    
    # Test save
    db = DatabaseManager()
    saved = db.save_content_item(test_item)
    
    if saved:
        print(f"✅ Test item saved with ID: {saved.id}")
        
        # Test retrieve
        items = db.get_all_content(limit=5)
        print(f"✅ Retrieved {len(items)} items from database")
        
        # Test search
        results = db.search_content('test')
        print(f"✅ Search found {len(results)} items")
        
        # Test stats
        stats = db.count_items()
        print(f"✅ Database stats: {stats}")
    
    db.close()
    print("\n✅ DatabaseManager test complete!")