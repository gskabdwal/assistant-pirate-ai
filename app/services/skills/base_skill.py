"""
Base skill class for Captain Blackbeard's Voice Agent special abilities.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class BaseSkill(ABC):
    """Abstract base class for all voice agent skills."""
    
    def __init__(self, name: str, description: str):
        """
        Initialize base skill.
        
        Args:
            name: Skill name
            description: Skill description for function calling
        """
        self.name = name
        self.description = description
        self.enabled = True
        
    @abstractmethod
    def get_function_definition(self) -> Dict[str, Any]:
        """
        Get Gemini function calling definition for this skill.
        
        Returns:
            Function definition dict for Gemini API
        """
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """
        Execute the skill with given parameters.
        
        Args:
            **kwargs: Skill-specific parameters
            
        Returns:
            Skill execution result as string
        """
        pass
    
    def is_enabled(self) -> bool:
        """Check if skill is enabled."""
        return self.enabled
    
    def enable(self):
        """Enable the skill."""
        self.enabled = True
        logger.info(f"🏴‍☠️ Skill '{self.name}' enabled")
    
    def disable(self):
        """Disable the skill."""
        self.enabled = False
        logger.info(f"🏴‍☠️ Skill '{self.name}' disabled")
    
    def get_pirate_response_prefix(self) -> str:
        """Get a pirate-themed response prefix."""
        prefixes = [
            "Ahoy matey! Here be what I found:",
            "Arrr! The treasure ye seek:",
            "Avast! Captain Blackbeard's wisdom reveals:",
            "Shiver me timbers! Here's the intel:",
            "Batten down the hatches! I've discovered:",
        ]
        import random
        return random.choice(prefixes)
