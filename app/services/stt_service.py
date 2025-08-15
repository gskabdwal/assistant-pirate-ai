"""
Speech-to-Text service using AssemblyAI.
"""
import assemblyai as aai
import tempfile
import logging
import time
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)


class STTService:
    """Speech-to-Text service using AssemblyAI."""
    
    def __init__(self, api_key: str):
        """Initialize STT service with API key."""
        if not api_key:
            raise ValueError("AssemblyAI API key is required")
        
        aai.settings.api_key = api_key
        self.transcriber = aai.Transcriber()
        logger.info("STT Service initialized with AssemblyAI")
    
    async def transcribe_audio(self, audio_file: UploadFile) -> Tuple[str, Optional[float]]:
        """
        Transcribe audio file to text.
        
        Args:
            audio_file: Uploaded audio file
            
        Returns:
            Tuple of (transcription_text, confidence_score)
            
        Raises:
            HTTPException: If transcription fails
        """
        start_time = time.time()
        
        try:
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                content = await audio_file.read()
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            logger.info(f"Transcribing audio file: {audio_file.filename}")
            
            # Transcribe the audio
            transcript = self.transcriber.transcribe(temp_file_path)
            
            # Clean up temporary file
            import os
            os.unlink(temp_file_path)
            
            processing_time = time.time() - start_time
            
            if transcript.status == aai.TranscriptStatus.error:
                logger.error(f"Transcription failed: {transcript.error}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Transcription failed: {transcript.error}"
                )
            
            transcription_text = transcript.text or ""
            confidence = transcript.confidence if hasattr(transcript, 'confidence') else None
            
            logger.info(f"Transcription completed in {processing_time:.2f}s: {transcription_text[:100]}...")
            
            return transcription_text, confidence
            
        except Exception as e:
            logger.error(f"Error during transcription: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Transcription error: {str(e)}"
            )
    
    def health_check(self) -> bool:
        """Check if the STT service is healthy."""
        try:
            # Simple health check - verify API key is set
            return bool(aai.settings.api_key)
        except Exception as e:
            logger.error(f"STT health check failed: {str(e)}")
            return False
