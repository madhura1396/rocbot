"""Database models for RocBot."""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, create_engine, Index
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

Base = declarative_base()


class ContentItem(Base):
    """Stores all scraped content (pages, events, news, etc.)."""
    __tablename__ = 'content_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(100), nullable=False)  # 'cityofrochester', 'eventbrite', 'meetup'
    category = Column(String(50), nullable=False)  # 'news', 'events', 'services', etc.
    type = Column(String(50), nullable=False)  # 'page', 'event', 'news', 'meeting', etc.
    
    title = Column(String(500), nullable=False)
    description = Column(Text)
    content_full = Column(Text, nullable=False)
    
    url = Column(String(1000), unique=True, nullable=False)
    image_url = Column(String(1000))
    
    date_start = Column(String(100))  # For events
    date_end = Column(String(100))  # For events
    location = Column(String(500))  # For events
    
    meta_data = Column(JSON)  # Store flexible metadata as JSON
    
    scraped_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add indexes for faster searches
    __table_args__ = (
        Index('idx_title', 'title'),
        Index('idx_source', 'source'),
        Index('idx_category', 'category'),
        Index('idx_url', 'url'),
    )
    
    def __repr__(self):
        return f"<ContentItem(id={self.id}, title='{self.title[:50]}...', source='{self.source}')>"
    
    def to_dict(self):
        """Convert to dictionary for JSON responses."""
        return {
            'id': self.id,
            'source': self.source,
            'category': self.category,
            'type': self.type,
            'title': self.title,
            'description': self.description,
            'content_full': self.content_full,
            'url': self.url,
            'image_url': self.image_url,
            'date_start': self.date_start,
            'date_end': self.date_end,
            'location': self.location,
            'metadata': self.meta_data,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# Database connection
def get_engine():
    """Create database engine with connection pooling."""
    from sqlalchemy.pool import QueuePool
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL not found in .env file!")
    
    return create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=10,          # Keep 10 connections ready
        max_overflow=20,       # Allow 20 extra if needed
        pool_pre_ping=True,    # Check connection health
        echo=False
    )


def get_session():
    """Create database session."""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def init_db():
    """Initialize database - create all tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("✅ Database tables created successfully!")


if __name__ == "__main__":
    # Test database creation
    print("Creating database tables...")
    init_db()