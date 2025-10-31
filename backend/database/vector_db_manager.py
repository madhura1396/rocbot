"""Vector database manager using ChromaDB for semantic search."""
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
from loguru import logger
import os

from backend.database.db_manager import DatabaseManager
from backend.database.models import ContentItem


class VectorDBManager:
    """
    Manages vector embeddings and semantic search using ChromaDB.

    This replaces the keyword-based search with semantic similarity search.
    """

    def __init__(self, collection_name: str = "rocbot_content"):
        """
        Initialize the vector database manager.

        Args:
            collection_name: Name of the ChromaDB collection to use

        Line-by-line explanation:
        - We'll use ChromaDB to store vector embeddings of our content
        - We'll use SentenceTransformer to generate embeddings
        - The embedding model 'all-MiniLM-L6-v2' is fast and accurate for semantic search
        """

        # Line 1: Set up the path where ChromaDB will store its data
        # This creates a persistent database in the 'chroma_db' folder
        self.persist_directory = os.path.join(os.path.dirname(__file__), "../../chroma_db")
        os.makedirs(self.persist_directory, exist_ok=True)
        logger.info(f"ChromaDB persist directory: {self.persist_directory}")

        # Line 2: Initialize ChromaDB client with persistent storage
        # This means our embeddings won't disappear when we restart the app
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,  # Disable analytics
                allow_reset=True  # Allow us to reset the database if needed
            )
        )
        logger.info("ChromaDB client initialized")

        # Line 3: Initialize the embedding model
        # 'all-MiniLM-L6-v2' creates 384-dimensional vectors
        # It's lightweight (80MB) and works well for semantic similarity
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Sentence transformer model loaded: all-MiniLM-L6-v2")

        # Line 4: Get or create the collection
        # A collection is like a table in ChromaDB where we store embeddings
        try:
            self.collection = self.client.get_collection(name=collection_name)
            logger.info(f"Loaded existing collection: {collection_name}")
        except Exception:
            # If collection doesn't exist, create it
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "Rochester content embeddings for semantic search"}
            )
            logger.info(f"Created new collection: {collection_name}")

        # Line 5: Initialize the regular database manager for fetching full content
        self.db_manager = DatabaseManager()

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a vector embedding for a given text.

        Args:
            text: The text to embed

        Returns:
            A 384-dimensional vector representing the text's semantic meaning

        Line-by-line explanation:
        - This converts text into a numerical vector
        - Similar texts will have similar vectors (cosine similarity)
        - Example: "park events" and "outdoor activities" will be close in vector space
        """
        # The encode method converts text to a vector
        # normalize_embeddings=True ensures vectors are unit length (helps with comparison)
        embedding = self.embedding_model.encode(text, normalize_embeddings=True)

        # Convert numpy array to Python list for ChromaDB compatibility
        return embedding.tolist()

    def add_content_item(self, item: ContentItem) -> bool:
        """
        Add a single content item to the vector database.

        Args:
            item: ContentItem from PostgreSQL database

        Returns:
            True if successful, False otherwise

        Line-by-line explanation:
        - Takes a database item and creates an embedding for it
        - Stores the embedding in ChromaDB with metadata
        - The ID links back to the PostgreSQL record
        """
        try:
            # Line 1: Create a combined text for embedding
            # We combine title (3x weight), description, and content
            # Title gets more weight because it's usually more relevant
            combined_text = f"{item.title} {item.title} {item.title} {item.description or ''} {item.content_full[:1000]}"

            # Line 2: Generate the embedding vector
            embedding = self.generate_embedding(combined_text)

            # Line 3: Prepare metadata to store alongside the embedding
            # Metadata helps us filter results and provides context
            metadata = {
                "title": item.title[:500],  # Truncate to avoid size limits
                "source": item.source,
                "category": item.category,
                "url": item.url,
                "type": item.type or "unknown",
            }

            # Line 4: Add to ChromaDB collection
            # - ids: unique identifier (we use the PostgreSQL ID)
            # - embeddings: the vector representation
            # - metadatas: additional info we can filter on
            # - documents: the actual text (used for context)
            self.collection.add(
                ids=[str(item.id)],  # Must be string
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[combined_text[:1000]]  # Store truncated text
            )

            logger.debug(f"Added item {item.id} to vector DB: {item.title}")
            return True

        except Exception as e:
            logger.error(f"Error adding item {item.id} to vector DB: {e}")
            return False

    def add_multiple_items(self, items: List[ContentItem]) -> int:
        """
        Add multiple content items to the vector database in batch.

        Args:
            items: List of ContentItems from PostgreSQL

        Returns:
            Number of items successfully added

        Line-by-line explanation:
        - Batch processing is more efficient than adding one by one
        - We prepare all embeddings, then add them in one operation
        """
        if not items:
            return 0

        # Prepare batch data
        ids = []
        embeddings = []
        metadatas = []
        documents = []

        for item in items:
            try:
                # Same process as add_content_item, but collect into lists
                combined_text = f"{item.title} {item.title} {item.title} {item.description or ''} {item.content_full[:1000]}"
                embedding = self.generate_embedding(combined_text)

                ids.append(str(item.id))
                embeddings.append(embedding)
                metadatas.append({
                    "title": item.title[:500],
                    "source": item.source,
                    "category": item.category,
                    "url": item.url,
                    "type": item.type or "unknown",
                })
                documents.append(combined_text[:1000])

            except Exception as e:
                logger.error(f"Error processing item {item.id}: {e}")
                continue

        # Add all items at once
        if ids:
            try:
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents
                )
                logger.info(f"Added {len(ids)} items to vector DB in batch")
                return len(ids)
            except Exception as e:
                logger.error(f"Error adding batch to vector DB: {e}")
                return 0

        return 0

    def semantic_search(self, query: str, limit: int = 10, source_filter: Optional[str] = None) -> List[ContentItem]:
        """
        Perform semantic search to find similar content.

        Args:
            query: The user's question or search query
            limit: Maximum number of results to return
            source_filter: Optional filter by source (e.g., 'eventbrite', 'cityofrochester')

        Returns:
            List of ContentItem objects ordered by semantic similarity

        Line-by-line explanation:
        THIS IS THE KEY METHOD - replaces the old keyword search!
        - Converts the query to an embedding
        - Finds the closest matching embeddings in ChromaDB
        - Returns the actual database items in order of relevance
        """
        try:
            # Line 1: Convert the user's query into a vector
            # This is the same embedding space as our stored content
            query_embedding = self.generate_embedding(query)
            logger.info(f"Performing semantic search for: '{query}'")

            # Line 2: Prepare filter conditions (if any)
            where_filter = None
            if source_filter:
                where_filter = {"source": source_filter}

            # Line 3: Query ChromaDB for similar vectors
            # n_results: how many to return
            # where: metadata filters
            # include: what data to return
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_filter,
                include=["metadatas", "distances", "documents"]
            )

            # Line 4: Extract the IDs of matching items
            # results['ids'] is a list of lists, we take the first inner list
            if not results['ids'] or not results['ids'][0]:
                logger.info("No results found in vector search")
                return []

            matching_ids = results['ids'][0]  # List of string IDs
            distances = results['distances'][0]  # Similarity scores (lower = more similar)

            logger.info(f"Found {len(matching_ids)} results with distances: {distances[:3]}")

            # Line 5: Fetch the full ContentItem objects from PostgreSQL
            # ChromaDB only stores embeddings and metadata, not full content
            # We need to get the complete records from our main database
            content_items = []
            for item_id in matching_ids:
                # Query PostgreSQL for the full item
                db_item = self.db_manager.session.query(ContentItem).filter_by(id=int(item_id)).first()
                if db_item:
                    content_items.append(db_item)

            logger.info(f"Retrieved {len(content_items)} full content items")
            return content_items

        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []

    def get_collection_count(self) -> int:
        """
        Get the number of items in the vector database.

        Returns:
            Number of embeddings stored
        """
        try:
            return self.collection.count()
        except Exception:
            return 0

    def reset_collection(self):
        """
        Delete all embeddings and reset the collection.

        WARNING: This deletes all vector data! Use with caution.
        """
        logger.warning(f"Resetting collection: {self.collection.name}")
        self.client.delete_collection(name=self.collection.name)
        self.collection = self.client.create_collection(
            name=self.collection.name,
            metadata={"description": "Rochester content embeddings for semantic search"}
        )
        logger.info("Collection reset complete")

    def close(self):
        """Close database connections."""
        self.db_manager.close()


# Singleton instance for reuse
_vector_db_manager = None

def get_vector_db_manager() -> VectorDBManager:
    """
    Get or create the singleton VectorDBManager instance.

    This ensures we only load the embedding model once.
    """
    global _vector_db_manager
    if _vector_db_manager is None:
        _vector_db_manager = VectorDBManager()
    return _vector_db_manager
