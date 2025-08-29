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

async def test_weather_skill(session_id="default"):
    """Test weather skill functionality."""
    print("🌤️ Testing Weather Skill...")
    
    # Check if API key is configured (runtime or environment)
    weather_key = Config.get_api_key("OPENWEATHER", session_id)
    if not weather_key:
        print(f"❌ OPENWEATHER_API_KEY not configured for session {session_id}")
        print(f"   Session keys: {Config._session_api_keys.get(session_id, {})}")
        print(f"   Env key: {Config.OPENWEATHER_API_KEY}")
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
    
    # Test weather query with detailed error logging
    try:
        print("🔄 Executing weather skill...")
        result = await skill_manager.execute_skill("get_weather", location="London")
        print(f"✅ Weather result: {result[:200]}...")
        return True
    except Exception as e:
        print(f"❌ Weather skill error: {str(e)}")
        import traceback
        print(f"   Full traceback: {traceback.format_exc()}")
        return False

async def test_web_search_skill(session_id="default"):
    """Test web search skill functionality."""
    print("🔍 Testing Web Search Skill...")
    
    # Check if API key is configured (runtime or environment)
    tavily_key = Config.get_api_key("TAVILY", session_id)
    if not tavily_key:
        print(f"❌ TAVILY_API_KEY not configured for session {session_id}")
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

async def test_news_skill(session_id="default"):
    """Test news skill functionality."""
    print("📰 Testing News Skill...")
    
    # Check if API key is configured (runtime or environment)
    news_key = Config.get_api_key("NEWS", session_id)
    if not news_key:
        print(f"❌ NEWS_API_KEY not configured for session {session_id}")
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

async def test_function_definitions(session_id="default"):
    """Test that function definitions are properly generated."""
    print("🔧 Testing Function Definitions...")
    
    # Initialize skill manager with all skills
    skill_manager = SkillManager(
        tavily_api_key=Config.get_api_key("TAVILY", session_id),
        weather_api_key=Config.get_api_key("OPENWEATHER", session_id),
        news_api_key=Config.get_api_key("NEWS", session_id),
        translate_api_key=Config.get_api_key("GOOGLE_TRANSLATE", session_id)
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
    
    # Test with a test API key to see if the skill system works
    test_session = "test_session"
    
    # Set test API keys for debugging (proper format)
    print("🔧 Setting test API keys...")
    Config.set_api_key("OPENWEATHER", "12345678901234567890123456789012", test_session)  # 32 chars alphanumeric
    Config.set_api_key("TAVILY", "tvly-1234567890abcdef1234567890", test_session)  # Tavily format
    Config.set_api_key("NEWS", "abcdef1234567890abcdef1234567890", test_session)  # 32 chars alphanumeric
    Config.set_api_key("GOOGLE_TRANSLATE", "AIzaSyTest_translate_key_for_debugging_12345", test_session)
    
    results = []
    
    # Test function definitions
    results.append(await test_function_definitions(test_session))
    
    # Test individual skills with test session
    results.append(await test_weather_skill(test_session))
    results.append(await test_web_search_skill(test_session))
    results.append(await test_news_skill(test_session))
    
    print("\n" + "=" * 50)
    print(f"🏴‍☠️ Test Results: {sum(results)}/{len(results)} skills working")
    
    if all(results):
        print("✅ All skills are ready for adventure!")
    else:
        print("❌ Some skills need attention, matey!")
        print("\n💡 Issues found:")
        print("1. Check API key configuration in the web interface")
        print("2. Verify skill initialization in Complete Voice Agent")
        print("3. Test with real API keys through the browser")

if __name__ == "__main__":
    asyncio.run(main())
