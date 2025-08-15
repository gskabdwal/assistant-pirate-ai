"""
AI Voice Agent - Entry Point
This file serves as the main entry point for the refactored application.
"""
import uvicorn
from app.main import app
from app.config import Config


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG
    )
