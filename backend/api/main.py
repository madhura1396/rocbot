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
    # max_sources is no longer used by the handler, but we keep it for API compatibility
    # in case you want to re-introduce it later. It won't cause an error.
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
    return {"name": "RocBot API", "version": "1.0.0", "status": "running"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        db = DatabaseManager()
        count = db.count_items()['total']
        db.close()
        return {"status": "healthy", "database": "connected", "items_count": count}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


# We are keeping the non-streaming endpoint for simple tests, but the UI will use /chat/stream
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Non-streaming chat endpoint. Not recommended for UI use."""
    try:
        logger.info(f"Non-streaming chat request: {request.message} (conv: {request.conversation_id})")
        handler = get_rag_handler()
        # The old handler.ask() method is no longer in the final version. 
        # This endpoint will now fail unless you re-add a non-streaming 'ask' method.
        # For now, we focus on the streaming endpoint.
        raise HTTPException(status_code=404, detail="This non-streaming endpoint is deprecated. Please use /api/chat/stream.")
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint - returns answer word-by-word."""
    try:
        logger.info(f"Streaming chat request: {request.message}")
        
        async def generate():
            handler = get_rag_handler()
            try:
                # --- THIS IS THE FIX ---
                # The call to ask_stream now only passes the arguments it expects.
                for chunk in handler.ask_stream(
                    question=request.message,
                    conversation_id=request.conversation_id
                ):
                    data = json.dumps(chunk)
                    yield f"data: {data}\n\n"
                    await asyncio.sleep(0.01)
                
                yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            except Exception as e:
                logger.error(f"Error during stream generation: {e}")
                yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")
    
    except Exception as e:
        logger.error(f"Error setting up stream endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error setting up stream: {str(e)}")


@app.delete("/api/conversation/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """Clear conversation history."""
    try:
        handler = get_rag_handler()
        handler.clear_conversation(conversation_id)
        return {"status": "success", "message": f"Conversation {conversation_id} cleared"}
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/events")
async def get_events(limit: int = 20):
    """Get events from database."""
    try:
        db = DatabaseManager()
        events = db.get_by_category('events', limit=limit)
        db.close()
        return {"count": len(events), "events": [event.to_dict() for event in events]}
    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search")
async def search(q: str, limit: int = 10):
    """Search database for content."""
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
    try:
        db = DatabaseManager()
        results = db.search_content(q, limit=limit)
        db.close()
        return {"query": q, "count": len(results), "results": [item.to_dict() for item in results]}
    except Exception as e:
        logger.error(f"Error in search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Get database statistics."""
    try:
        db = DatabaseManager()
        stats = db.count_items()
        db.close()
        return StatsResponse(**stats)
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Run server
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    
    logger.info(f"Starting RocBot API server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)

