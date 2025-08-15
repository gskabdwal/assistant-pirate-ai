"""
Text-to-Speech service using Murf AI.
"""
import requests
import logging
import time
import uuid
from typing import Optional, Dict, Any
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class TTSService:
    """Text-to-Speech service using Murf AI."""
    
    def __init__(self, api_key: str):
        """Initialize TTS service with API key."""
        if not api_key:
            raise ValueError("Murf API key is required")
        
        self.api_key = api_key
        self.api_url = "https://api.murf.ai/v1/speech/generate"
        self.voices_url = "https://api.murf.ai/v1/studio/voice-ai/voice-list"
        self.max_chars = 3000  # Murf API character limit
        
        logger.info("TTS Service initialized with Murf AI")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Murf API requests."""
        return {
            "accept": "application/json",
            "api-key": self.api_key,
            "content-type": "application/json"
        }
    
    async def text_to_speech(self, text: str, voice_id: str = "en-US-natalie") -> str:
        """
        Convert text to speech using Murf AI.
        
        Args:
            text: Text to convert to speech
            voice_id: Voice ID to use for TTS
            
        Returns:
            URL to the generated audio file
            
        Raises:
            HTTPException: If TTS generation fails
        """
        start_time = time.time()
        
        try:
            # Check character limit
            if len(text) > self.max_chars:
                logger.warning(f"Text length ({len(text)}) exceeds Murf limit ({self.max_chars})")
                text = text[:self.max_chars - 50] + "..."
            
            logger.info(f"Generating TTS for text: {text[:100]}... (voice: {voice_id})")
            
            payload = {
                "voiceId": voice_id,
                "style": "Conversational",
                "text": text,
                "rate": 0,
                "pitch": 0,
                "sampleRate": 48000,
                "format": "MP3",
                "channelType": "STEREO",
                "pronunciationDictionary": {},
                "encodeAsBase64": False,
                "variation": 1,
                "audioDuration": 0,
                "modelVersion": "GEN2"
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                headers=self._get_headers(),
                timeout=30
            )
            
            processing_time = time.time() - start_time
            
            if response.status_code != 200:
                logger.error(f"Murf API error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"TTS generation failed: {response.text}"
                )
            
            result = response.json()
            audio_url = result.get("audioFile")
            
            if not audio_url:
                logger.error("No audio URL in Murf response")
                raise HTTPException(
                    status_code=500,
                    detail="TTS generation failed: No audio URL returned"
                )
            
            logger.info(f"TTS generated successfully in {processing_time:.2f}s")
            return audio_url
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error during TTS: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"TTS request failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error during TTS generation: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"TTS error: {str(e)}"
            )
    
    async def get_available_voices(self) -> Dict[str, Any]:
        """
        Get list of available voices from Murf AI.
        
        Returns:
            Dictionary containing available voices
            
        Raises:
            HTTPException: If request fails
        """
        try:
            logger.info("Fetching available voices from Murf AI")
            
            response = requests.get(
                self.voices_url,
                headers=self._get_headers(),
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch voices: {response.status_code}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to fetch available voices"
                )
            
            voices = response.json()
            logger.info(f"Retrieved {len(voices.get('voices', []))} voices")
            return voices
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching voices: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch voices: {str(e)}"
            )
    
    def health_check(self) -> bool:
        """Check if the TTS service is healthy."""
        try:
            # Simple health check - verify API key is set
            return bool(self.api_key)
        except Exception as e:
            logger.error(f"TTS health check failed: {str(e)}")
            return False
