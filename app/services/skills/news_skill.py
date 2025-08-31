"""
News headlines skill using NewsAPI for Captain Blackbeard's Voice Agent.
"""
import httpx
import logging
from typing import Dict, Any
from .base_skill import BaseSkill

logger = logging.getLogger(__name__)


class NewsSkill(BaseSkill):
    """News headlines skill using NewsAPI."""
    
    def __init__(self, api_key: str):
        """
        Initialize news skill.
        
        Args:
            api_key: NewsAPI key
        """
        super().__init__(
            name="news",
            description="Get latest news headlines by category or topic"
        )
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2"
        
    def get_function_definition(self) -> Dict[str, Any]:
        """Get Gemini function calling definition for news."""
        return {
            "name": "get_news",
            "description": "Get latest news headlines by category or search for specific topics",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for specific news topics (optional)"
                    },
                    "category": {
                        "type": "string",
                        "description": "News category: business, entertainment, general, health, science, sports, technology",
                        "enum": ["business", "entertainment", "general", "health", "science", "sports", "technology"]
                    },
                    "country": {
                        "type": "string",
                        "description": "Country code for news (e.g., 'us', 'gb', 'ca', default: 'us')"
                    },
                    "max_articles": {
                        "type": "integer",
                        "description": "Maximum number of articles to return (default: 5)"
                    }
                }
            }
        }
    
    async def execute(self, query: str = None, category: str = None, country: str = "us", max_articles: int = 5) -> str:
        """
        Execute news lookup.
        
        Args:
            query: Search query for specific topics
            category: News category
            country: Country code
            max_articles: Maximum number of articles
            
        Returns:
            Formatted news headlines
        """
        try:
            # Convert max_articles to integer to handle float values from Gemini
            max_articles = int(max_articles) if max_articles is not None else 5
            logger.info(f"📰 Getting news - Query: {query}, Category: {category}")
            
            async with httpx.AsyncClient() as client:
                # Choose endpoint based on parameters
                if query:
                    # Use everything endpoint for search
                    endpoint = f"{self.base_url}/everything"
                    params = {
                        "apiKey": self.api_key,
                        "q": query,
                        "sortBy": "publishedAt",
                        "language": "en",
                        "pageSize": max_articles
                    }
                else:
                    # Use top-headlines endpoint for categories
                    endpoint = f"{self.base_url}/top-headlines"
                    params = {
                        "apiKey": self.api_key,
                        "country": country,
                        "pageSize": max_articles
                    }
                    if category:
                        params["category"] = category
                
                response = await client.get(endpoint, params=params, timeout=10.0)
                
                if response.status_code != 200:
                    logger.error(f"News API error: {response.status_code}")
                    return f"Arrr! The news ravens be silent today, matey. Try again later!"
                
                data = response.json()
                articles = data.get("articles", [])
                
                if not articles:
                    search_term = query or category or "general news"
                    return f"Shiver me timbers! No news treasure found for '{search_term}', matey!"
                
                # Format results with pirate flair
                results = []
                
                if query:
                    results.append(f"**Latest News on '{query}':**")
                elif category:
                    results.append(f"**Top {category.title()} Headlines:**")
                else:
                    results.append(f"**Breaking News from the Seven Seas:**")
                
                for i, article in enumerate(articles[:max_articles], 1):
                    title = article.get("title", "Unknown Title")
                    description = article.get("description", "")
                    source = article.get("source", {}).get("name", "Unknown Source")
                    url = article.get("url", "")
                    published_at = article.get("publishedAt", "")
                    
                    # Format date
                    if published_at:
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                            time_str = dt.strftime("%B %d, %Y at %H:%M UTC")
                        except:
                            time_str = published_at
                    else:
                        time_str = "Unknown time"
                    
                    results.append(f"\n{i}. **{title}**")
                    results.append(f"   📰 Source: {source}")
                    results.append(f"   🕒 Published: {time_str}")
                    
                    if description:
                        # Limit description length and handle None values
                        description = description or ""
                        desc = description[:150] + "..." if len(description) > 150 else description
                        results.append(f"   📝 {desc}")
                    
                    if url:
                        results.append(f"   🔗 {url}")
                
                prefix = self.get_pirate_response_prefix()
                return f"{prefix}\n\n" + "\n".join(results)
                
        except Exception as e:
            logger.error(f"News error: {str(e)}")
            return f"Blimey! The news parrot be squawking nonsense: {str(e)}"
