"""FastAPI server for RocBot."""
import sys, os, json, asyncio
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from loguru import logger
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from backend.rag.llm_handler import get_rag_handler
from backend.database.db_manager import DatabaseManager

load_dotenv()

app = FastAPI(title="RocBot API")

# --- IMPORTANT: Serve Frontend Static Files ---
# This line tells FastAPI to serve your CSS and JS files.
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = "default"

# --- API Endpoints ---

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Main streaming chat endpoint."""
    try:
        async def generate():
            handler = get_rag_handler()
            for chunk in handler.ask_stream(
                question=request.message,
                conversation_id=request.conversation_id
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        return StreamingResponse(generate(), media_type="text/event-stream")
    except Exception as e:
        logger.error(f"Error in stream endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error setting up stream")

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

# --- IMPORTANT: Catch-all endpoint to serve the index.html file ---
# This MUST be the last route in the file.
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serves the index.html file for any path not matching an API route."""
    logger.info(f"Serving index.html for path: {full_path}")
    return FileResponse("frontend/index.html")