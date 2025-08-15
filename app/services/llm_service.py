"""
Large Language Model service using Google Gemini.
"""
import google.generativeai as genai
import logging
import time
from typing import List, Dict, Any, Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class LLMService:
    """LLM service using Google Gemini."""
    
    def __init__(self, api_key: str):
        """Initialize LLM service with API key."""
        if not api_key:
            raise ValueError("Gemini API key is required")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.max_response_chars = 2950  # Keep under Murf's 3000 char limit
        
        logger.info("LLM Service initialized with Google Gemini")
    
    async def generate_response(
        self, 
        user_input: str, 
        chat_history: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Generate response using Gemini LLM.
        
        Args:
            user_input: User's input text
            chat_history: Previous conversation history
            
        Returns:
            Generated response text
            
        Raises:
            HTTPException: If generation fails
        """
        start_time = time.time()
        
        try:
            # Build conversation context
            context = self._build_context(user_input, chat_history)
            
            logger.info(f"Generating LLM response for: {user_input[:100]}...")
            
            # Generate response
            response = self.model.generate_content(context)
            
            processing_time = time.time() - start_time
            
            if not response.text:
                logger.error("Empty response from Gemini")
                raise HTTPException(
                    status_code=500,
                    detail="LLM generated empty response"
                )
            
            response_text = response.text.strip()
            
            # Ensure response fits within TTS character limits
            if len(response_text) > self.max_response_chars:
                logger.warning(f"Response too long ({len(response_text)} chars), truncating")
                response_text = response_text[:self.max_response_chars - 50] + "..."
            
            logger.info(f"LLM response generated in {processing_time:.2f}s")
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"LLM generation error: {str(e)}"
            )
    
    def _build_context(
        self, 
        user_input: str, 
        chat_history: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Build conversation context for the LLM.
        
        Args:
            user_input: Current user input
            chat_history: Previous conversation history
            
        Returns:
            Formatted context string
        """
        context_parts = [
            "You are a helpful AI assistant. Please provide concise, helpful responses.",
            f"Keep your responses under {self.max_response_chars} characters to ensure they can be converted to speech.",
            "Be conversational and friendly in your tone."
        ]
        
        # Add chat history if available
        if chat_history:
            context_parts.append("\nConversation history:")
            for message in chat_history[-10:]:  # Last 10 messages for context
                role = message.get('role', 'unknown')
                content = message.get('content', '')
                context_parts.append(f"{role.capitalize()}: {content}")
        
        # Add current user input
        context_parts.append(f"\nUser: {user_input}")
        context_parts.append("Assistant:")
        
        return "\n".join(context_parts)
    
    def health_check(self) -> bool:
        """Check if the LLM service is healthy."""
        try:
            # Simple health check - try to generate a minimal response
            test_response = self.model.generate_content("Hello")
            return bool(test_response.text)
        except Exception as e:
            logger.error(f"LLM health check failed: {str(e)}")
            return False
