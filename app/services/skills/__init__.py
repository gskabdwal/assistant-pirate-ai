"""
Skills package for Captain Blackbeard's Voice Agent.
"""
from .base_skill import BaseSkill
from .skill_manager import SkillManager
from .web_search_skill import WebSearchSkill
from .weather_skill import WeatherSkill
from .news_skill import NewsSkill

__all__ = [
    'BaseSkill',
    'SkillManager', 
    'WebSearchSkill',
    'WeatherSkill',
    'NewsSkill'
]
