"""
Skill manager for Captain Blackbeard's Voice Agent special abilities.
"""
import logging
from typing import Dict, List, Any, Optional
from .base_skill import BaseSkill
from .web_search_skill import WebSearchSkill
from .weather_skill import WeatherSkill
from .news_skill import NewsSkill
from .translation_skill import TranslationSkill

logger = logging.getLogger(__name__)


class SkillManager:
    """Manages all special skills for the voice agent."""
    
    def __init__(self, tavily_api_key: str = None, weather_api_key: str = None, news_api_key: str = None, translate_api_key: str = None):
        """
        Initialize skill manager with API keys.
        
        Args:
            tavily_api_key: Tavily API key for web search
            weather_api_key: OpenWeatherMap API key
            news_api_key: NewsAPI key
            translate_api_key: Google Cloud API key for translation
        """
        self.skills: Dict[str, BaseSkill] = {}
        
        # Initialize skills based on available API keys
        if tavily_api_key:
            try:
                self.skills["search_web"] = WebSearchSkill(tavily_api_key)
                logger.info("🔍 Web search skill enabled")
            except Exception as e:
                logger.error(f"Failed to initialize web search skill: {e}")
        
        if weather_api_key:
            try:
                self.skills["get_weather"] = WeatherSkill(weather_api_key)
                logger.info("🌤️ Weather skill enabled")
            except Exception as e:
                logger.error(f"Failed to initialize weather skill: {e}")
        
        if news_api_key:
            try:
                self.skills["get_news"] = NewsSkill(news_api_key)
                logger.info("📰 News skill enabled")
            except Exception as e:
                logger.error(f"Failed to initialize news skill: {e}")
        
        if translate_api_key:
            try:
                self.skills["translate_text"] = TranslationSkill(translate_api_key)
                logger.info("🌍 Translation skill enabled")
            except Exception as e:
                logger.error(f"Failed to initialize translation skill: {e}")
        
        logger.info(f"🏴‍☠️ Skill Manager initialized with {len(self.skills)} skills")
    
    def get_available_skills(self) -> List[str]:
        """Get list of available skill names."""
        return [name for name, skill in self.skills.items() if skill.is_enabled()]
    
    def get_skill_functions(self) -> List[Dict[str, Any]]:
        """Get function definitions for all enabled skills."""
        functions = []
        for skill in self.skills.values():
            if skill.is_enabled():
                functions.append(skill.get_function_definition())
        return functions
    
    async def execute_skill(self, function_name: str, **kwargs) -> str:
        """
        Execute a skill by function name.
        
        Args:
            function_name: Name of the function to execute
            **kwargs: Function parameters
            
        Returns:
            Skill execution result
        """
        if function_name not in self.skills:
            return f"Arrr! Unknown skill '{function_name}', matey!"
        
        skill = self.skills[function_name]
        
        if not skill.is_enabled():
            return f"Blimey! The '{function_name}' skill be disabled, matey!"
        
        try:
            logger.info(f"🏴‍☠️ Executing skill: {function_name}")
            result = await skill.execute(**kwargs)
            logger.info(f"✅ Skill '{function_name}' executed successfully")
            return result
        except Exception as e:
            logger.error(f"❌ Skill '{function_name}' failed: {str(e)}")
            return f"Shiver me timbers! The '{function_name}' skill ran aground: {str(e)}"
    
    def enable_skill(self, skill_name: str) -> bool:
        """Enable a skill by name."""
        if skill_name in self.skills:
            self.skills[skill_name].enable()
            return True
        return False
    
    def disable_skill(self, skill_name: str) -> bool:
        """Disable a skill by name."""
        if skill_name in self.skills:
            self.skills[skill_name].disable()
            return True
        return False
    
    def get_skill_info(self) -> Dict[str, Any]:
        """Get information about all skills."""
        info = {
            "total_skills": len(self.skills),
            "enabled_skills": len([s for s in self.skills.values() if s.is_enabled()]),
            "skills": {}
        }
        
        for name, skill in self.skills.items():
            info["skills"][name] = {
                "name": skill.name,
                "description": skill.description,
                "enabled": skill.is_enabled()
            }
        
        return info
