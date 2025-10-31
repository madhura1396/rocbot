"""
Test script to compare keyword search vs semantic search.

This demonstrates the improvements from semantic search.
"""
from backend.database.db_manager import DatabaseManager
from backend.database.vector_db_manager import get_vector_db_manager
from backend.database.models import init_db

# Initialize
init_db()
db_keyword = DatabaseManager()
db_semantic = get_vector_db_manager()

# Test queries that semantic search handles better
test_queries = [
    "outdoor activities",           # Synonyms for "parks", "recreation"
    "family fun",                  # Related to "events", "parks"
    "upcoming gatherings",         # Synonym for "events"
    "recreational areas",          # Synonym for "parks"
    "municipal services"           # Synonym for "city government"
]

print("\n" + "="*80)
print("SEMANTIC SEARCH vs KEYWORD SEARCH COMPARISON")
print("="*80)

for query in test_queries:
    print(f"\n🔍 Query: '{query}'")
    print("-" * 80)

    # Keyword search
    keyword_results = db_keyword.search_content(query, limit=3)
    print(f"\n📝 KEYWORD SEARCH ({len(keyword_results)} results):")
    if keyword_results:
        for i, item in enumerate(keyword_results, 1):
            print(f"  {i}. {item.title[:60]}")
    else:
        print("  ❌ No results found")

    # Semantic search
    semantic_results = db_semantic.semantic_search(query, limit=3)
    print(f"\n🤖 SEMANTIC SEARCH ({len(semantic_results)} results):")
    if semantic_results:
        for i, item in enumerate(semantic_results, 1):
            print(f"  {i}. {item.title[:60]}")
    else:
        print("  ❌ No results found")

print("\n" + "="*80)
print("SUMMARY:")
print("- Keyword search only matches exact words")
print("- Semantic search understands meaning and finds related content")
print("="*80 + "\n")

# Clean up
db_keyword.close()
db_semantic.close()
