# server/src/server/main.py
"""
DroneSphere Server Main Application

FastAPI-based server that provides REST and WebSocket APIs for drone control.

Usage:
    uvicorn server.main:app --reload
"""

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import API modules directly
from server.api import chat, commands, drones, websocket
from server.core.config import get_settings
from server.core.logging import setup_logging

# Load environment variables
load_dotenv()

# Setup logging
setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting DroneSphere Server", version="0.1.0")

    # Initialize services here
    # TODO: Initialize command registry, LLM service, etc.

    yield

    # Shutdown
    logger.info("Shutting down DroneSphere Server")

    # Cleanup resources here


# Create FastAPI application
app = FastAPI(
    title="DroneSphere API",
    description="AI-powered drone control system API",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(commands.router, prefix="/api/v1/commands", tags=["commands"])
app.include_router(drones.router, prefix="/api/v1/drones", tags=["drones"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "DroneSphere API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "dronesphere-server", "version": "0.1.0"}


# Mount static files if web directory exists
web_dir = Path(__file__).parent.parent.parent.parent / "web" / "dist"
if web_dir.exists():
    app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="static")
    logger.info("Serving static files from", path=str(web_dir))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
