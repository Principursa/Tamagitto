"""Tamagitto FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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