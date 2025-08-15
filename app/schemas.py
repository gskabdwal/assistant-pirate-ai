"""
Pydantic schemas for request and response models.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class TTSRequest(BaseModel):
    """Text-to-Speech request schema."""
    text: str
    voice_id: Optional[str] = "en-US-natalie"


class TTSResponse(BaseModel):
    """Text-to-Speech response schema."""
    audio_url: str
    message: str


class TranscriptionRequest(BaseModel):
    """Audio transcription request schema."""
    audio_file: str  # File path or identifier


class TranscriptionResponse(BaseModel):
    """Audio transcription response schema."""
    transcription: str
    confidence: Optional[float] = None
    processing_time: Optional[float] = None


class LLMRequest(BaseModel):
    """LLM query request schema."""
    text: str
    context: Optional[List[Dict[str, Any]]] = None


class LLMResponse(BaseModel):
    """LLM query response schema."""
    response: str
    model_used: Optional[str] = None
    processing_time: Optional[float] = None


class ChatMessage(BaseModel):
    """Chat message schema."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime


class ChatHistoryResponse(BaseModel):
    """Chat history response schema."""
    session_id: str
    messages: List[ChatMessage]
    total_messages: int


class VoiceAgentRequest(BaseModel):
    """Complete voice agent request schema."""
    session_id: Optional[str] = None
    voice_id: Optional[str] = "en-US-natalie"


class VoiceAgentResponse(BaseModel):
    """Complete voice agent response schema."""
    session_id: str
    transcription: str
    llm_response: str
    audio_url: str
    chat_history_length: int
    processing_time: Optional[float] = None


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str
    detail: Optional[str] = None
    status_code: int
