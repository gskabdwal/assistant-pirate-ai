"""
Text-to-Speech service using Murf AI with WebSocket streaming support.
"""
import asyncio
import base64
import json
import logging
import requests
import time
import uuid
import websockets
from typing import Optional, Dict, Any, AsyncGenerator
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
        # Generate unique context_id for each session to avoid conflicts
        self.base_context_id = "voice-agent-day22"
        
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
    
    def _split_text_into_chunks(self, text: str, max_chunk_size: int = 200) -> list[str]:
        """Split text into smaller chunks to avoid WebSocket timeout."""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 > max_chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = len(word)
            else:
                current_chunk.append(word)
                current_length += len(word) + 1
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    async def stream_text_to_speech(
        self,
        text: str,
        voice_id: str = "en-US-natalie",
        sample_rate: int = 44100,
        format: str = "WAV",
        channel_type: str = "MONO"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream text-to-speech audio using Murf WebSocket API with connection retry."""
        session_context_id = f"voice-agent-day22-{uuid.uuid4().hex[:8]}-{int(time.time() * 1000)}"
        logger.info(f"Starting TTS streaming with context_id: {session_context_id}")
        
        ws_url = "wss://api.murf.ai/v1/speech/stream-input"
        
        try:
            logger.info(f"Starting Murf WebSocket TTS streaming for text: {text[:50]}...")
            
            # Connect to Murf WebSocket with original working URL format
            async with websockets.connect(
                f"{ws_url}?api-key={self.api_key}&sample_rate={sample_rate}&channel_type={channel_type}&format={format}"
            ) as websocket:
                logger.info("Connected to Murf WebSocket")
                
                # Send voice configuration with unique context_id
                voice_config = {
                    "voice_config": {
                        "voiceId": voice_id,
                        "style": "Conversational",
                        "rate": 0,
                        "pitch": 0,
                        "variation": 1,
                        "context_id": session_context_id
                    }
                }
                
                logger.info(f"Sending voice config: {voice_config}")
                await websocket.send(json.dumps(voice_config))
                
                # Send text message
                text_msg = {
                    "text": text,
                    "context_id": session_context_id,
                    "end": True  # Properly close context after sending text
                }
                
                logger.info(f"Sending text message: {text_msg}")
                await websocket.send(json.dumps(text_msg))
                
                # Process responses with enhanced error handling
                chunk_count = 0
                while True:
                    try:
                        response = await websocket.recv()
                        if not response:
                            logger.warning("Received empty response from Murf WebSocket")
                            break
                        data = json.loads(response)
                    except websockets.exceptions.ConnectionClosed as e:
                        logger.error(f"Murf WebSocket connection closed: {e}")
                        break
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON response: {e}")
                        break
                    except Exception as recv_error:
                        logger.error(f"Error receiving WebSocket data: {recv_error}")
                        break
                    
                    chunk_count += 1
                    logger.info(f"Received chunk {chunk_count}: {data}")
                    
                    # Enhanced base64 audio logging for LinkedIn screenshot
                    if "audio" in data:
                        audio_b64 = data["audio"]
                        print("\n" + "="*80)
                        print(f"MURF WEBSOCKET BASE64 AUDIO CHUNK {chunk_count}")
                        print("="*80)
                        print(f"Audio length: {len(audio_b64)} characters")
                        print(f"First 200 chars: {audio_b64[:200]}")
                        print(f"Last 200 chars: {audio_b64[-200:]}")
                        print("="*80)
                        
                        # Also log to logger for persistent record
                        logger.info(f"Base64 audio chunk {chunk_count}: {len(audio_b64)} chars")
                    
                    yield data
                    
                    # Check if this is the final message
                    if data.get("final"):
                        logger.info("Murf WebSocket streaming completed")
                        break
                        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"WebSocket TTS streaming error: {error_msg}")
            
            # Check for rate limiting
            if "429" in error_msg or "Too Many Requests" in error_msg:
                raise HTTPException(
                    status_code=429,
                    detail="TTS service rate limited. Please wait a few minutes before trying again."
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"WebSocket TTS streaming error: {error_msg}"
                )
    
    async def _stream_single_chunk(self, text: str, session_context_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream a single text chunk to avoid WebSocket timeouts."""
        ws_url = "wss://api.murf.ai/v1/speech/stream-input"
        
        try:
            logger.info(f"Starting Murf WebSocket TTS streaming for chunk: {text[:50]}...")
            
            # Connect to Murf WebSocket with original working URL format
            async with websockets.connect(
                f"{ws_url}?api-key={self.api_key}&sample_rate=44100&channel_type=MONO&format=WAV"
            ) as websocket:
                logger.info("Connected to Murf WebSocket")
                
                # Send voice configuration with unique context_id
                voice_config = {
                    "voice_config": {
                        "voiceId": "en-US-natalie",
                        "style": "Conversational",
                        "rate": 0,
                        "pitch": 0,
                        "variation": 1,
                        "context_id": session_context_id
                    }
                }
                
                logger.info(f"Sending voice config: {voice_config}")
                await websocket.send(json.dumps(voice_config))
                
                # Send text message with same context_id and end=True to properly close
                text_msg = {
                    "text": text,
                    "context_id": session_context_id,
                    "end": True  # Properly close context after sending text
                }
                
                logger.info(f"Sending text message: {text_msg}")
                await websocket.send(json.dumps(text_msg))
                
                # Process responses
                chunk_count = 0
                while True:
                    try:
                        response = await websocket.recv()
                        if not response:
                            logger.warning("Received empty response from Murf WebSocket")
                            break
                        data = json.loads(response)
                    except websockets.exceptions.ConnectionClosed as e:
                        logger.error(f"Murf WebSocket connection closed: {e}")
                        break
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON response: {e}")
                        break
                    except Exception as recv_error:
                        logger.error(f"Error receiving WebSocket data: {recv_error}")
                        break
                    
                    chunk_count += 1
                    logger.info(f"Received chunk {chunk_count}: {data}")
                    
                    # Enhanced base64 audio logging for LinkedIn screenshot
                    if "audio" in data:
                        audio_b64 = data["audio"]
                        print("\n" + "="*80)
                        print(f"MURF WEBSOCKET BASE64 AUDIO CHUNK {chunk_count}")
                        print("="*80)
                        print(f"Audio length: {len(audio_b64)} characters")
                        print(f"First 200 chars: {audio_b64[:200]}")
                        print(f"Last 50 chars: ...{audio_b64[-50:]}")
                        print("="*80 + "\n")
                        
                        # Also log to logger for persistent record
                        logger.info(f"Base64 audio chunk {chunk_count}: {len(audio_b64)} chars")
                    
                    yield data
                    
                    # Check if this is the final message
                    if data.get("final"):
                        logger.info("Murf WebSocket streaming completed")
                        break
                        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"WebSocket TTS streaming error: {error_msg}")
            
            # Check for rate limiting
            if "429" in error_msg or "Too Many Requests" in error_msg:
                raise HTTPException(
                    status_code=429,
                    detail="TTS service rate limited. Please wait a few minutes before trying again."
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"WebSocket TTS streaming error: {error_msg}"
                )
    
    def health_check(self) -> bool:
        """Check if the TTS service is healthy."""
        try:
            # Simple health check - verify API key is set
            return bool(self.api_key)
        except Exception as e:
            logger.error(f"TTS health check failed: {str(e)}")
            return False
