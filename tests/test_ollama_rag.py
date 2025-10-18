"""Test Ollama with database content (RAG - Retrieval Augmented Generation)."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import ollama
from loguru import logger
from backend.database.db_manager import DatabaseManager


def ask_ollama_with_database(question: str, db: DatabaseManager):
    """Ask Ollama a question using database search for context."""
    
    print("\n" + "="*60)
    print(f"❓ QUESTION: {question}")
    print("="*60)
    
    # Step 1: Search database for relevant content
    print(f"\n🔍 Searching database for relevant content...")
    relevant_items = db.search_content(question, limit=5)
    
    if not relevant_items:
        print("⚠️  No relevant content found in database")
        return None
    
    print(f"✅ Found {len(relevant_items)} relevant items:")
    for i, item in enumerate(relevant_items, 1):
        print(f"   {i}. {item.title} ({item.source} - {item.category})")
    
    # Step 2: Build context from relevant items
    context = ""
    for i, item in enumerate(relevant_items, 1):
        context += f"\n--- Source {i}: {item.title} ({item.source}) ---\n"
        context += f"URL: {item.url}\n"
        context += item.content_full[:2000]  # Limit to 2000 chars per item
        context += "\n\n"
    
    # Step 3: Create the prompt
    prompt = f"""You are RocBot, an AI assistant that helps people learn about Rochester, NY - including city services, events, meetups, and community information.

Based on the following information from official sources (City of Rochester website, Eventbrite, and Meetup), please answer the user's question.

CONTEXT FROM DATABASE:
{context}

USER QUESTION: {question}

Please provide a helpful, accurate answer based on the context above. If you mention specific events or services, include relevant details like dates, locations, or links when available. If the context doesn't contain enough information to answer, say so.

ANSWER:"""
    
    # Step 4: Ask Ollama
    print("\n" + "="*60)
    print("🤖 Asking Ollama (llama3.2)...")
    print("="*60)
    
    try:
        response = ollama.chat(
            model='llama3.2:latest',
            messages=[
                {
                    'role': 'user',
                    'content': prompt
                }
            ]
        )
        
        answer = response['message']['content']
        
        print("\n💬 ANSWER:")
        print("-" * 60)
        print(answer)
        print("-" * 60)
        
        return answer
    
    except Exception as e:
        print(f"❌ ERROR calling Ollama: {e}")
        print("\nMake sure Ollama is running:")
        print("  Check with: ollama list")
        return None


def test_rag_with_database():
    """Test the complete RAG system using database."""
    
    print("\n" + "="*60)
    print("🧪 TESTING RAG SYSTEM WITH DATABASE")
    print("="*60)
    
    # Connect to database
    print("\n📁 Connecting to database...")
    db = DatabaseManager()
    
    # Get stats
    stats = db.count_items()
    print(f"✅ Database connected!")
    print(f"   Total items: {stats['total']}")
    print(f"   Sources: {stats['by_source']}")
    print(f"   Categories: {stats['by_category']}")
    
    # Test questions
    test_questions = [
        "Who is the mayor of Rochester?",
        "What events are happening in Rochester this week?",
        "Are there any tech meetups in Rochester?",
        "How do I contact the city of Rochester?",
        "What python or programming groups exist in Rochester?"
    ]
    
    for question in test_questions:
        answer = ask_ollama_with_database(question, db)
        
        if not answer:
            print("\n⚠️  Skipping to next question...")
            continue
        
        print("\n⏸️  Press Enter to continue to next question...")
        input()
    
    db.close()
    print("\n" + "="*60)
    print("✅ RAG SYSTEM TEST COMPLETE!")
    print("="*60)


if __name__ == "__main__":
    print("\n🎯 DATABASE-POWERED RAG SYSTEM TEST")
    print("="*60)
    print("This test will:")
    print("  1. Connect to your PostgreSQL database")
    print("  2. Search for relevant content based on questions")
    print("  3. Ask Ollama to answer using that context")
    print("  4. Test with 5 different questions")
    print("\n⚠️  IMPORTANT: Make sure Ollama is running!")
    
    input("\n📍 Press Enter when ready...")
    
    test_rag_with_database()