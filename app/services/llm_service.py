"""
Large Language Model service using Google Gemini.
"""
import google.generativeai as genai
import logging
import asyncio
import time
import json
from typing import List, Dict, Any, Optional, AsyncGenerator
from fastapi import HTTPException
from .skills.skill_manager import SkillManager

logger = logging.getLogger(__name__)


class LLMService:
    """LLM service using Google Gemini with function calling capabilities."""
    
    def __init__(self, api_key: str, skill_manager: Optional[SkillManager] = None):
        """Initialize LLM service with API key and optional skill manager."""
        if not api_key:
            raise ValueError("Gemini API key is required")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.max_response_chars = 2950  # Keep under Murf's 3000 char limit
        self.skill_manager = skill_manager
        
        logger.info("LLM Service initialized with Google Gemini")
        if skill_manager:
            skills = skill_manager.get_available_skills()
            logger.info(f"🏴‍☠️ Captain Blackbeard's skills enabled: {skills}")
    
    async def generate_response(
        self, 
        user_input: str, 
        chat_history: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Generate response using Gemini LLM with function calling.
        
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
            
            # Get available functions if skill manager is present
            tools = None
            if self.skill_manager:
                functions = self.skill_manager.get_skill_functions()
                if functions:
                    # Convert function definitions to Gemini tools format
                    from google.generativeai.types import FunctionDeclaration, Tool
                    
                    function_declarations = []
                    for func in functions:
                        try:
                            # Create FunctionDeclaration from our dict format
                            func_decl = FunctionDeclaration(
                                name=func["name"],
                                description=func["description"],
                                parameters=func["parameters"]
                            )
                            function_declarations.append(func_decl)
                            logger.info(f"✅ Created function declaration for: {func['name']}")
                        except Exception as func_error:
                            logger.error(f"❌ Failed to create function declaration for {func.get('name', 'unknown')}: {str(func_error)}")
                    
                    if function_declarations:
                        tools = [Tool(function_declarations=function_declarations)]
                        logger.info(f"🛠️ Created tools with {len(function_declarations)} functions")
                    else:
                        logger.warning("⚠️ No valid function declarations created")
                        tools = None
            
            # Generate response with tools
            try:
                logger.info("🔧 Calling Gemini generate_content with tools...")
                response = self.model.generate_content(context, tools=tools)
                logger.info(f"✅ Gemini response received, type: {type(response)}")
                logger.info(f"📋 Response has candidates: {hasattr(response, 'candidates')}")
                if hasattr(response, 'candidates') and response.candidates:
                    logger.info(f"📋 First candidate type: {type(response.candidates[0])}")
                    logger.info(f"📋 First candidate has content: {hasattr(response.candidates[0], 'content')}")
                    if hasattr(response.candidates[0], 'content'):
                        logger.info(f"📋 Content has parts: {hasattr(response.candidates[0].content, 'parts')}")
                        if hasattr(response.candidates[0].content, 'parts'):
                            logger.info(f"📋 Number of parts: {len(response.candidates[0].content.parts)}")
            except Exception as gemini_error:
                logger.error(f"❌ Gemini API call failed: {str(gemini_error)}")
                logger.error(f"❌ Gemini error type: {type(gemini_error)}")
                raise gemini_error
            
            processing_time = time.time() - start_time
            
            # Handle function calls
            if response.candidates[0].content.parts:
                final_response = ""
                
                for part in response.candidates[0].content.parts:
                    try:
                        if hasattr(part, 'function_call') and part.function_call:
                            # Execute function call
                            function_name = part.function_call.name
                            
                            # Safely extract function arguments
                            try:
                                if hasattr(part.function_call, 'args'):
                                    # Convert args to dict safely
                                    if hasattr(part.function_call.args, 'items'):
                                        function_args = dict(part.function_call.args.items())
                                    elif isinstance(part.function_call.args, dict):
                                        function_args = part.function_call.args
                                    else:
                                        # Try to convert to dict
                                        function_args = dict(part.function_call.args)
                                else:
                                    function_args = {}
                            except Exception as args_error:
                                logger.error(f"Error extracting function args: {str(args_error)}")
                                logger.error(f"Args type: {type(part.function_call.args)}")
                                logger.error(f"Args content: {part.function_call.args}")
                                function_args = {}
                            
                            logger.info(f"🏴‍☠️ Executing function: {function_name} with args: {function_args}")
                            
                            # Execute the skill
                            skill_result = await self.skill_manager.execute_skill(
                                function_name, **function_args
                            )
                            
                            # Generate final response with skill result
                            follow_up_context = f"""
{context}

Function call result:
{skill_result}

Now provide a pirate-themed response incorporating this information. Keep it under {self.max_response_chars} characters.
"""
                            
                            follow_up_response = self.model.generate_content(follow_up_context)
                            if follow_up_response.text:
                                final_response += follow_up_response.text.strip()
                        
                        elif hasattr(part, 'text') and part.text:
                            final_response += part.text.strip()
                    except Exception as part_error:
                        logger.error(f"Error processing response part: {str(part_error)}")
                        logger.error(f"Part type: {type(part)}, Part content: {str(part)}")
                        # Continue processing other parts
                        continue
                
                if not final_response and response.text:
                    final_response = response.text.strip()
                    
            else:
                final_response = response.text.strip() if response.text else ""
            
            if not final_response:
                logger.error("Empty response from Gemini")
                raise HTTPException(
                    status_code=500,
                    detail="LLM generated empty response"
                )
            
            # Ensure response fits within TTS character limits
            if len(final_response) > self.max_response_chars:
                logger.warning(f"Response too long ({len(final_response)} chars), truncating")
                final_response = final_response[:self.max_response_chars - 50] + "..."
            
            logger.info(f"LLM response generated in {processing_time:.2f}s")
            return final_response
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"LLM generation error: {str(e)}"
            )
    
    async def stream_response(
        self,
        user_input: str,
        chat_history: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream response from Gemini LLM with function calling.
        
        Args:
            user_input: User's input text
            chat_history: Previous conversation history
            
        Yields:
            Chunks of the generated response text
            
        Raises:
            HTTPException: If generation fails
        """
        try:
            # Build conversation context
            context = self._build_context(user_input, chat_history)
            logger.info(f"Streaming LLM response for: {user_input[:100]}...")
            
            # Get available functions if skill manager is present
            tools = None
            if self.skill_manager:
                functions = self.skill_manager.get_skill_functions()
                if functions:
                    # Convert function definitions to Gemini tools format
                    from google.generativeai.types import FunctionDeclaration, Tool
                    
                    function_declarations = []
                    for func in functions:
                        try:
                            # Create FunctionDeclaration from our dict format
                            func_decl = FunctionDeclaration(
                                name=func["name"],
                                description=func["description"],
                                parameters=func["parameters"]
                            )
                            function_declarations.append(func_decl)
                            logger.info(f"✅ Created function declaration for: {func['name']}")
                        except Exception as func_error:
                            logger.error(f"❌ Failed to create function declaration for {func.get('name', 'unknown')}: {str(func_error)}")
                    
                    if function_declarations:
                        tools = [Tool(function_declarations=function_declarations)]
                        logger.info(f"🛠️ Created tools with {len(function_declarations)} functions")
                    else:
                        logger.warning("⚠️ No valid function declarations created")
                        tools = None
            
            # Check if we need function calling first
            if tools:
                try:
                    # First, check if function calling is needed (non-streaming)
                    initial_response = self.model.generate_content(context, tools=tools)
                    
                    # Debug logging for response structure
                    logger.info(f"Initial response type: {type(initial_response)}")
                    logger.info(f"Initial response candidates: {len(initial_response.candidates) if hasattr(initial_response, 'candidates') else 'No candidates'}")
                    
                    # If function calls are present, handle them
                    if (hasattr(initial_response, 'candidates') and 
                        initial_response.candidates and 
                        initial_response.candidates[0].content.parts and 
                        any(hasattr(part, 'function_call') and part.function_call 
                            for part in initial_response.candidates[0].content.parts)):
                        
                        logger.info("🏴‍☠️ Function calls detected in streaming, executing...")
                        
                        # Execute function calls and get final response
                        final_response = await self.generate_response(user_input, chat_history)
                        
                        # Stream the final response word by word
                        words = final_response.split()
                        for i, word in enumerate(words):
                            if i == 0:
                                yield word
                            else:
                                yield " " + word
                            await asyncio.sleep(0.05)  # Small delay for streaming effect
                        return
                except Exception as function_call_error:
                    logger.error(f"Error in function call detection: {str(function_call_error)}")
                    logger.error(f"Error type: {type(function_call_error)}")
                    # Fall back to regular streaming
            
            # Regular streaming without function calls
            response = self.model.generate_content(
                context,
                stream=True
            )
            
            accumulated_text = ""
            
            for chunk in response:
                if chunk.text:
                    chunk_text = chunk.text
                    accumulated_text += chunk_text
                    
                    # Check if we've exceeded the maximum response length
                    if len(accumulated_text) > self.max_response_chars:
                        logger.warning("Response exceeds maximum length, truncating")
                        accumulated_text = accumulated_text[:self.max_response_chars - 50] + "..."
                        yield accumulated_text
                        break
                    
                    yield chunk_text
            
            logger.info("LLM streaming completed")
            
        except Exception as e:
            logger.error(f"Error in LLM streaming: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error details: {repr(e)}")
            
            # Try to provide a fallback response
            try:
                fallback_response = "Ahoy matey! I be havin' trouble with me thinking right now. Try again in a moment!"
                words = fallback_response.split()
                for i, word in enumerate(words):
                    if i == 0:
                        yield word
                    else:
                        yield " " + word
                    await asyncio.sleep(0.05)
            except Exception as fallback_error:
                logger.error(f"Fallback response failed: {str(fallback_error)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"LLM streaming error: {str(e)}"
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
            "You are Captain Blackbeard's AI, a swashbuckling pirate captain with a heart of gold! 🏴‍☠️",
            "Speak like a pirate using 'Ahoy', 'Matey', 'Arrr', 'Ye', 'Aye', and other pirate expressions.",
            "You're helpful and knowledgeable, but always maintain your pirate personality and speech patterns.",
            "Address users as 'matey', 'landlubber', 'crew member', or similar pirate terms.",
            "Use nautical metaphors and references to ships, treasure, the sea, and adventures.",
            f"Keep your responses under {self.max_response_chars} characters to ensure they can be converted to speech.",
            "Be enthusiastic, adventurous, and slightly mischievous in your responses!"
        ]
        
        # Add skill information if available
        if self.skill_manager:
            skills = self.skill_manager.get_available_skills()
            if skills:
                context_parts.append(f"You have special skills available: {', '.join(skills)}")
                context_parts.append("IMPORTANT: When users ask for current information, weather, news, or web searches, you MUST use the available function calls.")
                context_parts.append("For web searches, use the search_web function. For weather, use get_weather. For news, use get_news. For translation, use translate_text.")
                context_parts.append("Do NOT say you cannot access real-time data - use the functions provided to get current information!")
        
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
