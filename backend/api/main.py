"""FastAPI server for RocBot."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
from loguru import logger
from dotenv import load_dotenv
import json
import asyncio

from backend.rag.llm_handler import get_rag_handler
from backend.database.db_manager import DatabaseManager

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="RocBot API",
    description="AI-powered Rochester, NY information assistant",
    version="1.0.0"
)

# Configure CORS (allow frontend to call API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = "default"
    max_sources: Optional[int] = 5

class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict]
    query: str
    conversation_id: str

class StatsResponse(BaseModel):
    total: int
    by_source: Dict[str, int]
    by_category: Dict[str, int]


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "name": "RocBot API",
        "version": "1.0.0",
        "status": "running",
        "features": ["conversation_history", "streaming", "caching", "fallback"],
        "endpoints": {
            "chat": "POST /api/chat",
            "chat_stream": "POST /api/chat/stream",
            "events": "GET /api/events",
            "search": "GET /api/search?q=query",
            "stats": "GET /api/stats",
            "health": "GET /api/health"
        }
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        db = DatabaseManager()
        count = db.count_items()['total']
        db.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "items_count": count,
            "ollama": "available"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint - ask a question, get an AI answer.
    Maintains conversation history.
    
    Example:
        POST /api/chat
        {
            "message": "Who is the mayor?",
            "conversation_id": "user_123_session_abc"
        }
    """
    try:
        logger.info(f"Chat request: {request.message} (conv: {request.conversation_id})")
        
        # Get RAG handler and process question
        handler = get_rag_handler()
        result = handler.ask(
            question=request.message,
            conversation_id=request.conversation_id,
            max_sources=request.max_sources
        )
        
        logger.info(f"Chat response generated with {len(result['sources'])} sources")
        
        return ChatResponse(**result)
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint - returns answer word-by-word.
    Uses Server-Sent Events (SSE) for real-time streaming.
    
    Example:
        POST /api/chat/stream
        {
            "message": "Tell me about Rochester",
            "conversation_id": "user_123"
        }
    """
    try:
        logger.info(f"Streaming chat request: {request.message}")
        
        async def generate():
            """Generator for streaming response."""
            handler = get_rag_handler()
            
            try:
                for chunk in handler.ask_stream(
                    question=request.message,
                    conversation_id=request.conversation_id,
                    max_sources=request.max_sources
                ):
                    # Send Server-Sent Event format
                    data = json.dumps(chunk)
                    yield f"data: {data}\n\n"
                    
                    # Small delay to prevent overwhelming the client
                    await asyncio.sleep(0.01)
                
                # Send final completion message
                yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                
            except Exception as e:
                logger.error(f"Error in streaming: {e}")
                error_chunk = {
                    'type': 'error',
                    'data': f"Error: {str(e)}"
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    except Exception as e:
        logger.error(f"Error in stream endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error streaming: {str(e)}")


@app.delete("/api/conversation/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """
    Clear conversation history for a specific conversation ID.
    
    Example:
        DELETE /api/conversation/user_123
    """
    try:
        handler = get_rag_handler()
        handler.clear_conversation(conversation_id)
        
        return {
            "status": "success",
            "message": f"Conversation {conversation_id} cleared",
            "conversation_id": conversation_id
        }
    
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/api/events")
async def get_events(limit: int = 20):
    """
    Get events from database.
    
    Example:
        GET /api/events?limit=10
    """
    try:
        db = DatabaseManager()
        events = db.get_by_category('events', limit=limit)
        db.close()
        
        # Convert to dict
        events_list = [event.to_dict() for event in events]
        
        return {
            "count": len(events_list),
            "events": events_list
        }
    
    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching events: {str(e)}")


@app.get("/api/search")
async def search(q: str, limit: int = 10):
    """
    Search database for content.
    
    Example:
        GET /api/search?q=mayor&limit=5
    """
    try:
        if not q or len(q.strip()) == 0:
            raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
        
        db = DatabaseManager()
        results = db.search_content(q, limit=limit)
        db.close()
        
        # Convert to dict
        results_list = [item.to_dict() for item in results]
        
        return {
            "query": q,
            "count": len(results_list),
            "results": results_list
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in search: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching: {str(e)}")


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """
    Get database statistics.
    
    Example:
        GET /api/stats
    """
    try:
        db = DatabaseManager()
        stats = db.count_items()
        db.close()
        
        return StatsResponse(**stats)
    
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")


# Run server
if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    
    logger.info(f"Starting RocBot API server on {host}:{port}")
    logger.info("Features: Conversation History, Streaming, Caching, Fallback")
    logger.info("API Documentation available at: http://localhost:8000/docs")
    
    uvicorn.run(app, host=host, port=port)