"""
Configuration settings for the AI Voice Agent.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration."""
    
    # API Keys
    MURF_API_KEY = os.getenv("MURF_API_KEY")
    ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Application settings
    APP_TITLE = "AI Voice Agent"
    APP_VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # Server settings
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    
    # File paths
    BASE_DIR = Path(__file__).resolve().parent.parent
    UPLOAD_DIR = BASE_DIR / "uploads"
    STATIC_DIR = BASE_DIR / "static"
    TEMPLATES_DIR = BASE_DIR / "templates"
    
    # Logging configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Service limits
    MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_TTS_CHARS = 3000
    MAX_CHAT_HISTORY = 10
    
    @classmethod
    def validate_config(cls) -> None:
        """Validate required configuration."""
        missing_keys = []
        
        if not cls.MURF_API_KEY:
            missing_keys.append("MURF_API_KEY")
        
        if not cls.ASSEMBLYAI_API_KEY:
            missing_keys.append("ASSEMBLYAI_API_KEY")
        
        if not cls.GEMINI_API_KEY:
            missing_keys.append("GEMINI_API_KEY")
        
        if missing_keys:
            logging.warning(f"Missing API keys: {', '.join(missing_keys)}")
            logging.warning("Some functionality may not work properly.")
    
    @classmethod
    def setup_directories(cls) -> None:
        """Create necessary directories."""
        cls.UPLOAD_DIR.mkdir(exist_ok=True)
        logging.info(f"Upload directory: {cls.UPLOAD_DIR}")
    
    @classmethod
    def setup_logging(cls) -> None:
        """Setup application logging."""
        logging.basicConfig(
            level=getattr(logging, cls.LOG_LEVEL),
            format=cls.LOG_FORMAT,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(cls.BASE_DIR / "app.log")
            ]
        )
        
        # Set specific loggers
        logging.getLogger("uvicorn").setLevel(logging.INFO)
        logging.getLogger("fastapi").setLevel(logging.INFO)
        
        logging.info(f"Logging configured at {cls.LOG_LEVEL} level")


# Initialize configuration on import
Config.setup_logging()
Config.validate_config()
Config.setup_directories()
