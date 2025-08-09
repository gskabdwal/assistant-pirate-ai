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

# Request model for TTS endpoint
class TTSRequest(BaseModel):
    text: str
    voice_id: str = "en-US-natalie"  # Default voice ID

class EchoRequest(BaseModel):
    audio: UploadFile
    voice_id: Optional[str] = "en-US-natalie"  # Default voice ID

class LLMRequest(BaseModel):
    text: str

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
async def llm_query(request: LLMRequest):
    """
    Generate a response using Google's Gemini API for the given text input.
    """
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=500, 
            detail="Gemini API key not configured. Please set GEMINI_API_KEY in your environment variables."
        )
    
    try:
        # Initialize the Gemini model (using the latest available model)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Generate response
        response = model.generate_content(request.text)
        
        # Check if response was generated successfully
        if not response.text:
            raise HTTPException(status_code=500, detail="Failed to generate response from Gemini API")
        
        return {
            "query": request.text,
            "response": response.text,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error in llm_query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred while processing your request: {str(e)}")

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