"""
AI Voice Agent - Refactored FastAPI Application.
"""
import logging
import time
import uuid
from typing import Dict, Any
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from .config import Config
from .schemas import (
    TTSRequest, TTSResponse, TranscriptionResponse, LLMRequest, LLMResponse,
    VoiceAgentResponse, ErrorResponse, ChatHistoryResponse
)
from .services import STTService, TTSService, LLMService, ChatService

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=Config.APP_TITLE,
    version=Config.APP_VERSION,
    description="AI Voice Agent with Speech-to-Text, LLM, and Text-to-Speech capabilities"
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory=Config.STATIC_DIR), name="static")
templates = Jinja2Templates(directory=Config.TEMPLATES_DIR)

# Initialize services
stt_service = None
tts_service = None
llm_service = None
chat_service = ChatService()

# Initialize services with error handling
try:
    if Config.ASSEMBLYAI_API_KEY:
        stt_service = STTService(Config.ASSEMBLYAI_API_KEY)
        logger.info("STT service initialized successfully")
    else:
        logger.warning("STT service not initialized - missing API key")
        
    if Config.MURF_API_KEY:
        tts_service = TTSService(Config.MURF_API_KEY)
        logger.info("TTS service initialized successfully")
    else:
        logger.warning("TTS service not initialized - missing API key")
        
    if Config.GEMINI_API_KEY:
        llm_service = LLMService(Config.GEMINI_API_KEY)
        logger.info("LLM service initialized successfully")
    else:
        logger.warning("LLM service not initialized - missing API key")
        
except Exception as e:
    logger.error(f"Error initializing services: {str(e)}")


# Dependency functions
def get_stt_service() -> STTService:
    """Get STT service dependency."""
    if not stt_service:
        raise HTTPException(status_code=503, detail="STT service not available")
    return stt_service


def get_tts_service() -> TTSService:
    """Get TTS service dependency."""
    if not tts_service:
        raise HTTPException(status_code=503, detail="TTS service not available")
    return tts_service


def get_llm_service() -> LLMService:
    """Get LLM service dependency."""
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM service not available")
    return llm_service


def get_chat_service() -> ChatService:
    """Get chat service dependency."""
    return chat_service


# API Routes
@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    """Serve the main application page."""
    logger.info("Serving main application page")
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/tts", response_model=TTSResponse)
async def text_to_speech(
    request: TTSRequest,
    tts: TTSService = Depends(get_tts_service)
):
    """Convert text to speech using Murf AI."""
    logger.info(f"TTS request received: {request.text[:50]}...")
    
    try:
        audio_url = await tts.text_to_speech(request.text, request.voice_id)
        
        return TTSResponse(
            audio_url=audio_url,
            message="TTS generation successful"
        )
    except Exception as e:
        logger.error(f"TTS endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    stt: STTService = Depends(get_stt_service)
):
    """Transcribe audio file using AssemblyAI."""
    logger.info(f"Transcription request received: {file.filename}")
    
    try:
        start_time = time.time()
        transcription, confidence = await stt.transcribe_audio(file)
        processing_time = time.time() - start_time
        
        return TranscriptionResponse(
            transcription=transcription,
            confidence=confidence,
            processing_time=processing_time
        )
    except Exception as e:
        logger.error(f"Transcription endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/llm/query", response_model=LLMResponse)
async def llm_query(
    request: LLMRequest,
    llm: LLMService = Depends(get_llm_service)
):
    """Generate LLM response using Gemini."""
    logger.info(f"LLM query received: {request.text[:50]}...")
    
    try:
        start_time = time.time()
        response = await llm.generate_response(request.text, request.context)
        processing_time = time.time() - start_time
        
        return LLMResponse(
            response=response,
            model_used="gemini-pro",
            processing_time=processing_time
        )
    except Exception as e:
        logger.error(f"LLM endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/echo", response_model=TTSResponse)
async def echo_tts(
    file: UploadFile = File(...),
    voice_id: str = Form("en-US-natalie"),
    stt: STTService = Depends(get_stt_service),
    tts: TTSService = Depends(get_tts_service)
):
    """Echo endpoint: transcribe audio and convert back to speech."""
    logger.info(f"Echo request received: {file.filename}")
    
    try:
        # Transcribe audio
        transcription, _ = await stt.transcribe_audio(file)
        
        if not transcription.strip():
            raise HTTPException(status_code=400, detail="No speech detected in audio")
        
        # Convert back to speech
        audio_url = await tts.text_to_speech(transcription, voice_id)
        
        return TTSResponse(
            audio_url=audio_url,
            message=f"Echo successful: {transcription}"
        )
    except Exception as e:
        logger.error(f"Echo endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/chat/{session_id}", response_model=VoiceAgentResponse)
async def agent_chat(
    session_id: str,
    file: UploadFile = File(...),
    voice_id: str = Form("en-US-natalie"),
    stt: STTService = Depends(get_stt_service),
    tts: TTSService = Depends(get_tts_service),
    llm: LLMService = Depends(get_llm_service),
    chat: ChatService = Depends(get_chat_service)
):
    """
    Complete voice agent with chat history.
    Transcribe audio, generate LLM response with context, and convert to speech.
    """
    logger.info(f"Voice agent request for session: {session_id[:8]}...")
    
    try:
        start_time = time.time()
        
        # Step 1: Transcribe audio
        transcription, _ = await stt.transcribe_audio(file)
        
        if not transcription.strip():
            raise HTTPException(status_code=400, detail="No speech detected in audio")
        
        # Step 2: Get chat history for context
        chat_history = chat.get_chat_history(session_id, limit=Config.MAX_CHAT_HISTORY)
        
        # Step 3: Generate LLM response with context
        llm_response = await llm.generate_response(transcription, chat_history)
        
        # Step 4: Convert response to speech
        audio_url = await tts.text_to_speech(llm_response, voice_id)
        
        # Step 5: Update chat history
        chat.add_message(session_id, "user", transcription)
        chat.add_message(session_id, "assistant", llm_response)
        
        processing_time = time.time() - start_time
        chat_history_length = chat.get_session_count(session_id)
        
        logger.info(f"Voice agent completed in {processing_time:.2f}s for session {session_id[:8]}...")
        
        return VoiceAgentResponse(
            session_id=session_id,
            transcription=transcription,
            llm_response=llm_response,
            audio_url=audio_url,
            chat_history_length=chat_history_length,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Voice agent error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat/{session_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str,
    chat: ChatService = Depends(get_chat_service)
):
    """Get chat history for a session."""
    logger.info(f"Chat history requested for session: {session_id[:8]}...")
    
    try:
        messages = chat.get_chat_history(session_id)
        
        return ChatHistoryResponse(
            session_id=session_id,
            messages=[
                {
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg["timestamp"]
                }
                for msg in messages
            ],
            total_messages=len(messages)
        )
    except Exception as e:
        logger.error(f"Chat history error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/chat/{session_id}")
async def clear_chat_history(
    session_id: str,
    chat: ChatService = Depends(get_chat_service)
):
    """Clear chat history for a session."""
    logger.info(f"Clearing chat history for session: {session_id[:8]}...")
    
    try:
        success = chat.clear_session(session_id)
        
        if success:
            return {"message": f"Chat history cleared for session {session_id}"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
            
    except Exception as e:
        logger.error(f"Clear chat history error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    services_status = {
        "stt_service": stt_service.health_check() if stt_service else False,
        "tts_service": tts_service.health_check() if tts_service else False,
        "llm_service": llm_service.health_check() if llm_service else False,
        "chat_service": True  # Chat service is always available
    }
    
    all_healthy = all(services_status.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": services_status,
        "timestamp": time.time()
    }


@app.get("/uploads/{filename}")
async def get_uploaded_file(filename: str):
    """Serve uploaded files."""
    file_path = Config.UPLOAD_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path)


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.error(f"HTTP {exc.status_code}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            status_code=exc.status_code
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc) if Config.DEBUG else None,
            status_code=500
        ).dict()
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info(f"Starting {Config.APP_TITLE} v{Config.APP_VERSION}")
    logger.info(f"Debug mode: {Config.DEBUG}")
    logger.info(f"Upload directory: {Config.UPLOAD_DIR}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down AI Voice Agent")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG
    )
