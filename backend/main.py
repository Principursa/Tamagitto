"""Tamagitto FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import routers
from routers import (
    auth_router,
    repositories_router,
    entities_router,
    analysis_router,
    webhooks_router,
    websocket_router
)

# Create FastAPI app
app = FastAPI(
    title="Tamagitto API",
    description="Developer Monitoring Tamagotchi Backend",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "chrome-extension://*",
        "https://tamagitto.xyz",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(repositories_router, prefix="/api")
app.include_router(entities_router, prefix="/api") 
app.include_router(analysis_router, prefix="/api")
app.include_router(webhooks_router)
app.include_router(websocket_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Tamagitto API is running!", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "tamagitto-backend",
        "timestamp": "2025-09-27T19:50:00Z"
    }


@app.get("/api/status")
async def api_status():
    """API status endpoint."""
    return {
        "api": "Tamagitto Developer Monitoring API",
        "status": "operational",
        "endpoints": {
            "auth": "/api/auth/*",
            "repositories": "/api/repositories",
            "entities": "/api/entities/*",
            "analysis": "/api/analysis/*",
            "webhooks": "/api/webhook/*",
            "websocket": "/api/ws"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)