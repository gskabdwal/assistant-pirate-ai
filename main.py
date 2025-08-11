from fastapi import FastAPI, Request, HTTPException, UploadFile, File, status, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import os
import requests
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
import time
import assemblyai as aai
import tempfile
import uuid
import google.generativeai as genai

# Load environment variables
load_dotenv()

app = FastAPI(title="Voice Agent")

# Get API keys from environment variables
MURF_API_KEY = os.getenv("MURF_API_KEY")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not MURF_API_KEY:
    print("Warning: MURF_API_KEY not found in environment variables. TTS functionality will not work.")

if not ASSEMBLYAI_API_KEY:
    print("Warning: ASSEMBLYAI_API_KEY not found in environment variables. Transcription will not work.")
else:
    # Configure AssemblyAI
    aai.settings.api_key = ASSEMBLYAI_API_KEY

if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not found in environment variables. LLM functionality will not work.")
else:
    # Configure Gemini AI
    genai.configure(api_key=GEMINI_API_KEY)

# API endpoints
MURF_API_URL = "https://api.murf.ai/v1/speech/generate"
MURF_VOICES_URL = "https://api.murf.ai/v1/studio/voice-ai/voice-list"

# In-memory chat history storage (session_id -> list of messages)
chat_history = {}

# Request model for TTS endpoint
class TTSRequest(BaseModel):
    text: str

class EchoRequest(BaseModel):
    audio: UploadFile
    voice_id: Optional[str] = "en-US-natalie"

class LLMRequest(BaseModel):
    text: str

class LLMAudioRequest(BaseModel):
    audio: UploadFile
    voice_id: Optional[str] = "en-US-natalie"

# Set up directories
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Mount static files directory
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Set up templates
templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
os.makedirs(templates_dir, exist_ok=True)
templates = Jinja2Templates(directory=templates_dir)

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/tts")
async def text_to_speech(request: Request):
    """Convert text to speech using Murf's TTS API"""
    # Try to parse the request body as JSON first
    try:
        data = await request.json()
        print(f"Parsed JSON data: {data}")
        
        # Manually create TTSRequest from the parsed data
        tts_request = TTSRequest(
            text=data.get('text', ''),
            voice_id=data.get('voice_id', 'en-US-natalie')
        )
        print(f"Created TTSRequest: {tts_request}")
        
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        raise HTTPException(
            status_code=422,
            detail=f"Invalid request format: {str(e)}"
        )
    
    if not MURF_API_KEY:
        error_msg = "Murf API key not configured"
        print(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    
    # Prepare the request to Murf API
    headers = {
        "api-key": f"{MURF_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": tts_request.text,
        "voiceId": tts_request.voice_id,
        "format": "MP3",
        "modelVersion": "GEN2"
    }
    
    print(f"Sending to Murf API: {payload}")
    
    try:
        # Call Murf API
        response = requests.post(MURF_API_URL, json=payload, headers=headers)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # Extract audio URL from response
        result = response.json()
        if "audioFile" in result:
            return {"audio_url": result["audioFile"]}
        else:
            raise HTTPException(status_code=500, detail="No audio URL in response")
            
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error calling Murf API: {str(e)}")

@app.post("/transcribe/file")
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe audio file using AssemblyAI"""
    print(f"Received file for transcription: {file.filename}, size: {file.size}")
    
    if not ASSEMBLYAI_API_KEY:
        error_msg = "AssemblyAI API key not configured"
        print(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )
    
    try:
        # Read the audio file content
        audio_data = await file.read()
        print(f"Read {len(audio_data)} bytes of audio data")
        
        if not audio_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty audio file received"
            )
        
        # Save the audio data to a temporary file for debugging
        temp_file = os.path.join(UPLOAD_DIR, f"debug_{int(time.time())}_{file.filename}")
        with open(temp_file, 'wb') as f:
            f.write(audio_data)
        print(f"Saved audio to {temp_file}")
        
        # Create a transcriber
        transcriber = aai.Transcriber()
        
        # Print available models for debugging
        print("Available models:", dir(aai.TranscriptionConfig))
        
        # Transcribe the audio data with more verbose logging
        print("Starting transcription...")
        config = aai.TranscriptionConfig(
            speaker_labels=True,
            language_detection=True,
            punctuate=True,
            format_text=True
        )
        print("Using config:", config)
        
        transcript = transcriber.transcribe(
            data=audio_data,
            config=config
        )
        print("Transcription completed. Status:", transcript.status)
        
        if transcript.error:
            error_msg = f"Transcription error: {transcript.error}"
            print(error_msg)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
            
        # Return the transcription text
        if not transcript.text or not transcript.text.strip():
            print("Warning: Empty transcription text received")
            return {"text": "", "status": "success", "warning": "No speech detected in audio"}
            
        return {"text": transcript.text, "status": "success"}
        
        # Return the transcription text
        return {
            "status": "success",
            "transcript": transcript.text,
            "speakers": transcript.utterances if hasattr(transcript, 'utterances') else None
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during transcription: {str(e)}"
        )
    finally:
        await file.close()

@app.post("/upload-audio/")
async def upload_audio(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Handle audio file uploads (kept for backward compatibility)"""
    try:
        # Just read the file content without saving
        content = await file.read()
        return {
            "message": "File processed successfully (not saved to disk)",
            "file_size": len(content)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file: {str(e)}"
        )
    finally:
        await file.close()

@app.post("/tts/echo")
async def echo_tts(
    file: UploadFile = File(...),
    voice_id: str = Form("en-US-natalie")  # Default voice ID
):
    """
    Endpoint that accepts audio, transcribes it using the existing endpoint,
    and returns Murf TTS audio using the existing TTS endpoint.
    """
    try:
        # First, transcribe the audio using the existing endpoint
        transcription_response = await transcribe_audio(file)
        print(f"Transcription response: {transcription_response}")
        
        if not transcription_response or "text" not in transcription_response:
            raise HTTPException(status_code=400, detail="Could not transcribe audio: No text in response")
        
        transcription = transcription_response["text"].strip()
        print(f"Transcription: '{transcription}'")
        
        if not transcription:
            raise HTTPException(status_code=400, detail="Transcription returned empty text. Please try speaking more clearly.")
        
        # Now generate TTS directly calling the Murf API
        print(f"Generating TTS for: '{transcription[:50]}...'")
        
        if not MURF_API_KEY:
            error_msg = "Murf API key not configured"
            print(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Prepare the request to Murf API
        headers = {
            "api-key": MURF_API_KEY,
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": transcription,
            "voiceId": voice_id,
            "format": "MP3",
            "modelVersion": "GEN2"
        }
        
        print(f"Sending to Murf API: {payload}")
        
        try:
            # Call Murf API directly
            response = requests.post(MURF_API_URL, json=payload, headers=headers)
            response.raise_for_status()  # Raise exception for HTTP errors
            
            # Extract audio URL from response
            result = response.json()
            if "audioFile" in result:
                tts_response = {"audio_url": result["audioFile"]}
                print(f"Successfully generated TTS audio: {tts_response}")
            else:
                error_msg = "No audio URL in Murf API response"
                print(error_msg)
                raise HTTPException(status_code=500, detail=error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Error calling Murf API: {str(e)}"
            print(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        if not tts_response or "audio_url" not in tts_response:
            raise HTTPException(status_code=500, detail="TTS generation failed")
        
        # Include the transcription in the response
        return {
            "audio_url": tts_response["audio_url"],
            "transcription": {
                "text": transcription,
                "status": "success"
            }
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"Error in echo_tts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.post("/llm/query")
async def llm_query(
    file: UploadFile = File(...),
    voice_id: str = Form("en-US-natalie")
):
    """
    Full non-streaming pipeline: Accept audio, transcribe, send to LLM, generate TTS response.
    """
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=500, 
            detail="Gemini API key not configured. Please set GEMINI_API_KEY in your environment variables."
        )
    
    if not ASSEMBLYAI_API_KEY:
        raise HTTPException(
            status_code=500, 
            detail="AssemblyAI API key not configured. Please set ASSEMBLYAI_API_KEY in your environment variables."
        )
    
    if not MURF_API_KEY:
        raise HTTPException(
            status_code=500, 
            detail="Murf API key not configured. Please set MURF_API_KEY in your environment variables."
        )
    
    try:
        # Step 1: Save the uploaded audio file
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'wav'
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = UPLOAD_DIR / unique_filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"Audio file saved: {file_path}")
        
        # Step 2: Transcribe audio using AssemblyAI
        print("Starting transcription...")
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(str(file_path))
        
        if transcript.status == aai.TranscriptStatus.error:
            raise HTTPException(status_code=500, detail=f"Transcription failed: {transcript.error}")
        
        transcribed_text = transcript.text
        print(f"Transcription completed: {transcribed_text}")
        
        # Step 3: Send transcribed text to LLM (Gemini)
        print("Generating LLM response...")
        model = genai.GenerativeModel('gemini-1.5-flash')
        llm_response = model.generate_content("Generate a response to the following text in less than 2950 characters: " + transcribed_text)
        
        if not llm_response.text:
            raise HTTPException(status_code=500, detail="Failed to generate response from Gemini API")
        
        response_text = llm_response.text
        print(f"LLM response generated: {response_text[:100]}...")
        
        # Step 4: Handle Murf's 3000 character limit
        if len(response_text) > 3000:
            print(f"Response too long ({len(response_text)} chars), truncating to 3000 chars")
            response_text = response_text[:2997] + "..."
        
        # Step 5: Generate TTS audio using Murf
        print("Generating TTS audio...")
        murf_payload = {
            "voiceId": voice_id,
            "style": "Conversational",
            "text": response_text,
            "rate": 0,
            "pitch": 0,
            "sampleRate": 48000,
            "format": "MP3",
            "channelType": "MONO",
            "pronunciationDictionary": {},
            "encodeAsBase64": False,
            "variation": 1,
            "audioDuration": 0,
            "modelVersion": "GEN2"
        }
        
        murf_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "api-key": MURF_API_KEY
        }
        
        murf_response = requests.post(MURF_API_URL, json=murf_payload, headers=murf_headers)
        
        if not murf_response.ok:
            print(f"Murf API error: {murf_response.status_code} - {murf_response.text}")
            raise HTTPException(status_code=500, detail=f"TTS generation failed: {murf_response.text}")
        
        murf_data = murf_response.json()
        
        if not murf_data.get("audioFile"):
            raise HTTPException(status_code=500, detail="No audio file received from Murf API")
        
        # Step 6: Save the TTS audio file
        tts_filename = f"llm_response_{uuid.uuid4()}.mp3"
        tts_file_path = UPLOAD_DIR / tts_filename
        
        # Download and save the audio file
        audio_response = requests.get(murf_data["audioFile"])
        if audio_response.ok:
            with open(tts_file_path, "wb") as audio_file:
                audio_file.write(audio_response.content)
            print(f"TTS audio saved: {tts_file_path}")
        else:
            raise HTTPException(status_code=500, detail="Failed to download TTS audio file")
        
        # Step 7: Clean up the original audio file
        try:
            os.remove(file_path)
            print(f"Cleaned up original audio file: {file_path}")
        except Exception as cleanup_error:
            print(f"Warning: Could not clean up file {file_path}: {cleanup_error}")
        
        # Step 8: Return the response
        return {
            "transcription": transcribed_text,
            "llm_response": response_text,
            "audio_url": f"/uploads/{tts_filename}",
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error in llm_query: {str(e)}")
        # Clean up files in case of error
        try:
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"An error occurred while processing your request: {str(e)}")

@app.post("/agent/chat/{session_id}")
async def agent_chat(
    session_id: str,
    file: UploadFile = File(...),
    voice_id: str = Form("en-US-natalie")
):
    """
    Chat endpoint with session-based history: Accept audio, transcribe, maintain chat history, 
    send to LLM with context, generate TTS response.
    """
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=500, 
            detail="Gemini API key not configured. Please set GEMINI_API_KEY in your environment variables."
        )
    
    if not ASSEMBLYAI_API_KEY:
        raise HTTPException(
            status_code=500, 
            detail="AssemblyAI API key not configured. Please set ASSEMBLYAI_API_KEY in your environment variables."
        )
    
    if not MURF_API_KEY:
        raise HTTPException(
            status_code=500, 
            detail="Murf API key not configured. Please set MURF_API_KEY in your environment variables."
        )
    
    try:
        # Step 1: Save the uploaded audio file
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'wav'
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = UPLOAD_DIR / unique_filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"Audio file saved: {file_path}")
        
        # Step 2: Transcribe audio using AssemblyAI
        print("Starting transcription...")
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(str(file_path))
        
        if transcript.status == aai.TranscriptStatus.error:
            raise HTTPException(status_code=500, detail=f"Transcription failed: {transcript.error}")
        
        transcribed_text = transcript.text
        print(f"Transcription completed: {transcribed_text}")
        
        # Step 3: Get or initialize chat history for this session
        if session_id not in chat_history:
            chat_history[session_id] = []
        
        # Add user message to chat history
        chat_history[session_id].append({
            "role": "user",
            "content": transcribed_text,
            "timestamp": time.time()
        })
        
        # Step 4: Prepare conversation context for LLM
        conversation_context = "You are a helpful AI assistant. Please respond conversationally and keep your responses under 2950 characters.\n\n"
        conversation_context += "Previous conversation:\n"
        
        # Include recent chat history (last 10 messages to avoid token limits)
        recent_messages = chat_history[session_id][-10:]
        for msg in recent_messages[:-1]:  # Exclude the current message
            role = "User" if msg["role"] == "user" else "Assistant"
            conversation_context += f"{role}: {msg['content']}\n"
        
        conversation_context += f"\nUser: {transcribed_text}\nAssistant:"
        
        # Step 5: Send to LLM (Gemini) with conversation context
        print("Generating LLM response with chat history...")
        model = genai.GenerativeModel('gemini-1.5-flash')
        llm_response = model.generate_content(conversation_context)
        
        if not llm_response.text:
            raise HTTPException(status_code=500, detail="Failed to generate response from Gemini API")
        
        response_text = llm_response.text
        print(f"LLM response generated: {response_text[:100]}...")
        
        # Step 6: Add assistant response to chat history
        chat_history[session_id].append({
            "role": "assistant",
            "content": response_text,
            "timestamp": time.time()
        })
        
        # Step 7: Handle Murf's 3000 character limit
        tts_text = response_text
        if len(tts_text) > 3000:
            print(f"Response too long ({len(tts_text)} chars), truncating to 3000 chars")
            tts_text = tts_text[:2997] + "..."
        
        # Step 8: Generate TTS audio using Murf
        print("Generating TTS audio...")
        murf_payload = {
            "voiceId": voice_id,
            "style": "Conversational",
            "text": tts_text,
            "rate": 0,
            "pitch": 0,
            "sampleRate": 48000,
            "format": "MP3",
            "channelType": "MONO",
            "pronunciationDictionary": {},
            "encodeAsBase64": False,
            "variation": 1,
            "audioDuration": 0,
            "modelVersion": "GEN2"
        }
        
        murf_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "api-key": MURF_API_KEY
        }
        
        murf_response = requests.post(MURF_API_URL, json=murf_payload, headers=murf_headers)
        
        if not murf_response.ok:
            print(f"Murf API error: {murf_response.status_code} - {murf_response.text}")
            raise HTTPException(status_code=500, detail=f"TTS generation failed: {murf_response.text}")
        
        murf_data = murf_response.json()
        
        if not murf_data.get("audioFile"):
            raise HTTPException(status_code=500, detail="No audio file received from Murf API")
        
        # Step 9: Save the TTS audio file
        tts_filename = f"chat_response_{session_id}_{uuid.uuid4()}.mp3"
        tts_file_path = UPLOAD_DIR / tts_filename
        
        # Download and save the audio file
        audio_response = requests.get(murf_data["audioFile"])
        if audio_response.ok:
            with open(tts_file_path, "wb") as audio_file:
                audio_file.write(audio_response.content)
            print(f"TTS audio saved: {tts_file_path}")
        else:
            raise HTTPException(status_code=500, detail="Failed to download TTS audio file")
        
        # Step 10: Clean up the original audio file
        try:
            os.remove(file_path)
            print(f"Cleaned up original audio file: {file_path}")
        except Exception as cleanup_error:
            print(f"Warning: Could not clean up file {file_path}: {cleanup_error}")
        
        # Step 11: Return the response with chat history info
        # Include a trimmed recent history (last 10 messages) for UI rendering
        recent_history = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in chat_history[session_id][-10:]
        ]
        return {
            "session_id": session_id,
            "transcription": transcribed_text,
            "llm_response": response_text,
            "audio_url": f"/uploads/{tts_filename}",
            "chat_history_length": len(chat_history[session_id]),
            "recent_messages": recent_history,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error in agent_chat: {str(e)}")
        # Clean up files in case of error
        try:
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
        raise HTTPException(status_code=500, detail="Error processing chat request")

# Make sure uploads directory is served
@app.get("/uploads/{filename}")
async def get_uploaded_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)