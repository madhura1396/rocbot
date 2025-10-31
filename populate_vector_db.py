"""
Script to populate ChromaDB with embeddings from existing PostgreSQL data.

Run this script once to migrate from keyword search to semantic search.

Usage:
    python populate_vector_db.py
"""
import sys
from loguru import logger
from backend.database.db_manager import DatabaseManager
from backend.database.vector_db_manager import VectorDBManager, get_vector_db_manager
from backend.database.models import init_db, ContentItem


def populate_vector_database(reset: bool = False):
    """
    Populate the vector database with all content from PostgreSQL.

    Args:
        reset: If True, delete existing embeddings before populating

    Line-by-line explanation:
    - Reads all content from PostgreSQL
    - Generates embeddings for each item
    - Stores embeddings in ChromaDB for semantic search
    """

    # Line 1: Initialize databases
    logger.info("Initializing databases...")
    init_db()  # Ensure PostgreSQL tables exist
    vector_db = get_vector_db_manager()  # Initialize ChromaDB

    # Line 2: Optionally reset the vector database
    if reset:
        logger.warning("Resetting vector database (deleting all embeddings)...")
        vector_db.reset_collection()

    # Line 3: Check current state
    current_count = vector_db.get_collection_count()
    logger.info(f"Current vector DB count: {current_count}")

    # Line 4: Fetch all content items from PostgreSQL
    logger.info("Fetching all content items from PostgreSQL...")
    db_manager = DatabaseManager()

    # Get all items (no limit)
    all_items = db_manager.session.query(ContentItem).all()
    logger.info(f"Found {len(all_items)} items in PostgreSQL")

    if len(all_items) == 0:
        logger.warning("No items found in database. Run 'python run_full_crawl.py' first to populate data.")
        return

    # Line 5: Add items to vector database in batches
    # Processing in batches is more efficient
    batch_size = 50
    total_added = 0

    for i in range(0, len(all_items), batch_size):
        batch = all_items[i:i + batch_size]
        logger.info(f"Processing batch {i // batch_size + 1} ({i + 1}-{min(i + batch_size, len(all_items))} of {len(all_items)})")

        # Add batch to vector DB
        added_count = vector_db.add_multiple_items(batch)
        total_added += added_count

        logger.info(f"Added {added_count}/{len(batch)} items from this batch")

    # Line 6: Final statistics
    final_count = vector_db.get_collection_count()
    logger.info(f"\n{'=' * 50}")
    logger.info(f"Population complete!")
    logger.info(f"Total items processed: {len(all_items)}")
    logger.info(f"Total items added: {total_added}")
    logger.info(f"Final vector DB count: {final_count}")
    logger.info(f"{'=' * 50}\n")

    # Line 7: Test the semantic search
    logger.info("Testing semantic search...")
    test_queries = [
        "What events are happening this weekend?",
        "Where can I find parks?",
        "City government services",
    ]

    for query in test_queries:
        logger.info(f"\nTest query: '{query}'")
        results = vector_db.semantic_search(query, limit=3)
        logger.info(f"Found {len(results)} results:")
        for idx, item in enumerate(results, 1):
            logger.info(f"  {idx}. {item.title} ({item.source})")

    # Clean up
    db_manager.close()
    vector_db.close()


if __name__ == "__main__":
    """
    Main entry point.

    Line-by-line explanation:
    - Checks for --reset flag
    - Runs the population process
    - Shows helpful error messages
    """

    # Line 1: Check command line arguments
    reset_flag = "--reset" in sys.argv

    if reset_flag:
        logger.warning("⚠️  RESET MODE: All existing embeddings will be deleted!")
        confirm = input("Are you sure? Type 'yes' to continue: ")
        if confirm.lower() != "yes":
            logger.info("Operation cancelled")
            sys.exit(0)

    # Line 2: Run the population
    try:
        logger.info("Starting vector database population...")
        populate_vector_database(reset=reset_flag)
        logger.info("✅ Success! Semantic search is now ready to use.")
        logger.info("\nNext steps:")
        logger.info("1. Restart your FastAPI server if it's running")
        logger.info("2. The chatbot will now use semantic search instead of keyword search")
        logger.info("3. Try queries like 'outdoor activities' or 'family events'")

    except Exception as e:
        logger.error(f"❌ Error during population: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
