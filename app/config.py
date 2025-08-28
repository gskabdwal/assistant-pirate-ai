"""
Configuration settings for the AI Voice Agent.
"""
import os
import sys
import logging
from pathlib import Path
from typing import Optional

# Load environment variables from .env file
from dotenv import load_dotenv

# Get the base directory and load .env file
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / '.env'
print(f" Loading .env from: {env_path}")
print(f" .env file exists: {env_path.exists()}")

load_dotenv(env_path)


class Config:
    """Application configuration."""
    
    # API Keys - Default to environment variables, can be overridden by frontend
    MURF_API_KEY = os.getenv("MURF_API_KEY")
    ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Special Skills API Keys (Day 25)
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")
    
    # Translation Skill API Key (Day 26)
    GOOGLE_TRANSLATE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY")
    
    # Runtime API keys (can be set by frontend)
    _runtime_api_keys = {}
    
    @classmethod
    def set_api_key(cls, service: str, api_key: str) -> None:
        """Set API key at runtime with basic validation."""
        service_upper = service.upper()
        if api_key and api_key.strip():
            cleaned_key = api_key.strip()
            
            # Basic API key format validation
            if cls._validate_api_key_format(service_upper, cleaned_key):
                cls._runtime_api_keys[service_upper] = cleaned_key
            else:
                raise ValueError(f"Invalid API key format for {service_upper}")
        else:
            # Remove the key if empty
            cls._runtime_api_keys.pop(service_upper, None)
    
    @classmethod
    def _validate_api_key_format(cls, service: str, api_key: str) -> bool:
        """Basic API key format validation."""
        # Minimum length check
        if len(api_key) < 10:
            return False
        
        # Service-specific format checks
        if service == 'ASSEMBLYAI':
            # AssemblyAI keys are typically 32+ chars, alphanumeric
            return len(api_key) >= 32 and api_key.replace('-', '').replace('_', '').isalnum()
        elif service == 'OPENWEATHER':
            # OpenWeather keys are typically 32 chars, alphanumeric
            return len(api_key) == 32 and api_key.isalnum()
        elif service == 'TAVILY':
            # Tavily keys start with 'tvly-' and are longer
            return api_key.startswith('tvly-') and len(api_key) > 20
        elif service == 'NEWS':
            # NewsAPI keys are typically 32 chars, alphanumeric
            return len(api_key) == 32 and api_key.isalnum()
        elif service == 'GEMINI':
            # Gemini keys start with specific prefixes
            return (api_key.startswith('AIza') or api_key.startswith('AIzaSy')) and len(api_key) > 30
        elif service == 'MURF':
            # Murf keys - less strict validation
            return len(api_key) >= 20
        elif service == 'GOOGLE_TRANSLATE':
            # Google Cloud keys
            return (api_key.startswith('AIza') or api_key.startswith('AIzaSy')) and len(api_key) > 30
        
        # Default: just check minimum length
        return len(api_key) >= 10
    
    @classmethod
    def get_api_key(cls, service: str) -> str:
        """Get API key, prioritizing runtime keys over environment variables."""
        service_upper = service.upper()
        
        # Check runtime keys first
        if service_upper in cls._runtime_api_keys:
            return cls._runtime_api_keys[service_upper]
        
        # Fallback to environment variables
        env_key_map = {
            'MURF': cls.MURF_API_KEY,
            'ASSEMBLYAI': cls.ASSEMBLYAI_API_KEY,
            'GEMINI': cls.GEMINI_API_KEY,
            'TAVILY': cls.TAVILY_API_KEY,
            'OPENWEATHER': cls.OPENWEATHER_API_KEY,
            'NEWS': cls.NEWS_API_KEY,
            'GOOGLE_TRANSLATE': cls.GOOGLE_TRANSLATE_API_KEY,
        }
        
        return env_key_map.get(service_upper, '')
    
    @classmethod
    def get_api_status(cls) -> dict:
        """Get status of all API keys."""
        services = ['MURF', 'ASSEMBLYAI', 'GEMINI', 'TAVILY', 'OPENWEATHER', 'NEWS', 'GOOGLE_TRANSLATE']
        status = {}
        
        # Debug logging
        print("🔍 DEBUG: Checking API key status...")
        print(f"🔍 Runtime keys: {list(cls._runtime_api_keys.keys())}")
        
        for service in services:
            api_key = cls.get_api_key(service)
            env_key = os.getenv(f"{service}_API_KEY")
            
            # Debug logging for each service
            print(f"🔍 {service}: runtime={service in cls._runtime_api_keys}, env_key={'✓' if env_key else '✗'}, final_key={'✓' if api_key else '✗'}")
            
            status[service.lower()] = {
                'configured': bool(api_key),
                'source': 'runtime' if service in cls._runtime_api_keys else 'environment',
                'api_key': api_key  # Include the actual API key (will be masked on frontend)
            }
        
        return status
    
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
