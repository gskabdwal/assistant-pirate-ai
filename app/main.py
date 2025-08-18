"""
AI Voice Agent - Refactored FastAPI Application.
"""
import logging
import time
import uuid
import asyncio
import json
from typing import Dict, Any
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import assemblyai as aai
from assemblyai.streaming.v3 import (
    BeginEvent,
    StreamingClient,
    StreamingClientOptions,
    StreamingError,
    StreamingEvents,
    StreamingParameters,
    StreamingSessionParameters,
    TerminationEvent,
    TurnEvent,
)

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


@app.get("/websocket-test", response_class=HTMLResponse)
async def get_websocket_test():
    """Serve the WebSocket test client."""
    logger.info("Serving WebSocket test client")
    test_file_path = Path(__file__).parent.parent / "websocket_test.html"
    
    if not test_file_path.exists():
        raise HTTPException(status_code=404, detail="WebSocket test file not found")
    
    with open(test_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return HTMLResponse(content=content)


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
            logger.warning(f"Empty transcription for session {session_id[:8]}")
            raise HTTPException(status_code=400, detail="No speech detected in audio. Please speak clearly and try again.")
        
        # Step 2: Add user message to chat history
        chat.add_message(session_id, "user", transcription)
        
        # Step 3: Get updated chat history for context
        chat_history = chat.get_chat_history(session_id)
        
        # Process the user's audio with the LLM
        logger.info(f"Processing user message with LLM for session {session_id[:8]}...")
        llm_response = await llm.generate_response(
            user_input=transcription,  # Changed from user_message to user_input
            chat_history=chat_history
        )
        
        # Add assistant's response to chat history
        chat.add_message(session_id, "assistant", llm_response)
        
        # Generate TTS for the response
        logger.info(f"Generating TTS for response in session {session_id[:8]}...")
        audio_url = await tts.text_to_speech(
            text=llm_response,
            voice_id=voice_id
        )
        
        processing_time = time.time() - start_time
        chat_history_length = chat.get_session_count(session_id)
        
        # Get recent messages for the frontend in the format it expects
        # The frontend expects an array of objects with 'role' and 'content' only
        chat_history = chat.get_chat_history(session_id, limit=10)
        recent_messages = [
            {
                'role': msg.get('role', 'user'),
                'content': msg.get('content', '')
            }
            for msg in chat_history
        ]
        
        logger.info(f"Voice agent completed in {processing_time:.2f}s for session {session_id[:8]}...")
        logger.info(f"Returning {len(recent_messages)} recent messages to frontend")
        
        # Create response with all required fields
        response = VoiceAgentResponse(
            session_id=session_id,
            transcription=transcription,
            llm_response=llm_response,
            audio_url=audio_url,
            chat_history_length=chat_history_length,
            recent_messages=recent_messages,
            processing_time=processing_time
        )
        
        # Log the response structure for debugging
        logger.debug(f"Response data: {response.dict()}")
        
        return response
        
    except HTTPException:
        # Re-raise HTTPExceptions as-is (they have proper status codes)
        raise
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Voice agent error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {error_traceback}")
        
        # Log the current state of variables
        logger.error(f"Session ID: {session_id}")
        logger.error(f"Voice ID: {voice_id}")
        logger.error(f"File info: {file.filename if file else 'No file'}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Voice agent error: {str(e)}"
        )


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


@app.websocket("/ws/audio-stream")
async def audio_stream_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for streaming audio data.
    Receives binary audio chunks and saves them to a file.
    """
    await websocket.accept()
    logger.info(f"Audio stream WebSocket connection established from {websocket.client}")
    
    # Generate unique filename for this session
    session_id = str(uuid.uuid4())
    audio_filename = f"streamed_audio_{session_id}_{int(time.time())}.wav"
    audio_file_path = Config.UPLOAD_DIR / audio_filename
    
    # Ensure upload directory exists
    Config.UPLOAD_DIR.mkdir(exist_ok=True)
    
    audio_chunks = []
    
    try:
        await websocket.send_text(f"Ready to receive audio stream. Session: {session_id}")
        
        while True:
            # Receive binary audio data
            message = await websocket.receive()
            
            if message["type"] == "websocket.receive":
                if "bytes" in message:
                    # Handle binary audio data
                    audio_data = message["bytes"]
                    audio_chunks.append(audio_data)
                    logger.debug(f"Received audio chunk: {len(audio_data)} bytes")
                    
                    # Send acknowledgment
                    await websocket.send_text(f"Received chunk: {len(audio_data)} bytes")
                    
                elif "text" in message:
                    # Handle text commands
                    text_message = message["text"]
                    logger.info(f"Received command: {text_message}")
                    
                    if text_message == "STOP_RECORDING":
                        # Save all audio chunks to file
                        if audio_chunks:
                            with open(audio_file_path, 'wb') as f:
                                for chunk in audio_chunks:
                                    f.write(chunk)
                            
                            file_size = audio_file_path.stat().st_size
                            logger.info(f"Saved audio stream to {audio_filename} ({file_size} bytes)")
                            
                            await websocket.send_text(f"Audio saved: {audio_filename} ({file_size} bytes)")
                        else:
                            await websocket.send_text("No audio data received")
                        
                        # Reset for next recording
                        audio_chunks = []
                        session_id = str(uuid.uuid4())
                        audio_filename = f"streamed_audio_{session_id}_{int(time.time())}.wav"
                        audio_file_path = Config.UPLOAD_DIR / audio_filename
                        
                    elif text_message == "START_RECORDING":
                        audio_chunks = []
                        await websocket.send_text(f"Started new recording session: {session_id}")
                        
                    else:
                        await websocket.send_text(f"Unknown command: {text_message}")
            
    except WebSocketDisconnect:
        logger.info(f"Audio stream WebSocket client disconnected: {websocket.client}")
        
        # Save any remaining audio data
        if audio_chunks:
            with open(audio_file_path, 'wb') as f:
                for chunk in audio_chunks:
                    f.write(chunk)
            file_size = audio_file_path.stat().st_size
            logger.info(f"Saved final audio stream to {audio_filename} ({file_size} bytes)")
            
    except Exception as e:
        logger.error(f"Audio stream WebSocket error: {str(e)}")
        try:
            await websocket.close()
        except:
            pass


@app.websocket("/ws/transcribe-stream")
async def transcribe_stream_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time audio transcription using AssemblyAI Universal-Streaming.
    Receives binary audio chunks and streams transcription results.
    """
    await websocket.accept()
    logger.info(f"Transcription stream WebSocket connection established from {websocket.client}")
    
    if not Config.ASSEMBLYAI_API_KEY:
        await websocket.send_text(json.dumps({
            "error": "AssemblyAI API key not configured"
        }))
        await websocket.close()
        return
    
    # Create streaming client with new Universal-Streaming API
    streaming_client = None
    
    # Store the main event loop for use in callbacks
    main_loop = asyncio.get_running_loop()
    
    def on_begin(client, event: BeginEvent):
        logger.info(f"AssemblyAI session started: {event.id}")
        print(f"TRANSCRIPTION SESSION STARTED: {event.id}")
    
    def on_turn(client, event: TurnEvent):
        logger.info(f"Turn transcript: {event.transcript} (end_of_turn: {event.end_of_turn})")
        print(f"TRANSCRIPTION: {event.transcript}")
        
        # Send to WebSocket client using the stored main loop
        asyncio.run_coroutine_threadsafe(
            send_turn_to_client(websocket, event),
            main_loop
        )
    
    def on_terminated(client, event: TerminationEvent):
        logger.info(f"AssemblyAI session terminated: {event.audio_duration_seconds} seconds processed")
        print(f"SESSION ENDED: {event.audio_duration_seconds}s processed")
    
    def on_error(client, error: StreamingError):
        logger.error(f"AssemblyAI streaming error: {error}")
        print(f"TRANSCRIPTION ERROR: {error}")
        # Send error to client without asyncio.create_task to avoid event loop issues
        asyncio.run_coroutine_threadsafe(
            send_error_to_client(websocket, str(error)), 
            asyncio.get_event_loop()
        )
    
    try:
        # Create streaming client
        streaming_client = StreamingClient(
            StreamingClientOptions(
                api_key=Config.ASSEMBLYAI_API_KEY,
                api_host="streaming.assemblyai.com"
            )
        )
        
        # Set up event handlers
        streaming_client.on(StreamingEvents.Begin, on_begin)
        streaming_client.on(StreamingEvents.Turn, on_turn)
        streaming_client.on(StreamingEvents.Termination, on_terminated)
        streaming_client.on(StreamingEvents.Error, on_error)
        
        # Connect to AssemblyAI
        streaming_client.connect(
            StreamingParameters(
                sample_rate=16000,
                format_turns=True
            )
        )
        
        await websocket.send_text(json.dumps({
            "status": "connected",
            "message": "Ready to receive audio for real-time transcription"
        }))
        
        while True:
            message = await websocket.receive()
            
            if message["type"] == "websocket.receive":
                if "bytes" in message:
                    # Stream audio data to AssemblyAI
                    audio_data = message["bytes"]
                    streaming_client.stream(audio_data)
                    logger.debug(f"Streamed {len(audio_data)} bytes to AssemblyAI")
                    
                elif "text" in message:
                    text_message = message["text"]
                    logger.info(f"Received command: {text_message}")
                    
                    if text_message == "STOP_TRANSCRIPTION":
                        streaming_client.disconnect(terminate=True)
                        await websocket.send_text(json.dumps({
                            "status": "stopped",
                            "message": "Transcription stopped"
                        }))
                        break
                    elif text_message == "START_TRANSCRIPTION":
                        await websocket.send_text(json.dumps({
                            "status": "started",
                            "message": "Transcription started"
                        }))
                    else:
                        await websocket.send_text(json.dumps({
                            "status": "unknown_command",
                            "message": f"Unknown command: {text_message}"
                        }))
            
    except WebSocketDisconnect:
        logger.info(f"Transcription stream WebSocket client disconnected: {websocket.client}")
        if streaming_client:
            streaming_client.disconnect(terminate=True)
        
    except Exception as e:
        logger.error(f"Transcription stream WebSocket error: {str(e)}")
        try:
            await websocket.send_text(json.dumps({
                "error": str(e)
            }))
            await websocket.close()
        except:
            pass
        finally:
            if streaming_client:
                streaming_client.disconnect(terminate=True)


async def send_turn_to_client(websocket: WebSocket, turn_event: TurnEvent):
    """Send turn event to WebSocket client."""
    try:
        await websocket.send_text(json.dumps({
            "type": "turn_transcript",
            "text": turn_event.transcript,
            "end_of_turn": turn_event.end_of_turn,
            "message": f"Transcript: {turn_event.transcript}"
        }))
    except Exception as e:
        logger.error(f"Error sending turn to client: {str(e)}")


async def send_error_to_client(websocket: WebSocket, error_message: str):
    """Send error to WebSocket client."""
    try:
        await websocket.send_text(json.dumps({
            "type": "error",
            "error": error_message,
            "message": f"Transcription error: {error_message}"
        }))
    except Exception as e:
        logger.error(f"Error sending error to client: {str(e)}")


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
