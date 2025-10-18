"""LLM handler for RAG system using Ollama."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import hashlib
from datetime import datetime, timedelta
import ollama
from typing import Dict, List, Optional, Generator
from loguru import logger
from backend.database.db_manager import DatabaseManager
from backend.database.models import ContentItem


class RAGHandler:
    """Handles retrieval and generation for questions."""
    
    def __init__(self, model: str = "llama3.2:latest"):
        self.model = model
        self.db = DatabaseManager()
        self.cache = {}  # Query cache
        self.conversations = {}  # Store conversation history by conversation_id
        logger.info(f"RAGHandler initialized with model: {model}")
    
    def ask(self, question: str, conversation_id: str = "default", max_sources: int = 5) -> Dict:
        """
        Ask a question and get an AI-generated answer with sources.
        Maintains conversation history for context.
        
        Args:
            question: User's question
            conversation_id: Unique ID for this conversation thread
            max_sources: Max number of sources to retrieve
        
        Returns:
            {
                'answer': 'AI generated answer',
                'sources': [{'title': '...', 'url': '...', 'source': '...'}],
                'query': 'original question',
                'conversation_id': 'conversation_id'
            }
        """
        logger.info(f"Processing question: {question} (conversation: {conversation_id})")
        
        # Initialize conversation history if new
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        
        # Check cache first (only for first message in conversation)
        cache_key = hashlib.md5(question.lower().strip().encode()).hexdigest()
        
        if not self.conversations[conversation_id] and cache_key in self.cache:
            logger.info(f"✨ Cache hit for: {question}")
            return self.cache[cache_key]
        
        # Step 1: Search database
        relevant_items = self.db.search_content(question, limit=max_sources)
        
        # Step 2: Decide RAG or Fallback
        if not relevant_items or len(relevant_items) == 0:
            logger.warning(f"No relevant content found in database for: {question}")
            return self._handle_fallback(question, conversation_id, cache_key)
        
        # Step 3: Try RAG first
        logger.info(f"Found {len(relevant_items)} relevant sources")
        
        context = self._build_context(relevant_items)
        
        # Get conversation history (last 5 messages)
        conversation_history = self.conversations[conversation_id][-10:]  # Last 10 items (5 exchanges)
        
        answer = self._generate_answer(question, context, conversation_history)
        sources = self._format_sources(relevant_items)
        
        # Step 4: Check if RAG answer is insufficient
        insufficient_phrases = [
            "couldn't find",
            "don't have",
            "no information",
            "doesn't seem to be",
            "not mentioned",
            "no mention",
            "unfortunately"
        ]
        
        answer_lower = answer.lower()
        is_insufficient = any(phrase in answer_lower for phrase in insufficient_phrases)
        
        if is_insufficient:
            logger.info("RAG answer was insufficient, using fallback...")
            return self._handle_fallback(question, conversation_id, cache_key)
        
        # Step 5: Save to conversation history
        self.conversations[conversation_id].append({
            'role': 'user',
            'content': question
        })
        self.conversations[conversation_id].append({
            'role': 'assistant',
            'content': answer
        })
        
        result = {
            'answer': answer,
            'sources': sources,
            'query': question,
            'conversation_id': conversation_id
        }
        
        # Only cache if no prior conversation context
        if len(conversation_history) == 0:
            self.cache[cache_key] = result
            logger.info(f"💾 Cached result for: {question}")
        
        return result
    
    def ask_stream(self, question: str, conversation_id: str = "default", max_sources: int = 5) -> Generator:
        """
        Streaming version - yields answer word by word.
        
        Yields chunks of:
            {
                'type': 'sources' | 'token' | 'done',
                'data': ...
            }
        """
        logger.info(f"Processing streaming question: {question} (conversation: {conversation_id})")
        
        # Initialize conversation history if new
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        
        # Step 1: Search database
        relevant_items = self.db.search_content(question, limit=max_sources)
        
        if not relevant_items or len(relevant_items) == 0:
            # Fallback to non-streaming for now
            logger.warning("No sources for streaming, using regular response")
            result = self._handle_fallback(question, conversation_id, "")
            yield {'type': 'token', 'data': result['answer']}
            yield {'type': 'done', 'data': {'sources': [], 'conversation_id': conversation_id}}
            return
        
        # Step 2: Send sources first
        sources = self._format_sources(relevant_items)
        yield {'type': 'sources', 'data': sources}
        
        # Step 3: Stream the answer
        context = self._build_context(relevant_items)
        conversation_history = self.conversations[conversation_id][-10:]
        
        full_answer = ""
        for chunk in self._generate_answer_stream(question, context, conversation_history):
            full_answer += chunk
            yield {'type': 'token', 'data': chunk}
        
        # Step 4: Save to history
        self.conversations[conversation_id].append({
            'role': 'user',
            'content': question
        })
        self.conversations[conversation_id].append({
            'role': 'assistant',
            'content': full_answer
        })
        
        # Step 5: Send completion
        yield {'type': 'done', 'data': {'conversation_id': conversation_id}}
    
    def _handle_fallback(self, question: str, conversation_id: str, cache_key: str) -> Dict:
        """Handle fallback to Ollama's general knowledge."""
        logger.info("Attempting to answer using Ollama's general knowledge...")
        
        conversation_history = self.conversations[conversation_id][-10:]
        fallback_answer = self._generate_fallback_answer(question, conversation_history)
        
        # Save to conversation history
        self.conversations[conversation_id].append({
            'role': 'user',
            'content': question
        })
        self.conversations[conversation_id].append({
            'role': 'assistant',
            'content': fallback_answer
        })
        
        result = {
            'answer': fallback_answer,
            'sources': [],
            'query': question,
            'conversation_id': conversation_id
        }
        
        if len(conversation_history) == 0 and cache_key:
            self.cache[cache_key] = result
            logger.info(f"💾 Cached fallback result for: {question}")
        
        return result
    
    def _build_context(self, items: List[ContentItem]) -> str:
        """Build context string from content items."""
        context = ""
        for i, item in enumerate(items, 1):
            context += f"\n--- Source {i}: {item.title} ({item.source}) ---\n"
            context += f"URL: {item.url}\n"
            content = item.content_full[:2000]
            context += content + "\n\n"
        return context
    
    def _generate_answer(self, question: str, context: str, conversation_history: List[Dict]) -> str:
        """Generate answer using Ollama with RAG context and conversation history."""
        
        # Build conversation context
        history_text = ""
        if conversation_history:
            history_text = "\n\nPREVIOUS CONVERSATION:\n"
            for msg in conversation_history:
                role = "User" if msg['role'] == 'user' else "Assistant"
                history_text += f"{role}: {msg['content']}\n"
        
        prompt = f"""You are RocBot, a helpful AI assistant for Rochester, NY. You help people find information about city services, events, meetups, and community resources.

Based on the following context from official sources (City of Rochester website, Eventbrite, and Meetup), please answer the user's question accurately and helpfully.

CONTEXT:
{context}
{history_text}

CURRENT QUESTION: {question}

INSTRUCTIONS:
- Provide a clear, accurate answer based on the context above
- If this is a follow-up question, use the previous conversation for context
- Include specific details like dates, times, locations, or contact info when available
- Keep your answer concise but informative
- Use a friendly, helpful tone

ANSWER:"""
        
        try:
            logger.info("Calling Ollama for answer generation...")
            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            )
            
            answer = response['message']['content']
            logger.info("Answer generated successfully")
            return answer
            
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return f"I encountered an error generating an answer: {str(e)}."
    
    def _generate_answer_stream(self, question: str, context: str, conversation_history: List[Dict]) -> Generator[str, None, None]:
        """Generate answer using Ollama with streaming."""
        
        # Build conversation context
        history_text = ""
        if conversation_history:
            history_text = "\n\nPREVIOUS CONVERSATION:\n"
            for msg in conversation_history:
                role = "User" if msg['role'] == 'user' else "Assistant"
                history_text += f"{role}: {msg['content']}\n"
        
        prompt = f"""You are RocBot, a helpful AI assistant for Rochester, NY.

CONTEXT:
{context}
{history_text}

CURRENT QUESTION: {question}

INSTRUCTIONS:
- Provide a clear, accurate answer based on the context
- If this is a follow-up question, use the previous conversation
- Be concise and friendly

ANSWER:"""
        
        try:
            logger.info("Calling Ollama for streaming answer...")
            response = ollama.chat(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}],
                stream=True
            )
            
            for chunk in response:
                if 'message' in chunk and 'content' in chunk['message']:
                    yield chunk['message']['content']
            
            logger.info("Streaming answer complete")
            
        except Exception as e:
            logger.error(f"Error streaming from Ollama: {e}")
            yield f"Error: {str(e)}"
    
    def _generate_fallback_answer(self, question: str, conversation_history: List[Dict]) -> str:
        """Generate answer using Ollama's general knowledge."""
        
        history_text = ""
        if conversation_history:
            history_text = "\n\nPREVIOUS CONVERSATION:\n"
            for msg in conversation_history:
                role = "User" if msg['role'] == 'user' else "Assistant"
                history_text += f"{role}: {msg['content']}\n"
        
        prompt = f"""You are RocBot, an AI assistant for Rochester, NY.

The user asked a question that isn't in your local database.
{history_text}

CURRENT QUESTION: {question}

You may answer using your general knowledge, BUT:

1. Start with: "⚠️ **Note:** I don't have this in my Rochester database, so I'm using general training data. Please verify from official sources."

2. Provide a helpful answer

3. If unsure, say so and suggest where to find official info

ANSWER:"""
        
        try:
            logger.info("Calling Ollama for fallback answer...")
            response = ollama.chat(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}]
            )
            
            return response['message']['content']
            
        except Exception as e:
            logger.error(f"Error in fallback: {e}")
            return f"I couldn't find this information: {str(e)}"
    
    def _format_sources(self, items: List[ContentItem]) -> List[Dict]:
        """Format content items as source references."""
        sources = []
        for item in items:
            sources.append({
                'title': item.title,
                'url': item.url,
                'source': item.source,
                'category': item.category
            })
        return sources
    
    def clear_conversation(self, conversation_id: str):
        """Clear conversation history for a given ID."""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            logger.info(f"Cleared conversation: {conversation_id}")
    
    def close(self):
        """Close database connection."""
        self.db.close()


# Singleton instance for API use
_rag_handler = None

def get_rag_handler() -> RAGHandler:
    """Get or create RAG handler singleton."""
    global _rag_handler
    if _rag_handler is None:
        model = os.getenv('OLLAMA_MODEL', 'llama3.2:latest')
        _rag_handler = RAGHandler(model=model)
    return _rag_handler


if __name__ == "__main__":
    print("Testing RAG Handler with conversation history...")
    
    handler = RAGHandler()
    conv_id = "test_conv_1"
    
    # First question
    result1 = handler.ask("Who is the mayor of Rochester?", conv_id)
    print(f"\nQ1: {result1['query']}")
    print(f"A1: {result1['answer'][:200]}...")
    
    # Follow-up question
    result2 = handler.ask("How do I contact him?", conv_id)
    print(f"\nQ2: {result2['query']}")
    print(f"A2: {result2['answer'][:200]}...")
    
    handler.close()
    print("\n✅ Test complete!")