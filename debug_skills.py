#!/usr/bin/env python3
"""
Debug script to test web search and news skills directly
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

# Add the app directory to Python path
sys.path.append('.')

from app.services.skills.web_search_skill import WebSearchSkill
from app.services.skills.news_skill import NewsSkill

async def test_web_search():
    print("Testing Web Search Skill...")
    try:
        load_dotenv()
        api_key = os.getenv('TAVILY_API_KEY')
        if not api_key:
            print("TAVILY_API_KEY not found")
            return
        
        skill = WebSearchSkill(api_key)
        result = await skill.execute("python tutorials", 2)
        print(f"Web Search Result: {result[:200]}...")
    except Exception as e:
        print(f"Web Search Error: {e}")

async def test_news():
    print("\nTesting News Skill...")
    try:
        load_dotenv()
        api_key = os.getenv('NEWS_API_KEY')
        if not api_key:
            print("NEWS_API_KEY not found")
            return
        
        skill = NewsSkill(api_key)
        result = await skill.execute(category="technology", max_articles=2)
        print(f"News Result: {result[:200]}...")
    except Exception as e:
        print(f"News Error: {e}")

async def main():
    await test_web_search()
    await test_news()

if __name__ == "__main__":
    asyncio.run(main())
