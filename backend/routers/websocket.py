"""WebSocket API routes for real-time updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import SessionLocal
from services.websocket_service import WebSocketService

router = APIRouter(prefix="/ws", tags=["websocket"])
websocket_service = WebSocketService()


@router.websocket("")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time updates.
    
    Clients should connect with a JWT access token as a query parameter:
    ws://localhost:8000/ws?token=your_jwt_token
    """
    if not token:
        await websocket.close(code=4000, reason="Missing authentication token")
        return
    
    db = SessionLocal()
    try:
        await websocket_service.handle_websocket_connection(websocket, token, db)
    finally:
        db.close()


@router.get("/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    return websocket_service.get_manager().get_connection_stats()


# Initialize WebSocket cleanup task
import asyncio
import threading

def start_cleanup_task():
    """Start the periodic cleanup task in background."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(websocket_service.periodic_cleanup())

# Start cleanup in background thread
cleanup_thread = threading.Thread(target=start_cleanup_task, daemon=True)
cleanup_thread.start()