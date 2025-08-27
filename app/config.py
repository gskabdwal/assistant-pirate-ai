"""
Configuration settings for the AI Voice Agent.
"""
import os
import logging
import sys
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
    
    # Special Skills API Keys (Day 25)
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")
    
    # Translation Skill API Key (Day 26)
    GOOGLE_TRANSLATE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY")
    
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
        
        # Check special skills API keys (optional)
        skill_keys = []
        if cls.TAVILY_API_KEY:
            skill_keys.append("Web Search")
        if cls.OPENWEATHER_API_KEY:
            skill_keys.append("Weather")
        if cls.NEWS_API_KEY:
            skill_keys.append("News")
        if cls.GOOGLE_TRANSLATE_API_KEY:
            skill_keys.append("Translation")
        
        if skill_keys:
            logging.info(f"Special skills enabled: {', '.join(skill_keys)}")
        else:
            logging.info("No special skills API keys configured")
    
    @classmethod
    def setup_directories(cls) -> None:
        """Create necessary directories."""
        cls.UPLOAD_DIR.mkdir(exist_ok=True)
        logging.info(f"Upload directory: {cls.UPLOAD_DIR}")
    
    @classmethod
    def setup_logging(cls) -> None:
        """Setup application logging with Windows Unicode support."""
        # Configure handlers with UTF-8 encoding for Windows
        handlers = []
        
        # Console handler with UTF-8 encoding
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, cls.LOG_LEVEL))
        console_handler.setFormatter(logging.Formatter(cls.LOG_FORMAT))
        
        # Set UTF-8 encoding for Windows console
        if sys.platform.startswith('win'):
            try:
                console_handler.stream.reconfigure(encoding='utf-8')
            except AttributeError:
                # Fallback for older Python versions
                pass
        
        handlers.append(console_handler)
        
        # File handler with UTF-8 encoding
        try:
            file_handler = logging.FileHandler(cls.BASE_DIR / "app.log", encoding='utf-8')
            file_handler.setLevel(getattr(logging, cls.LOG_LEVEL))
            file_handler.setFormatter(logging.Formatter(cls.LOG_FORMAT))
            handlers.append(file_handler)
        except Exception:
            logging.warning("Could not create file handler")
        
        logging.basicConfig(
            level=getattr(logging, cls.LOG_LEVEL),
            format=cls.LOG_FORMAT,
            handlers=handlers,
            force=True
        )
        
        # Set specific loggers
        logging.getLogger("uvicorn").setLevel(logging.INFO)
        logging.getLogger("fastapi").setLevel(logging.INFO)
        
        logging.info(f"Logging configured at {cls.LOG_LEVEL} level")


# Initialize configuration on import
Config.setup_logging()
Config.validate_config()
Config.setup_directories()
