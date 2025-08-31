"""
AI Voice Agent - Refactored FastAPI Application.
"""
import logging
import asyncio
import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, Form, UploadFile, File, Depends
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
import uvicorn
import logging

from .config import Config
from .services.stt_service import STTService
from .services.tts_service import TTSService
from .services.llm_service import LLMService
from .services.chat_service import ChatService
from .services.skills.skill_manager import SkillManager
from app.config import Config

# AssemblyAI Streaming imports (v3 Universal-Streaming)
from assemblyai.streaming.v3 import StreamingClient, StreamingClientOptions, StreamingParameters, StreamingEvents, BeginEvent, TurnEvent, TerminationEvent, StreamingError

# Day 22 imports
import io
import wave

# Day 20 imports  
import websockets
from urllib.parse import urlparse, parse_qs

from .schemas import (
    TTSRequest, TTSResponse, TranscriptionResponse, LLMRequest, LLMResponse,
    VoiceAgentResponse, ErrorResponse, ChatHistoryResponse
)

# Day 27: API Configuration Models
class APIKeyRequest(BaseModel):
    service: str
    api_key: str

class APIKeysRequest(BaseModel):
    api_keys: Dict[str, str]

logger = logging.getLogger(__name__)

# Murf WebSocket streaming function
async def stream_murf_tts_websocket(client_websocket: WebSocket, text: str, voice_id: str, session_id: str):
    """Stream TTS audio from Murf WebSocket API directly to client"""
    try:
        murf_api_key = Config.get_api_key("MURF", session_id)
        if not murf_api_key:
            raise ValueError(f"Murf API key not configured for session {session_id}")
        
        murf_ws_url = f"wss://api.murf.ai/v1/speech/stream-input?api-key={murf_api_key}"
        
        async with websockets.connect(murf_ws_url) as murf_ws:
            # Send voice config first
            voice_config = {
                "voice_config": {
                    "voiceId": voice_id,
                    "style": "Conversational",
                    "rate": 0,
                    "pitch": 0,
                    "sampleRate": 44100,
                    "format": "WAV",
                    "channelType": "MONO",
                    "encodeAsBase64": True,
                    "variation": 1
                },
                "context_id": session_id
            }
            
            await murf_ws.send(json.dumps(voice_config))
            logger.info(f"Day 23: Sent Murf voice config: {voice_config}")
            
            # Send text for TTS
            text_message = {
                "text": text,
                "context_id": session_id,
                "end": True
            }
            
            await murf_ws.send(json.dumps(text_message))
            logger.info(f"Day 23: Sent text to Murf: {text[:100]}...")
            
            # Stream audio chunks back to client
            first_chunk = True
            while True:
                try:
                    response = await murf_ws.recv()
                    data = json.loads(response)
                    
                    if "audio" in data:
                        # Send audio chunk to client using Murf cookbook format
                        await client_websocket.send_text(json.dumps({
                            "type": "audio_chunk",
                            "data": data["audio"],
                            "is_first": first_chunk,
                            "session_id": session_id
                        }))
                        first_chunk = False
                        # logger.debug(f"Day 23: Streamed audio chunk to client")
                    
                    if data.get("isFinalAudio") or data.get("final"):
                        # logger.info("Day 23: Final audio chunk received from Murf")
                        await client_websocket.send_text(json.dumps({
                            "type": "audio_final",
                            "session_id": session_id
                        }))
                        break
                        
                except websockets.exceptions.ConnectionClosed:
                    logger.info("Day 23: Murf WebSocket connection closed")
                    break
                    
    except Exception as e:
        logger.error(f"Day 23: Murf WebSocket streaming error: {str(e)}")
        await client_websocket.send_text(json.dumps({
            "type": "error",
            "message": f"TTS streaming error: {str(e)}"
        }))

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
skill_manager = None

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
    
    # Initialize skill manager first
    skill_manager = SkillManager(
        tavily_api_key=Config.TAVILY_API_KEY,
        weather_api_key=Config.OPENWEATHER_API_KEY,
        news_api_key=Config.NEWS_API_KEY,
        translate_api_key=Config.GOOGLE_TRANSLATE_API_KEY
    )
    logger.info("🏴‍☠️ Skill Manager initialized")
        
    if Config.GEMINI_API_KEY:
        llm_service = LLMService(Config.GEMINI_API_KEY, skill_manager=skill_manager)
        logger.info("LLM service initialized successfully with special skills")
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


def get_skill_manager() -> SkillManager:
    """Get skill manager dependency."""
    if not skill_manager:
        raise HTTPException(status_code=503, detail="Skill manager not available")
    return skill_manager

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
            try:
                # Receive message from WebSocket
                message = await websocket.receive()
                
                # Handle disconnect messages
                if message["type"] == "websocket.disconnect":
                    logger.info("WebSocket disconnect message received")
                    break
                
                if message["type"] == "websocket.receive":
                    if "bytes" in message:
                        # Handle binary audio data
                        audio_data = message["bytes"]
                        audio_chunks.append(audio_data)
                        # logger.debug(f"Received audio chunk: {len(audio_data)} bytes")
                        
                        # Send acknowledgment (less frequent to avoid flooding)
                        if len(audio_chunks) % 10 == 0:  # Every 10th chunk
                            await websocket.send_text(f"Received {len(audio_chunks)} chunks")
                        
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
                                # logger.info(f"Saved audio stream to {audio_filename} ({file_size} bytes)")
                                
                                await websocket.send_text(f"Audio saved: {audio_filename} ({file_size} bytes)")
                                
                                # Schedule cleanup after 5 minutes
                                asyncio.create_task(cleanup_audio_file(audio_file_path, delay_seconds=300))
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
                logger.info("WebSocket disconnected during receive")
                break
            
    except WebSocketDisconnect:
        logger.info(f"Audio stream WebSocket client disconnected: {websocket.client}")
        
        # Save any remaining audio data
        if audio_chunks:
            with open(audio_file_path, 'wb') as f:
                for chunk in audio_chunks:
                    f.write(chunk)
            file_size = audio_file_path.stat().st_size
            # logger.info(f"Saved final audio stream to {audio_filename} ({file_size} bytes)")
            
            # Schedule cleanup after 5 minutes
            asyncio.create_task(cleanup_audio_file(audio_file_path, delay_seconds=300))
            
    except Exception as e:
        logger.error(f"Audio stream WebSocket error: {str(e)}")
        try:
            await websocket.close()
        except:
            pass


@app.websocket("/ws/llm-stream")
async def llm_stream_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for streaming LLM responses with Murf WebSocket TTS.
    Receives text input, streams LLM response, and sends to Murf for audio generation.
    """
    await websocket.accept()
    logger.info(f"LLM stream WebSocket connection established from {websocket.client}")
    
    if not Config.GEMINI_API_KEY:
        await websocket.send_text(json.dumps({
            "error": "Gemini API key not configured"
        }))
        await websocket.close()
        return
    
    llm = get_llm_service()
    chat = get_chat_service()
    tts = get_tts_service()
    
    try:
        while True:
            message = await websocket.receive()
            
            if message["type"] == "websocket.receive":
                if "text" in message:
                    data = json.loads(message["text"])
                    user_input = data.get("text", "")
                    session_id = data.get("session_id", "default-session")
                    voice_id = data.get("voice_id", "en-US-natalie")
                    
                    if not user_input:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "No text provided in request"
                        }))
                        continue
                    
                    logger.info(f"🚀 Day 20: Starting LLM streaming + Murf WebSocket TTS for: {user_input[:50]}...")
                    
                    # Get chat history for context
                    chat_history = chat.get_chat_history(session_id, limit=10)
                    
                    # Send start of stream
                    await websocket.send_text(json.dumps({
                        "type": "start",
                        "message": "Starting LLM stream"
                    }))
                    
                    # Stream the LLM response
                    full_response = ""
                    async for chunk in llm.stream_response(user_input, chat_history):
                        full_response += chunk
                        await websocket.send_text(json.dumps({
                            "type": "chunk",
                            "text": chunk,
                            "is_complete": False
                        }))
                    
                    # Send end of LLM stream
                    await websocket.send_text(json.dumps({
                        "type": "end",
                        "text": full_response,
                        "is_complete": True
                    }))
                    
                    # Update chat history
                    chat.add_message(session_id, "user", user_input)
                    chat.add_message(session_id, "assistant", full_response)
                    
                    # Day 20: Send the complete LLM response to Murf WebSocket for TTS
                    if full_response.strip():
                        logger.info(f"🎵 Sending LLM response to Murf WebSocket TTS: {len(full_response)} chars")
                        
                        await websocket.send_text(json.dumps({
                            "type": "tts_start",
                            "message": "Starting Murf WebSocket TTS generation"
                        }))
                        
                        try:
                            # Stream TTS from Murf WebSocket
                            async for tts_chunk in tts.stream_text_to_speech(
                                text=full_response,
                                voice_id=voice_id
                            ):
                                # Send TTS chunk to client
                                await websocket.send_text(json.dumps({
                                    "type": "tts_chunk",
                                    "data": tts_chunk,
                                    "is_final": tts_chunk.get("final", False)
                                }))
                                
                                # The base64 audio logging is already handled in the TTS service
                                
                            await websocket.send_text(json.dumps({
                                "type": "tts_complete",
                                "message": "Murf WebSocket TTS generation completed"
                            }))
                            
                        except Exception as tts_error:
                            import traceback
                            error_details = traceback.format_exc()
                            logger.error(f"Murf WebSocket TTS error: {str(tts_error)}")
                            logger.error(f"TTS Error traceback: {error_details}")
                            await websocket.send_text(json.dumps({
                                "type": "tts_error",
                                "message": f"TTS generation failed: {str(tts_error)}"
                            }))
                    
    except WebSocketDisconnect:
        logger.info(f"LLM stream WebSocket client disconnected: {websocket.client}")
    except Exception as e:
        logger.error(f"LLM stream WebSocket error: {str(e)}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e)
            }))
            await websocket.close()
        except:
            pass


@app.websocket("/ws/llm-to-murf")
async def llm_to_murf_websocket(websocket: WebSocket):
    """
    WebSocket endpoint that streams LLM responses to Murf TTS and returns audio.
    """
    await websocket.accept()
    logger.info(f"LLM to Murf WebSocket connection established from {websocket.client}")
    
    # Get dependencies
    try:
        llm = get_llm_service()
        tts = get_tts_service()
        chat = get_chat_service()
    except HTTPException as e:
        await websocket.close(code=1011, reason=e.detail)
        return
    
    try:
        # Receive initial message with user input and session ID
        message = await websocket.receive_text()
        data = json.loads(message)
        
        user_input = data.get("text", "")
        session_id = data.get("session_id", str(uuid.uuid4()))
        voice_id = data.get("voice_id", "en-US-natalie")
        
        if not user_input:
            raise WebSocketException(code=1008, reason="No text provided")
        
        logger.info(f"LLM to Murf request: {user_input[:50]}... (session: {session_id[:8]})")
        
        # Get chat history for context
        chat_history = chat.get_chat_history(session_id, limit=10)
        
        # Generate LLM response
        llm_response = ""
        full_response = ""
        
        # Stream the LLM response
        async for chunk in llm.stream_response(user_input, chat_history):
            llm_response += chunk
            full_response += chunk
            
            # Send text chunks to client as they come in
            await websocket.send_text(json.dumps({
                "type": "llm_chunk",
                "text": chunk,
                "is_complete": False
            }))
        
        # Add to chat history
        chat.add_message(session_id, "user", user_input)
        chat.add_message(session_id, "assistant", full_response)
        
        # Send LLM response complete message
        await websocket.send_text(json.dumps({
            "type": "llm_complete",
            "text": full_response
        }))
        
        # Stream TTS response
        logger.info(f"Streaming TTS for response (length: {len(full_response)} chars)")
        
        # Stream TTS chunks to client
        async for tts_chunk in tts.stream_text_to_speech(
            text=full_response,
            voice_id=voice_id
        ):
            # Send TTS data to client
            await websocket.send_text(json.dumps({
                "type": "tts_chunk",
                "data": tts_chunk,
                "is_final": tts_chunk.get("final", False)
            }))
            
            # Print base64 audio to console (as per requirements)
            # if "audio" in tts_chunk:
            #     print("\n" + "="*80)
            #     print("MURF TTS BASE64 AUDIO (first 100 chars):")
            #     print(tts_chunk["audio"][:100] + "...")
            #     print("="*80 + "\n")
        
        logger.info("LLM to Murf streaming completed successfully")
        
    except WebSocketDisconnect:
        logger.info("LLM to Murf WebSocket client disconnected")
    except json.JSONDecodeError:
        await websocket.close(code=1003, reason="Invalid JSON")
    except Exception as e:
        logger.error(f"LLM to Murf WebSocket error: {str(e)}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": "WebSocket error occurred"
            })
            await websocket.close(code=1011, reason="Error")
        except Exception:
            pass


@app.websocket("/ws/audio-stream-base64")
async def audio_stream_base64_websocket(websocket: WebSocket):
    """
    Day 22: WebSocket endpoint for streaming base64 audio data with seamless playback.
    Enhanced to handle client disconnections and reconnections properly.
    """
    await websocket.accept()
    
    # Extract session_id from query parameters
    session_id = websocket.query_params.get("session_id", "default")
    # logger.info(f"Day 22: Streaming audio WebSocket connection established from {websocket.client}")
    
    # Initialize session-based services for base64 audio streaming
    try:
        from .services.llm_service import LLMService
        from .services.tts_service import TTSService
        from .services.chat_service import ChatService
        from .services.skills.skill_manager import SkillManager
        
        # Get session-based API keys
        gemini_key = Config.get_api_key("GEMINI", session_id)
        murf_key = Config.get_api_key("MURF", session_id)
        
        if not gemini_key:
            raise ValueError(f"Gemini API key not configured for session {session_id}")
        if not murf_key:
            raise ValueError(f"Murf API key not configured for session {session_id}")
        
        # Initialize services with session keys
        skill_manager = SkillManager(
            tavily_api_key=Config.get_api_key("TAVILY", session_id),
            weather_api_key=Config.get_api_key("OPENWEATHER", session_id),
            news_api_key=Config.get_api_key("NEWS", session_id),
            translate_api_key=Config.get_api_key("GOOGLE_TRANSLATE", session_id)
        )
        
        llm = LLMService(gemini_key, skill_manager)
        tts = TTSService(murf_key)
        chat = ChatService()
        
    except Exception as e:
        error_msg = f"Service initialization failed for session {session_id}: {str(e)}"
        logger.error(f"Base64 audio stream: {error_msg}")
        try:
            await websocket.send_json({
                "type": "error", 
                "message": "API keys not configured"
            })
            await websocket.close(code=1011, reason="Config error")
        except Exception:
            pass
        return
    
    try:
        # Send ready message
        await websocket.send_text(json.dumps({
            "type": "ready",
            "message": "Ready to stream and play audio"
        }))
        
        while True:
            try:
                message = await websocket.receive()
                
                if message["type"] == "websocket.disconnect":
                    logger.info("Day 22: Client requested disconnect")
                    break
                    
                if message["type"] == "websocket.receive":
                    if "text" in message:
                        data = json.loads(message["text"])
                        user_input = data.get("text", "")
                        session_id = data.get("session_id", str(uuid.uuid4()))
                        voice_id = data.get("voice_id", "en-US-natalie")
                        
                        logger.info(f"Day 22: Processing request - Text: {user_input[:50]}..., Session: {session_id[:8]}")
                        
                        if not user_input:
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "message": "No text provided in request"
                            }))
                            continue
                        
                        # logger.info(f"🎵 Day 22: Starting streaming audio playback for: {user_input[:50]}...")
                        
                        # Get chat history for context
                        chat_history = chat.get_chat_history(session_id, limit=10)
                        
                        # Generate LLM response
                        llm_response = ""
                        async for chunk in llm.stream_response(user_input, chat_history):
                            llm_response += chunk
                            
                            # Send text chunks to client
                            await websocket.send_text(json.dumps({
                                "type": "llm_chunk",
                                "text": chunk,
                                "is_complete": False
                            }))
                        
                        # Update chat history
                        chat.add_message(session_id, "user", user_input)
                        chat.add_message(session_id, "assistant", llm_response)
                        
                        # Send LLM response complete
                        await websocket.send_text(json.dumps({
                            "type": "llm_complete",
                            "text": llm_response
                        }))
                        
                        # Day 22: Stream base64 audio chunks for seamless playback
                        if llm_response.strip():
                            # logger.info(f"🎵 Day 22: Streaming audio for seamless playback: {len(llm_response)} chars")
                            
                            await websocket.send_text(json.dumps({
                                "type": "audio_stream_start",
                                "message": "Starting streaming audio playback"
                            }))
                            
                            try:
                                # Stream TTS base64 chunks for real-time playback
                                chunk_index = 0
                                final_chunk_sent = False
                                
                                async for tts_chunk in tts.stream_text_to_speech(
                                    text=llm_response,
                                    voice_id=voice_id
                                ):
                                    # Send base64 audio chunk for immediate playback
                                    if "audio" in tts_chunk:
                                        chunk_index += 1
                                        is_final = tts_chunk.get("final", False)
                                        
                                        await websocket.send_text(json.dumps({
                                            "type": "audio_chunk",
                                            "data": tts_chunk["audio"],  # Base64 audio data
                                            "is_final": is_final,
                                            "chunk_index": chunk_index
                                        }))
                                        
                                        # Log streaming audio chunk
                                        # logger.info(f"🎵 Day 22: Sent streaming audio chunk {chunk_index} for playback ({len(tts_chunk['audio'])} chars) - Final: {is_final}")
                                        
                                        if is_final:
                                            final_chunk_sent = True
                                            logger.info(f"🎵 Day 22: Final chunk {chunk_index} sent, streaming will complete")
                                
                                # Always send completion message after the streaming loop ends
                                logger.info(f"🎵 Day 22: TTS streaming loop completed, sending completion message (final_chunk_sent: {final_chunk_sent})")
                                await websocket.send_text(json.dumps({
                                    "type": "audio_stream_complete",
                                    "message": f"Streaming audio playback completed - {chunk_index} chunks sent"
                                }))
                                
                            except Exception as tts_error:
                                import traceback
                                error_details = traceback.format_exc()
                                # logger.error(f"Day 22: Streaming audio error: {str(tts_error)}")
                                logger.error(f"Day 22: Error traceback: {error_details}")
                                error_detail = str(tts_error) if str(tts_error) else "TTS streaming connection terminated unexpectedly"
                                logger.error(f"TTS streaming failed with error: {error_detail}")
                                await websocket.send_text(json.dumps({
                                    "type": "audio_stream_error",
                                    "message": f"Streaming audio failed: {error_detail}"
                                }))
                            
            except WebSocketDisconnect:
                logger.info("Day 22: Client disconnected during message processing")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Day 22: Invalid JSON received: {str(e)}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
            except Exception as e:
                logger.error(f"Day 22: Error processing message: {str(e)}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Processing error: {str(e)}"
                }))
                        
    except WebSocketDisconnect:
        # logger.info(f"Day 22: Streaming audio WebSocket client disconnected: {websocket.client}")
        pass
    except Exception as e:
        # logger.error(f"Day 22: Streaming audio WebSocket error: {str(e)}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e)
            }))
        except:
            pass
    finally:
        # logger.info(f"Day 22: Streaming audio WebSocket connection closed for {websocket.client}")
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
    
    # Extract session_id from query parameters
    session_id = websocket.query_params.get("session_id", "default")
    logger.info(f"Transcription stream WebSocket connection established from {websocket.client} for session {session_id}")
    
    assemblyai_key = Config.get_api_key("ASSEMBLYAI", session_id)
    if not assemblyai_key:
        await websocket.send_text(json.dumps({
            "error": f"AssemblyAI API key not configured for session {session_id}"
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
    
    def on_turn(client, event):
        logger.info(f"Turn transcript: {event.transcript} (end_of_turn: {event.end_of_turn})")
        print(f"TRANSCRIPTION: {event.transcript} (end_of_turn: {event.end_of_turn})")
        
        # Send to WebSocket client using the stored main loop
        asyncio.run_coroutine_threadsafe(
            send_turn_to_client(websocket, event),
            main_loop
        )
        
        # If this is the start of a new turn, send a turn_detected event
        if not event.end_of_turn and event.transcript.strip():
            logger.info(f"New turn detected: {event.transcript[:50]}...")
            asyncio.run_coroutine_threadsafe(
                websocket.send_text(json.dumps({
                    "type": "turn_detected",
                    "text": event.transcript,
                    "timestamp": time.time()
                })),
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
        # Create streaming client with session API key
        logger.info(f"Day 17: Creating StreamingClient with key: {assemblyai_key[:8] if assemblyai_key else 'None'}... (session: {session_id})")
        
        if not assemblyai_key:
            raise ValueError(f"AssemblyAI API key not configured for session {session_id}")
            
        streaming_client = StreamingClient(
            StreamingClientOptions(
                api_key=assemblyai_key,
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
                    # logger.debug(f"Streamed {len(audio_data)} bytes to AssemblyAI")
                    
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


async def send_turn_to_client(websocket: WebSocket, turn_event):
    """Send turn event to WebSocket client."""
    try:
        # Send appropriate message type based on end_of_turn status
        if turn_event.end_of_turn:
            message_type = "final_transcript"
        else:
            message_type = "partial_transcript"
            
        message = {
            "type": message_type,
            "text": turn_event.transcript,
            "end_of_turn": turn_event.end_of_turn,
            "timestamp": time.time()
        }
        
        # Add additional metadata if available
        if hasattr(turn_event, 'speaker'):
            message["speaker"] = turn_event.speaker
            
        if hasattr(turn_event, 'confidence'):
            message["confidence"] = turn_event.confidence
            
        await websocket.send_text(json.dumps(message))
        logger.info(f"Day 23: Sent {message_type}: '{turn_event.transcript}'")
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


@app.websocket("/ws/complete-voice-agent")
async def complete_voice_agent_websocket(websocket: WebSocket):
    """
    Day 23: Complete Voice Agent WebSocket endpoint.
    Integrates Day 17 (Real-time Transcription) and Day 22 (Streaming Audio Playbook)
    for a complete conversational AI experience.
    
    Pipeline: Recording → Real-time STT → LLM → Streaming TTS → Audio Playback
    """
    # Accept with ping interval to prevent timeout
    await websocket.accept()
    
    # Extract session_id from query parameters
    session_id = websocket.query_params.get("session_id", "default")
    logger.info(f"Day 23: Complete Voice Agent WebSocket connection established from {websocket.client} for session {session_id}")
    
    # Start keepalive task to prevent timeout
    keepalive_task = None
    
    async def keepalive():
        """Send periodic ping to keep connection alive"""
        try:
            while True:
                await asyncio.sleep(30)  # Send ping every 30 seconds
                try:
                    await websocket.ping()
                    logger.debug("Day 23: Sent WebSocket ping")
                except Exception as ping_error:
                    logger.warning(f"Day 23: Ping failed: {ping_error}")
                    break
        except asyncio.CancelledError:
            logger.info("Day 23: Keepalive task cancelled")
        except Exception as e:
            logger.error(f"Day 23: Keepalive error: {e}")
    
    keepalive_task = asyncio.create_task(keepalive())
    
    # Initialize session-based services
    try:
        logger.info(f"Day 23: Initializing services for session {session_id}...")
        
        # Initialize services with session-based API keys
        from .services.stt_service import STTService
        from .services.tts_service import TTSService
        from .services.llm_service import LLMService
        from .services.chat_service import ChatService
        
        # Get session-based API keys
        assemblyai_key = Config.get_api_key("ASSEMBLYAI", session_id)
        murf_key = Config.get_api_key("MURF", session_id)
        gemini_key = Config.get_api_key("GEMINI", session_id)
        
        logger.info(f"Day 23: Retrieved API keys - AssemblyAI: {'✓' if assemblyai_key else '✗'}, Murf: {'✓' if murf_key else '✗'}, Gemini: {'✓' if gemini_key else '✗'}")
        
        if not assemblyai_key:
            raise ValueError(f"AssemblyAI API key not configured for session {session_id}")
        if not murf_key:
            raise ValueError(f"Murf API key not configured for session {session_id}")
        if not gemini_key:
            raise ValueError(f"Gemini API key not configured for session {session_id}")
        
        # Initialize services
        stt = STTService(assemblyai_key)
        tts = TTSService(murf_key)
        
        # Initialize skill manager with session keys
        from .services.skills.skill_manager import SkillManager
        skill_manager = SkillManager(
            tavily_api_key=Config.get_api_key("TAVILY", session_id),
            weather_api_key=Config.get_api_key("OPENWEATHER", session_id),
            news_api_key=Config.get_api_key("NEWS", session_id),
            translate_api_key=Config.get_api_key("GOOGLE_TRANSLATE", session_id)
        )
        
        llm = LLMService(gemini_key, skill_manager)
        chat = ChatService()
        
        logger.info(f"Day 23: All services initialized for session {session_id}")
        
    except Exception as e:
        error_msg = f"Service initialization failed for session {session_id}: {str(e)}"
        logger.error(f"Day 23: {error_msg}")
        # Send error message via WebSocket before closing (avoid long close reason)
        try:
            await websocket.send_json({
                "type": "error",
                "message": "API keys not configured. Please configure API keys in the settings.",
                "details": str(e)
            })
            await websocket.close(code=1011, reason="API keys missing")
        except Exception as close_error:
            logger.error(f"Day 23: Error closing WebSocket: {close_error}")
        return
    
    # AssemblyAI streaming client - will be created per session
    streaming_client = None
    main_loop = asyncio.get_running_loop()
    
    # Pipeline state
    current_session_id = None
    current_voice_id = "en-US-natalie"
    is_recording = False
    is_processing = False
    accumulated_transcript = ""
    streaming_client = None
    last_final_transcript = ""
    final_transcript_timer = None
    
    def on_begin(client, event: BeginEvent):
        logger.info(f"AssemblyAI session started: {event.id}")
        print(f"Day 23: TRANSCRIPTION SESSION STARTED: {event.id}")
        asyncio.run_coroutine_threadsafe(
            websocket.send_text(json.dumps({
                "type": "stt_started",
                "message": "Speech-to-text started",
                "session_id": event.id
            })),
            main_loop
        )
    
    def on_turn(client, event: TurnEvent):
        nonlocal accumulated_transcript
        
        logger.info(f"Day 23: Turn transcript: '{event.transcript}' (end_of_turn: {event.end_of_turn})")
        print(f"Day 23: TRANSCRIPTION: '{event.transcript}' | END_OF_TURN: {event.end_of_turn}")
        
        # ALWAYS send turn events to client, even if empty
        asyncio.run_coroutine_threadsafe(
            send_turn_to_client(websocket, event),
            main_loop
        )
        
        if event.end_of_turn:
            if event.transcript.strip():
                # Final transcript received - wait for potential refinement
                nonlocal last_final_transcript, final_transcript_timer
                last_final_transcript = event.transcript
                print(f"Day 23: FINAL TRANSCRIPT RECEIVED: '{event.transcript}' - waiting for refinement...")
                
                # Cancel previous timer if exists
                if final_transcript_timer:
                    final_transcript_timer.cancel()
                
                # Set timer to process transcript after 1 second (wait for refinement)
                final_transcript_timer = asyncio.run_coroutine_threadsafe(
                    process_refined_transcript(event.transcript, websocket),
                    main_loop
                )
            else:
                # End of turn but no speech detected
                print(f"Day 23: END OF TURN - NO SPEECH DETECTED")
                asyncio.run_coroutine_threadsafe(
                    websocket.send_text(json.dumps({
                        "type": "no_speech_detected",
                        "message": "No speech detected, resetting pipeline"
                    })),
                    main_loop
                )
    
    def on_error(client, error: StreamingError):
        logger.error(f"Day 23: AssemblyAI streaming error: {error}")
        print(f"Day 23: TRANSCRIPTION ERROR: {error}")
        asyncio.run_coroutine_threadsafe(
            websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Speech-to-text error: {error}",
                "step": "stt"
            })),
            main_loop
        )
    
    def on_terminated(client, event: TerminationEvent):
        logger.info(f"Day 23: AssemblyAI session terminated: {event.audio_duration_seconds}s")
        print(f"Day 23: SESSION ENDED: {event.audio_duration_seconds}s processed")
    
    async def process_refined_transcript(transcript: str, websocket: WebSocket):
        """Wait for potential transcript refinement, then process the final version."""
        try:
            # Wait 1 second for potential refinement
            await asyncio.sleep(1.0)
            
            # Use the latest transcript (may have been updated by newer final transcripts)
            final_transcript = last_final_transcript
            print(f"Day 23: PROCESSING REFINED FINAL TRANSCRIPT: '{final_transcript}'")
            
            # Send the refined transcript to UI for chat history
            await websocket.send_text(json.dumps({
                "type": "refined_final_transcript",
                "text": final_transcript
            }))
            
            # Process with LLM and TTS
            await process_with_llm_and_tts(final_transcript)
            
        except asyncio.CancelledError:
            print(f"Day 23: Transcript processing cancelled - newer transcript received")
        except Exception as e:
            logger.error(f"Error processing refined transcript: {str(e)}")
    
    async def send_turn_to_client(websocket: WebSocket, turn_event: TurnEvent):
        """Send turn event to WebSocket client - adapted from Day 17."""
        try:
            if not turn_event.end_of_turn:
                # Partial transcript
                await websocket.send_text(json.dumps({
                    "type": "partial_transcript",
                    "text": turn_event.transcript
                }))
            else:
                # Final transcript
                await websocket.send_text(json.dumps({
                    "type": "pipeline_status",
                    "step": "stt",
                    "status": "complete"
                }))
                
                await websocket.send_text(json.dumps({
                    "type": "final_transcript",
                    "text": turn_event.transcript
                }))
        except Exception as e:
            logger.error(f"Day 23: Error sending turn to client: {str(e)}")
    
    def create_streaming_client():
        """Create a new StreamingClient instance for each recording session."""
        try:
            # Get the current API key for this session
            current_api_key = Config.get_api_key("ASSEMBLYAI", session_id)
            logger.info(f"Day 23: Creating new StreamingClient with key: {current_api_key[:8] if current_api_key else 'None'}... (session: {session_id})")
            
            if not current_api_key:
                raise ValueError(f"AssemblyAI API key not configured for session {session_id}")
            
            client = StreamingClient(
                StreamingClientOptions(
                    api_key=current_api_key,
                    api_host="streaming.assemblyai.com"
                )
            )
            
            # Set up event handlers for the new client
            client.on(StreamingEvents.Begin, on_begin)
            client.on(StreamingEvents.Turn, on_turn)
            client.on(StreamingEvents.Error, on_error)
            client.on(StreamingEvents.Termination, on_terminated)
            
            logger.info("Day 23: New StreamingClient created successfully")
            return client
        except Exception as e:
            logger.error(f"Day 23: Failed to create StreamingClient: {str(e)}")
            raise e
    
    async def process_with_llm_and_tts(transcript: str):
        """Process transcript with LLM and stream TTS response."""
        nonlocal is_processing
        is_processing = True
        
        try:
            # Update pipeline status
            await websocket.send_text(json.dumps({
                "type": "pipeline_status",
                "step": "ai",
                "status": "thinking"
            }))
            
            # Get chat history for context
            chat_history = chat.get_chat_history(current_session_id, limit=10)
            
            # Add user message to chat history
            chat.add_message(current_session_id, "user", transcript)
            
            # Stream LLM response
            llm_response = ""
            await websocket.send_text(json.dumps({
                "type": "pipeline_status",
                "step": "ai",
                "status": "processing"
            }))
            
            async for chunk in llm.stream_response(transcript, chat_history):
                llm_response += chunk
                await websocket.send_text(json.dumps({
                    "type": "llm_chunk",
                    "text": chunk,
                    "is_complete": False
                }))
            
            # Add assistant response to chat history
            chat.add_message(current_session_id, "assistant", llm_response)
            
            # Send LLM complete
            await websocket.send_text(json.dumps({
                "type": "llm_complete",
                "text": llm_response
            }))
            
            await websocket.send_text(json.dumps({
                "type": "pipeline_status",
                "step": "ai",
                "status": "complete"
            }))
            
            # Start TTS streaming
            await websocket.send_text(json.dumps({
                "type": "pipeline_status",
                "step": "tts",
                "status": "generating"
            }))
            
            # Stream TTS audio chunks
            chunk_index = 0
            async for tts_chunk in tts.stream_text_to_speech(
                text=llm_response,
                voice_id=current_voice_id
            ):
                if "audio" in tts_chunk:
                    chunk_index += 1
                    is_final = tts_chunk.get("final", False)
                    
                    await websocket.send_text(json.dumps({
                        "type": "audio_chunk",
                        "data": tts_chunk["audio"],
                        "is_final": is_final,
                        "chunk_index": chunk_index
                    }))
                    
                    # logger.info(f"Day 23: Sent audio chunk {chunk_index} (Final: {is_final})")
            
            # Send TTS complete
            await websocket.send_text(json.dumps({
                "type": "tts_complete",
                "message": f"Speech generation complete - {chunk_index} chunks sent"
            }))
            
            # Send pipeline complete
            await websocket.send_text(json.dumps({
                "type": "pipeline_complete",
                "message": "Voice agent pipeline complete",
                "transcript": transcript,
                "response": llm_response,
                "chunks_sent": chunk_index
            }))
            
        except Exception as e:
            logger.error(f"Day 23: Error in LLM/TTS processing: {str(e)}")
            await websocket.send_text(json.dumps({
                "type": "pipeline_error",
                "message": f"Processing error: {str(e)}"
            }))
        finally:
            is_processing = False
    
    try:
        # Send ready message
        logger.info("Day 23: Sending ready message to client...")
        await websocket.send_text(json.dumps({
            "type": "ready",
            "message": "Complete Voice Agent ready"
        }))
        logger.info("Day 23: Ready message sent successfully")
        
        while True:
            message = await websocket.receive()
            
            if message["type"] == "websocket.disconnect":
                logger.info("Day 23: Client requested disconnect")
                break
            
            if message["type"] == "websocket.receive":
                if "text" in message:
                    try:
                        data = json.loads(message["text"])
                        message_type = data.get("type", "")
                        
                        if message_type == "start_recording":
                            current_session_id = data.get("session_id", str(uuid.uuid4()))
                            current_voice_id = data.get("voice_id", "en-US-natalie")
                            
                            logger.info(f"Day 23: Starting recording for session {current_session_id}")
                            
                            # Clean up any existing StreamingClient before creating new one
                            if streaming_client is not None:
                                try:
                                    logger.info("Day 23: Cleaning up previous StreamingClient")
                                    streaming_client.disconnect(terminate=True)
                                    streaming_client = None
                                except Exception as cleanup_error:
                                    logger.warning(f"Day 23: Error cleaning up previous StreamingClient: {cleanup_error}")
                            
                            # Send pipeline status update
                            await websocket.send_text(json.dumps({
                                "type": "pipeline_status",
                                "step": "recording",
                                "status": "active"
                            }))
                            
                            # Create new StreamingClient for this session
                            try:
                                streaming_client = create_streaming_client()
                                logger.info("Day 23: Starting AssemblyAI StreamingClient")
                                streaming_client.connect(
                                    StreamingParameters(
                                        sample_rate=16000,
                                        format_turns=True
                                    )
                                )
                                
                                is_recording = True
                                accumulated_transcript = ""
                                
                                await websocket.send_text(json.dumps({
                                    "type": "recording_started",
                                    "message": "Recording started",
                                    "session_id": current_session_id
                                }))
                            except Exception as e:
                                logger.error(f"Day 23: Failed to start recording: {str(e)}")
                                await websocket.send_text(json.dumps({
                                    "type": "error",
                                    "message": f"Failed to start recording: {str(e)}"
                                }))
                            
                        elif message_type == "stop_recording":
                            logger.info("Day 23: Stopping AssemblyAI StreamingClient")
                            streaming_client.disconnect(terminate=True)
                            
                            is_recording = False
                            
                            # Send pipeline status update
                            await websocket.send_text(json.dumps({
                                "type": "pipeline_status",
                                "step": "recording",
                                "status": "complete"
                            }))
                            
                            await websocket.send_text(json.dumps({
                                "type": "recording_stopped",
                                "message": "Recording stopped"
                            }))
                            
                            # Note: LLM processing is handled by process_with_llm_and_tts() 
                            # function called from AssemblyAI turn event handler.
                            # No need for duplicate processing here.
                            
                        elif message_type == "clear_chat":
                            chat_session_id = data.get("session_id", session_id)
                            chat.clear_history(chat_session_id)
                            
                            await websocket.send_text(json.dumps({
                                "type": "chat_history",
                                "messages": [],
                                "count": 0
                            }))
                            
                        else:
                            logger.warning(f"Day 23: Unknown message type: {message_type}")
                            await websocket.send_text(json.dumps({
                                "type": "unknown_command",
                                "message": f"Unknown message type: {message_type}"
                            }))
                            
                    except json.JSONDecodeError:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "Invalid JSON format"
                        }))
                
                elif "bytes" in message and is_recording:
                    # Stream audio data to AssemblyAI StreamingClient
                    audio_data = message["bytes"]
                    print(f"Day 23: RECEIVED AUDIO CHUNK: {len(audio_data)} bytes")
                    # logger.info(f"Day 23: Received audio chunk: {len(audio_data)} bytes")
                    
                    # Check if audio contains actual data (not just silence)
                    non_zero_bytes = sum(1 for b in audio_data if b != 0)
                    silence_ratio = (len(audio_data) - non_zero_bytes) / len(audio_data)
                    print(f"Day 23: AUDIO ANALYSIS - Non-zero bytes: {non_zero_bytes}/{len(audio_data)} ({(1-silence_ratio)*100:.1f}% content)")
                    # logger.info(f"Day 23: Audio analysis - Non-zero bytes: {non_zero_bytes}/{len(audio_data)} ({(1-silence_ratio)*100:.1f}% content)")
                    
                    if non_zero_bytes > 0:
                        print(f"Day 23: STREAMING TO ASSEMBLYAI - {len(audio_data)} bytes")
                        streaming_client.stream(audio_data)
                        # logger.debug(f"Day 23: Streamed {len(audio_data)} bytes to AssemblyAI")
                    else:
                        print(f"Day 23: SKIPPING SILENT CHUNK - all zeros")
    
    except WebSocketDisconnect:
        logger.info(f"Day 23: Complete Voice Agent WebSocket client disconnected: {websocket.client}")
    except Exception as e:
        logger.error(f"Day 23: Complete Voice Agent WebSocket error: {str(e)}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e)
            }))
        except:
            pass
    finally:
        # Cancel keepalive task
        if keepalive_task and not keepalive_task.done():
            keepalive_task.cancel()
            try:
                await keepalive_task
            except asyncio.CancelledError:
                pass
        
        # Clean up AssemblyAI connection
        try:
            if streaming_client:
                streaming_client.disconnect(terminate=True)
        except:
            pass
        
        logger.info(f"Day 23: Complete Voice Agent WebSocket connection closed for {websocket.client}")
        try:
            await websocket.close()
        except:
            pass


# Day 27: API Configuration Endpoints
@app.get("/api/config/status")
async def get_api_status(session_id: str = "default"):
    """Get status of all API keys for specific session."""
    return Config.get_api_status(session_id)

@app.get("/api/debug/env")
async def debug_env():
    """Debug endpoint to check environment variables."""
    import os
    env_vars = {
        'ASSEMBLYAI_API_KEY': '✓' if os.getenv('ASSEMBLYAI_API_KEY') else '✗',
        'MURF_API_KEY': '✓' if os.getenv('MURF_API_KEY') else '✗',
        'GEMINI_API_KEY': '✓' if os.getenv('GEMINI_API_KEY') else '✗',
        'TAVILY_API_KEY': '✓' if os.getenv('TAVILY_API_KEY') else '✗',
        'OPENWEATHER_API_KEY': '✓' if os.getenv('OPENWEATHER_API_KEY') else '✗',
        'NEWS_API_KEY': '✓' if os.getenv('NEWS_API_KEY') else '✗',
        'GOOGLE_TRANSLATE_API_KEY': '✓' if os.getenv('GOOGLE_TRANSLATE_API_KEY') else '✗',
    }
    return {
        'env_file_path': str(Config.BASE_DIR / '.env'),
        'env_file_exists': (Config.BASE_DIR / '.env').exists(),
        'environment_variables': env_vars,
        'runtime_keys': list(Config._runtime_api_keys.keys())
    }

@app.post("/api/config/key")
async def set_api_key(request: APIKeyRequest, session_id: str = "default"):
    """Set a single API key for specific session."""
    try:
        logger.info(f"🔧 API Key Update Request - Service: {request.service}, Key: {request.api_key[:8]}... (session: {session_id})")
        
        # Set the API key for this session
        Config.set_api_key(request.service, request.api_key, session_id)
        logger.info(f"✅ API key stored for {request.service} (session: {session_id})")
        
        # Verify the key was stored correctly
        stored_key = Config.get_api_key(request.service, session_id)
        logger.info(f"🔍 Verification - Stored key for {request.service}: {stored_key[:8] if stored_key else 'None'}... (session: {session_id})")
        
        # Reinitialize services when API keys are updated
        logger.info("🔄 Starting service reinitialization...")
        await reinitialize_services(session_id)
        logger.info("✅ Service reinitialization completed")
        
        return {"success": True, "message": f"API key for {request.service} updated and services reinitialized"}
    except Exception as e:
        logger.error(f"❌ Error setting API key for {request.service}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/config/reinitialize")
async def force_reinitialize_services():
    """Force reinitialize all services with current API keys."""
    try:
        await reinitialize_services()
        return {"success": True, "message": "All services reinitialized successfully"}
    except Exception as e:
        logger.error(f"Error reinitializing services: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def reinitialize_services(session_id: str = "default"):
    """Reinitialize services when API keys are updated."""
    global stt_service, tts_service, llm_service, skill_manager
    
    try:
        logger.info("🔄 === STARTING SERVICE REINITIALIZATION ===")
        
        # Note: Services are now session-aware and initialized per request
        # Global service reinitialization is no longer needed
        logger.info("🔄 Session-based services - no global reinitialization needed")
        
        # Reinitialize STT service
        assemblyai_key = Config.get_api_key("ASSEMBLYAI", session_id)
        logger.info(f"🔍 AssemblyAI key retrieved: {assemblyai_key[:8] if assemblyai_key else 'None'}...")
        if assemblyai_key:
            from .services.stt_service import STTService
            old_service = stt_service if 'stt_service' in globals() else None
            logger.info(f"🗑️ Old STT service: {type(old_service).__name__ if old_service else 'None'}")
            stt_service = STTService(assemblyai_key)
            logger.info(f"✅ NEW STT service created: {type(stt_service).__name__} with key {assemblyai_key[:8]}...")
        else:
            logger.warning("⚠️ No AssemblyAI key found, STT service not reinitialized")
        
        # Reinitialize TTS service
        murf_key = Config.get_api_key("MURF", session_id)
        logger.info(f"🔍 Murf key retrieved: {murf_key[:8] if murf_key else 'None'}...")
        if murf_key:
            from .services.tts_service import TTSService
            old_service = tts_service if 'tts_service' in globals() else None
            logger.info(f"🗑️ Old TTS service: {type(old_service).__name__ if old_service else 'None'}")
            tts_service = TTSService(murf_key)
            logger.info(f"✅ NEW TTS service created: {type(tts_service).__name__} with key {murf_key[:8]}...")
        else:
            logger.warning("⚠️ No Murf key found, TTS service not reinitialized")
        
        # Reinitialize skill manager first
        logger.info("🔄 Reinitializing Skill Manager...")
        from .services.skills.skill_manager import SkillManager
        skill_manager = SkillManager(
            tavily_api_key=Config.get_api_key("TAVILY", session_id),
            weather_api_key=Config.get_api_key("OPENWEATHER", session_id),
            news_api_key=Config.get_api_key("NEWS", session_id),
            translate_api_key=Config.get_api_key("GOOGLE_TRANSLATE", session_id)
        )
        logger.info("🏴‍☠️ Skill Manager reinitialized")
        
        # Reinitialize LLM service with skill manager
        gemini_key = Config.get_api_key("GEMINI", session_id)
        logger.info(f"🔍 Gemini key retrieved: {gemini_key[:8] if gemini_key else 'None'}...")
        if gemini_key:
            from .services.llm_service import LLMService
            old_service = llm_service if 'llm_service' in globals() else None
            logger.info(f"🗑️ Old LLM service: {type(old_service).__name__ if old_service else 'None'}")
            llm_service = LLMService(gemini_key, skill_manager=skill_manager)
            logger.info(f"✅ NEW LLM service created: {type(llm_service).__name__} with key {gemini_key[:8]}...")
        else:
            logger.warning("⚠️ No Gemini key found, LLM service not reinitialized")
        
        logger.info("🎉 === SERVICE REINITIALIZATION COMPLETED ===")
        
    except Exception as e:
        logger.error(f"❌ Error reinitializing services: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")

@app.delete("/api/config/session/{session_id}")
async def clear_session_keys(session_id: str):
    """Clear all API keys for a specific session."""
    try:
        Config.clear_session_keys(session_id)
        return {"success": True, "message": f"Cleared API keys for session {session_id}"}
    except Exception as e:
        logger.error(f"Error clearing session keys: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/config/test")
async def test_api_keys(session_id: str = "default"):
    """Test all configured API keys for specific session."""
    services = ['MURF', 'ASSEMBLYAI', 'GEMINI', 'TAVILY', 'OPENWEATHER', 'NEWS', 'GOOGLE_TRANSLATE']
    results = {}
    
    for service in services:
        api_key = Config.get_api_key(service, session_id)
        service_lower = service.lower()
        
        if not api_key:
            results[service_lower] = {
                'status': 'missing',
                'message': 'API key not configured'
            }
            continue
        
        # Basic validation - check if key looks valid
        if len(api_key.strip()) < 10:
            results[service_lower] = {
                'status': 'error',
                'message': 'API key appears to be too short'
            }
            continue
        
        # For now, just mark as valid if key exists and has reasonable length
        # In a production app, you'd make actual API calls to test
        results[service_lower] = {
            'status': 'valid',
            'message': 'API key format appears valid'
        }
    
    return results

@app.post("/api/config/test")
async def test_api_keys():
    """Test API key connectivity by making actual API calls when possible."""
    import httpx
    import google.generativeai as genai
    from assemblyai import Transcriber
    
    results = {}
    
    async def test_assemblyai(key: str) -> dict:
        """Test AssemblyAI API key by making a test request."""
        try:
            transcriber = Transcriber(api_key=key)
            # Test with a small audio file or list models
            models = transcriber.get_transcription_models()
            if models and isinstance(models, list):
                return {'status': 'valid', 'message': 'API key is valid'}
            return {'status': 'error', 'message': 'Invalid API key'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    async def test_gemini(key: str) -> dict:
        """Test Gemini API key by initializing the client."""
        try:
            genai.configure(api_key=key)
            # List available models as a test
            models = genai.list_models()
            if models:
                return {'status': 'valid', 'message': 'API key is valid'}
            return {'status': 'error', 'message': 'Invalid API key'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    async def test_murf(key: str) -> dict:
        """Test Murf API key by making a test request."""
        try:
            url = "https://api.murf.ai/v1/voices"
            headers = {"api-key": key}
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=10.0)
                if response.status_code == 200:
                    return {'status': 'valid', 'message': 'API key is valid'}
                return {'status': 'error', 'message': f'API error: {response.status_code} {response.text}'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    async def test_tavily(key: str) -> dict:
        """Test Tavily API key by making a test search."""
        try:
            url = "https://api.tavily.com/search"
            params = {"api_key": key, "query": "test", "search_depth": "basic", "include_answer": True}
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                if response.status_code == 200:
                    return {'status': 'valid', 'message': 'API key is valid'}
                return {'status': 'error', 'message': f'API error: {response.status_code} {response.text}'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    async def test_openweather(key: str) -> dict:
        """Test OpenWeather API key by making a test request."""
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather"
            params = {"q": "London,UK", "appid": key, "units": "metric"}
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                if response.status_code == 200:
                    return {'status': 'valid', 'message': 'API key is valid'}
                return {'status': 'error', 'message': f'API error: {response.status_code} {response.text}'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    async def test_news(key: str) -> dict:
        """Test NewsAPI key by making a test request."""
        try:
            url = f"https://newsapi.org/v2/top-headlines"
            params = {"apiKey": key, "country": "us", "pageSize": 1}
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                if response.status_code == 200:
                    return {'status': 'valid', 'message': 'API key is valid'}
                return {'status': 'error', 'message': f'API error: {response.status_code} {response.text}'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    # Test all services concurrently
    tasks = []
    
    # Test AssemblyAI
    assemblyai_key = Config.get_api_key('ASSEMBLYAI')
    if assemblyai_key:
        tasks.append((test_assemblyai(assemblyai_key), 'assemblyai'))
    else:
        results['assemblyai'] = {'status': 'missing', 'message': 'API key not configured'}
    
    # Test Gemini
    gemini_key = Config.get_api_key('GEMINI')
    if gemini_key:
        tasks.append((test_gemini(gemini_key), 'gemini'))
    else:
        results['gemini'] = {'status': 'missing', 'message': 'API key not configured'}
    
    # Test Murf
    murf_key = Config.get_api_key('MURF')
    if murf_key:
        tasks.append((test_murf(murf_key), 'murf'))
    else:
        results['murf'] = {'status': 'missing', 'message': 'API key not configured'}
    
    # Test special skills
    skill_tests = [
        ('TAVILY', test_tavily, 'tavily'),
        ('OPENWEATHER', test_openweather, 'openweather'),
        ('NEWS', test_news, 'news'),
    ]
    
    for service_key, test_func, service_name in skill_tests:
        key = Config.get_api_key(service_key)
        if key:
            tasks.append((test_func(key), service_name))
        else:
            results[service_name] = {'status': 'missing', 'message': 'API key not configured'}
    
    # Google Translate (no easy test endpoint, just check if key exists)
    translate_key = Config.get_api_key('GOOGLE_TRANSLATE')
    if translate_key:
        results['google_translate'] = {'status': 'valid', 'message': 'API key configured (not tested)'}
    else:
        results['google_translate'] = {'status': 'missing', 'message': 'API key not configured'}
    
    # Run all tests concurrently
    if tasks:
        test_coros, names = zip(*tasks)
        test_results = await asyncio.gather(*test_coros, return_exceptions=True)
        
        for result, name in zip(test_results, names):
            if isinstance(result, Exception):
                results[name] = {'status': 'error', 'message': str(result)}
            else:
                results[name] = result
    
    return results

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    services_status = {
        "stt": bool(Config.get_api_key('ASSEMBLYAI')),
        "tts": bool(Config.get_api_key('MURF')),
        "llm": bool(Config.get_api_key('GEMINI')),
        "skills": {
            "web_search": bool(Config.get_api_key('TAVILY')),
            "weather": bool(Config.get_api_key('OPENWEATHER')),
            "news": bool(Config.get_api_key('NEWS')),
            "translation": bool(Config.get_api_key('GOOGLE_TRANSLATE'))
        }
    }
    
    all_healthy = all([
        services_status["stt"],
        services_status["tts"], 
        services_status["llm"]
    ])
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": time.time(),
        "services": services_status
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
    
    # Clean up old audio files on startup
    try:
        await cleanup_old_audio_files(max_age_hours=24)
    except Exception as e:
        logger.error(f"Error during startup cleanup: {e}")
    
    # Schedule periodic cleanup every 6 hours
    asyncio.create_task(periodic_cleanup())


async def cleanup_audio_file(file_path: Path, delay_seconds: int = 300):
    """Clean up audio file after specified delay."""
    try:
        await asyncio.sleep(delay_seconds)
        if file_path.exists():
            os.remove(file_path)
            logger.info(f"Cleaned up audio file: {file_path.name}")
    except Exception as e:
        logger.error(f"Error cleaning up audio file {file_path}: {e}")


async def cleanup_old_audio_files(max_age_hours: int = 24):
    """Clean up audio files older than specified hours."""
    try:
        current_time = time.time()
        upload_dir = Config.UPLOAD_DIR
        
        if not upload_dir.exists():
            return
            
        cleaned_count = 0
        for file_path in upload_dir.glob("*"):
            if file_path.is_file():
                # Check if file is older than max_age_hours
                file_age = current_time - file_path.stat().st_mtime
                if file_age > (max_age_hours * 3600):  # Convert hours to seconds
                    try:
                        os.remove(file_path)
                        cleaned_count += 1
                        logger.info(f"Cleaned up old audio file: {file_path.name}")
                    except Exception as e:
                        logger.error(f"Error removing old file {file_path}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleanup completed: removed {cleaned_count} old audio files")
            
    except Exception as e:
        logger.error(f"Error during audio cleanup: {e}")


async def periodic_cleanup():
    """Run periodic cleanup every 6 hours."""
    while True:
        try:
            await asyncio.sleep(6 * 3600)  # 6 hours
            await cleanup_old_audio_files(max_age_hours=24)
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down AI Voice Agent")
    
    # Clean up any remaining audio files
    try:
        await cleanup_old_audio_files(max_age_hours=0)  # Clean all files on shutdown
    except Exception as e:
        logger.error(f"Error during shutdown cleanup: {e}")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG
    )
