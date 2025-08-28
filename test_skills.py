#!/usr/bin/env python3
"""
Test script for AI Voice Agent special skills.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.config import Config
from app.services.skills.skill_manager import SkillManager

async def test_weather_skill():
    """Test weather skill functionality."""
    print("🌤️ Testing Weather Skill...")
    
    # Check if API key is configured (runtime or environment)
    weather_key = Config.get_api_key("OPENWEATHER")
    if not weather_key:
        print("❌ OPENWEATHER_API_KEY not configured")
        return False
    
    print(f"✅ Weather API key found: {weather_key[:8]}...")
    
    # Initialize skill manager
    skill_manager = SkillManager(
        weather_api_key=weather_key
    )
    
    # Test weather skill
    if "get_weather" not in skill_manager.skills:
        print("❌ Weather skill not loaded")
        return False
    
    print("✅ Weather skill loaded successfully")
    
    # Test weather query
    try:
        result = await skill_manager.execute_skill("get_weather", location="London")
        print(f"✅ Weather result: {result[:200]}...")
        return True
    except Exception as e:
        print(f"❌ Weather skill error: {str(e)}")
        return False

async def test_web_search_skill():
    """Test web search skill functionality."""
    print("🔍 Testing Web Search Skill...")
    
    # Check if API key is configured (runtime or environment)
    tavily_key = Config.get_api_key("TAVILY")
    if not tavily_key:
        print("❌ TAVILY_API_KEY not configured")
        return False
    
    print(f"✅ Tavily API key found: {tavily_key[:8]}...")
    
    # Initialize skill manager
    skill_manager = SkillManager(
        tavily_api_key=tavily_key
    )
    
    # Test web search skill
    if "search_web" not in skill_manager.skills:
        print("❌ Web search skill not loaded")
        return False
    
    print("✅ Web search skill loaded successfully")
    
    # Test search query
    try:
        result = await skill_manager.execute_skill("search_web", query="Python programming")
        print(f"✅ Search result: {result[:200]}...")
        return True
    except Exception as e:
        print(f"❌ Web search skill error: {str(e)}")
        return False

async def test_news_skill():
    """Test news skill functionality."""
    print("📰 Testing News Skill...")
    
    # Check if API key is configured (runtime or environment)
    news_key = Config.get_api_key("NEWS")
    if not news_key:
        print("❌ NEWS_API_KEY not configured")
        return False
    
    print(f"✅ News API key found: {news_key[:8]}...")
    
    # Initialize skill manager
    skill_manager = SkillManager(
        news_api_key=news_key
    )
    
    # Test news skill
    if "get_news" not in skill_manager.skills:
        print("❌ News skill not loaded")
        return False
    
    print("✅ News skill loaded successfully")
    
    # Test news query
    try:
        result = await skill_manager.execute_skill("get_news", category="technology")
        print(f"✅ News result: {result[:200]}...")
        return True
    except Exception as e:
        print(f"❌ News skill error: {str(e)}")
        return False

async def test_function_definitions():
    """Test that function definitions are properly generated."""
    print("🔧 Testing Function Definitions...")
    
    # Initialize skill manager with all skills
    skill_manager = SkillManager(
        tavily_api_key=Config.get_api_key("TAVILY"),
        weather_api_key=Config.get_api_key("OPENWEATHER"),
        news_api_key=Config.get_api_key("NEWS"),
        translate_api_key=Config.get_api_key("GOOGLE_TRANSLATE")
    )
    
    # Get function definitions
    functions = skill_manager.get_skill_functions()
    
    if not functions:
        print("❌ No function definitions generated")
        return False
    
    print(f"✅ Generated {len(functions)} function definitions:")
    for func in functions:
        # Handle both dict and object formats
        if isinstance(func, dict):
            name = func.get('name', 'Unknown')
            description = func.get('description', 'No description')
        else:
            name = getattr(func, 'name', 'Unknown')
            description = getattr(func, 'description', 'No description')
        
        print(f"  - {name}: {description}")
    
    return True

async def main():
    """Run all skill tests."""
    print("🏴‍☠️ Captain Blackbeard's Skill Testing Voyage!")
    print("=" * 50)
    
    # Load configuration
    Config.setup_logging()
    Config.validate_config()
    
    results = []
    
    # Test function definitions
    results.append(await test_function_definitions())
    
    # Test individual skills
    results.append(await test_weather_skill())
    results.append(await test_web_search_skill())
    results.append(await test_news_skill())
    
    print("\n" + "=" * 50)
    print(f"🏴‍☠️ Test Results: {sum(results)}/{len(results)} skills working")
    
    if all(results):
        print("✅ All skills are ready for adventure!")
    else:
        print("❌ Some skills need attention, matey!")
        print("\n💡 Make sure to:")
        print("1. Copy .env.example to .env")
        print("2. Add your API keys to .env file")
        print("3. Install dependencies: pip install -r requirements.txt")

if __name__ == "__main__":
    asyncio.run(main())
