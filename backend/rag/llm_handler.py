"""LLM handler for RAG system using Ollama."""
import sys, os, hashlib, ollama, time
from typing import Dict, List, Generator
from loguru import logger
from backend.database.db_manager import DatabaseManager
from backend.database.models import ContentItem
from groq import Groq

class RAGHandler:
    def __init__(self, model: str = os.getenv('OLLAMA_MODEL', 'llama3.2:latest')):
        self.model = model
        self.db = DatabaseManager()
        self.conversations = {}
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_client = Groq(api_key=self.groq_api_key) if self.groq_api_key else None
        logger.info("Groq client initialized." if self.groq_client else "No GROQ_API_KEY, using local Ollama.")

    def ask_stream(self, question: str, conversation_id: str = "default") -> Generator:
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []

        history = self.conversations.get(conversation_id, [])[-6:]
        
        # 1. Get relevant documents from the database
        relevant_items = self.db.search_content(question, limit=3)

        # 2. If we found relevant items, try to generate a RAG answer silently
        full_rag_answer = None
        if relevant_items:
            context = self._build_context(relevant_items)
            full_rag_answer = self._generate_full_answer(question, context, history)

        # 3. Check if the RAG answer is insufficient or if we never found documents
        insufficient_phrases = ["couldn't find", "don't have information", "not in the provided context", "unable to find"]
        is_insufficient = not full_rag_answer or any(phrase in full_rag_answer.lower() for phrase in insufficient_phrases)

        # 4. DECIDE: Stream the good RAG answer OR stream the fallback answer
        if is_insufficient:
            logger.warning(f"RAG answer insufficient for '{question}'. Using fallback.")
            yield from self._stream_fallback_response(question, conversation_id)
        else:
            logger.info(f"Streaming good RAG answer for '{question}'.")
            sources = self._format_sources(relevant_items)
            yield {'type': 'sources', 'data': sources}
            
            self._add_to_history(conversation_id, question, full_rag_answer)

            for chunk in self._stream_text_in_chunks(full_rag_answer):
                yield {'type': 'token', 'data': chunk}
            
            yield {'type': 'done', 'data': {'conversation_id': conversation_id}}

    def _stream_fallback_response(self, question, conversation_id):
        """Helper to generate and stream a fallback response."""
        history = self.conversations.get(conversation_id, [])[-6:]
        fallback_stream = self._generate_fallback_stream(question, history)
        
        full_fallback_answer = ""
        for chunk in fallback_stream:
            full_fallback_answer += chunk
            yield {'type': 'token', 'data': chunk}

        self._add_to_history(conversation_id, question, full_fallback_answer)
        yield {'type': 'done', 'data': {'sources': [], 'conversation_id': conversation_id}}

    def _add_to_history(self, conversation_id, question, answer):
        self.conversations[conversation_id].append({'role': 'user', 'content': question})
        self.conversations[conversation_id].append({'role': 'assistant', 'content': answer})

    def _build_context(self, items: List[ContentItem]) -> str:
        return "\n\n".join([f"--- Source: {item.title}\nURL: {item.url}\n{item.content_full[:1500]}" for item in items])

    def _stream_text_in_chunks(self, text: str, chunk_size: int = 5) -> Generator[str, None, None]:
        """Yields a string in small chunks to simulate a stream."""
        for i in range(0, len(text), chunk_size):
            yield text[i:i + chunk_size]
            time.sleep(0.01) # Small delay for a better streaming feel

    def _generate_full_answer(self, question: str, context: str, history: List[Dict]) -> str:
        """Generates a complete, non-streaming answer for checking."""
        system_prompt = f"You are RocBot. Use ONLY the provided context to answer. If the context doesn't have the answer, you MUST say 'I couldn't find information about that'.\n\nCONTEXT:\n{context}"
        messages = [{'role': 'system', 'content': system_prompt}] + history + [{'role': 'user', 'content': question}]
        
        try:
            if self.groq_client:
                response = self.groq_client.chat.completions.create(messages=messages, model="llama3-8b-8192")
                return response.choices[0].message.content
            else:
                response = ollama.chat(model=self.model, messages=messages)
                return response['message']['content']
        except Exception as e:
            logger.error(f"Error in full answer generation: {e}")
            return "I couldn't find information about that due to an error."

    def _generate_fallback_stream(self, question: str, history: List[Dict]) -> Generator[str, None, None]:
        """Generates a fallback answer word-by-word."""
        system_prompt = "You are RocBot. The user asked a question not in your local database. You MUST start your answer with: '⚠️ **Note:** I don't have this in my Rochester database, so I'm using my general training data. Please verify this from official sources.' Then, answer the question using your general knowledge."
        messages = [{'role': 'system', 'content': system_prompt}] + history + [{'role': 'user', 'content': question}]
        
        try:
            if self.groq_client:
                stream = self.groq_client.chat.completions.create(messages=messages, model="llama3-8b-8192", stream=True)
                for chunk in stream:
                    if chunk.choices[0].delta.content: yield chunk.choices[0].delta.content
            else:
                stream = ollama.chat(model=self.model, messages=messages, stream=True)
                for chunk in stream:
                    if chunk['message']['content']: yield chunk['message']['content']
        except Exception as e:
            logger.error(f"Error in fallback stream: {e}")
            yield "There was an error generating a fallback response."

    def _format_sources(self, items: List[ContentItem]) -> List[Dict]:
        return [{'title': item.title, 'url': item.url, 'source': item.source, 'category': item.category} for item in items]

_rag_handler = None
def get_rag_handler() -> RAGHandler:
    global _rag_handler
    if _rag_handler is None: _rag_handler = RAGHandler()
    return _rag_handler
