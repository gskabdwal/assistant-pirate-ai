"""
Web search skill using Tavily API for Captain Blackbeard's Voice Agent.
"""
import httpx
import logging
from typing import Dict, Any
from .base_skill import BaseSkill

logger = logging.getLogger(__name__)


class WebSearchSkill(BaseSkill):
    """Web search skill using Tavily API."""
    
    def __init__(self, api_key: str):
        """
        Initialize web search skill.
        
        Args:
            api_key: Tavily API key
        """
        super().__init__(
            name="web_search",
            description="Search the internet for current information on any topic"
        )
        self.api_key = api_key
        self.base_url = "https://api.tavily.com/search"
        
    def get_function_definition(self) -> Dict[str, Any]:
        """Get Gemini function calling definition for web search."""
        return {
            "name": "search_web",
            "description": "Search the internet for current information, news, facts, or answers to questions",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query or question to search for"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of search results to return (default: 3)"
                    }
                },
                "required": ["query"]
            }
        }
    
    async def execute(self, query: str, max_results: int = 3) -> str:
        """
        Execute web search using Tavily API.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            Formatted search results
        """
        try:
            # Convert max_results to integer to handle float values from Gemini
            max_results = int(max_results) if max_results is not None else 3
            logger.info(f"🔍 Searching web for: {query}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "search_depth": "basic",
                        "include_answer": True,
                        "include_raw_content": False,
                        "max_results": max_results
                    },
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    logger.error(f"Tavily API error: {response.status_code}")
                    return f"Arrr! The search winds be unfavorable, matey. Try again later!"
                
                data = response.json()
                
                # Format results with pirate flair
                results = []
                
                # Add direct answer if available
                if data.get("answer"):
                    results.append(f"**Captain's Quick Answer:** {data['answer']}")
                
                # Add search results
                if data.get("results"):
                    results.append("**Search Treasures Found:**")
                    for i, result in enumerate(data["results"][:max_results], 1):
                        title = result.get("title", "Unknown")
                        content = result.get("content", "") or ""
                        content = content[:200] + "..." if len(content) > 200 else content
                        url = result.get("url", "")
                        
                        results.append(f"{i}. **{title}**")
                        results.append(f"   {content}")
                        if url:
                            results.append(f"   🔗 {url}")
                        results.append("")
                
                if not results:
                    return "Shiver me timbers! No treasure found in these waters, matey!"
                
                prefix = self.get_pirate_response_prefix()
                return f"{prefix}\n\n" + "\n".join(results)
                
        except Exception as e:
            logger.error(f"Web search error: {str(e)}")
            return f"Blimey! The search compass be broken: {str(e)}"
