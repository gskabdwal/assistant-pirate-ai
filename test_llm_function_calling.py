#!/usr/bin/env python3
"""
Test script to debug LLM function calling 'object' error.
"""
import asyncio
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.config import Config
from app.services.llm_service import LLMService
from app.services.skills.skill_manager import SkillManager

async def test_llm_function_calling():
    """Test LLM function calling directly to isolate the 'object' error."""
    print("🏴‍☠️ Testing LLM Function Calling...")
    
    # Initialize services
    skill_manager = SkillManager(
        tavily_api_key=Config.TAVILY_API_KEY,
        weather_api_key=Config.OPENWEATHER_API_KEY,
        news_api_key=Config.NEWS_API_KEY
    )
    
    llm_service = LLMService(api_key=Config.GEMINI_API_KEY, skill_manager=skill_manager)
    
    # Test queries that should trigger function calls
    test_queries = [
        "Search for Python tutorials",
        "What's the weather in London?",
        "Get me the latest tech news"
    ]
    
    for query in test_queries:
        print(f"\n🧪 Testing: '{query}'")
        
        try:
            # Test regular generate_response
            print("  📝 Testing generate_response...")
            response = await llm_service.generate_response(query)
            print(f"  ✅ Response: {response[:100]}...")
            
        except Exception as e:
            print(f"  ❌ generate_response error: {str(e)}")
            print(f"  🔍 Error type: {type(e)}")
        
        try:
            # Test streaming response
            print("  🌊 Testing stream_response...")
            chunks = []
            async for chunk in llm_service.stream_response(query):
                chunks.append(chunk)
                if len(chunks) > 5:  # Just get first few chunks
                    break
            
            print(f"  ✅ Streaming chunks: {len(chunks)}")
            print(f"  📄 First chunk: {chunks[0] if chunks else 'No chunks'}")
            
        except Exception as e:
            print(f"  ❌ stream_response error: {str(e)}")
            print(f"  🔍 Error type: {type(e)}")
            print(f"  📋 Error details: {repr(e)}")

async def test_skill_manager_directly():
    """Test skill manager function definitions."""
    print("\n🔧 Testing Skill Manager Function Definitions...")
    
    skill_manager = SkillManager(
        tavily_api_key=Config.TAVILY_API_KEY,
        weather_api_key=Config.OPENWEATHER_API_KEY,
        news_api_key=Config.NEWS_API_KEY
    )
    
    functions = skill_manager.get_skill_functions()
    print(f"✅ Generated {len(functions)} functions")
    
    for i, func in enumerate(functions):
        print(f"  {i+1}. Type: {type(func)}")
        if isinstance(func, dict):
            print(f"     Keys: {list(func.keys())}")
        else:
            print(f"     Attributes: {dir(func)}")

async def main():
    """Run all tests."""
    print("🏴‍☠️ Captain Blackbeard's Function Calling Debug Voyage!")
    print("=" * 60)
    
    # Load configuration
    Config.setup_logging()
    Config.validate_config()
    
    await test_skill_manager_directly()
    await test_llm_function_calling()
    
    print("\n" + "=" * 60)
    print("🏴‍☠️ Debug voyage complete!")

if __name__ == "__main__":
    asyncio.run(main())
