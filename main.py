from fastapi import FastAPI, Request, HTTPException, UploadFile, File, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import os
import requests
import shutil
from pathlib import Path
from typing import Dict, Any
from pydantic import BaseModel
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

app = FastAPI(title="Voice Agent")

# Get Murf API key from environment variables
MURF_API_KEY = os.getenv("MURF_API_KEY")
if not MURF_API_KEY:
    print("Warning: MURF_API_KEY not found in environment variables. TTS functionality will not work.")

# Murf API endpoint
MURF_API_URL = "https://api.murf.ai/v1/speech/generate"

# Request model for TTS endpoint
class TTSRequest(BaseModel):
    text: str
    voice_id: str = "en-US-natalie"  # Default voice ID

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
async def text_to_speech(tts_request: TTSRequest):
    """Convert text to speech using Murf's TTS API"""
    if not MURF_API_KEY:
        raise HTTPException(status_code=500, detail="Murf API key not configured")
    
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

@app.post("/upload-audio/")
async def upload_audio(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Handle audio file uploads"""
    try:
        # Create a safe filename
        file_extension = os.path.splitext(file.filename)[1]
        safe_filename = f"audio_{int(time.time())}{file_extension}"
        file_path = UPLOAD_DIR / safe_filename
        
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Get file info
        file_size = os.path.getsize(file_path)
        
        return {
            "filename": safe_filename,
            "content_type": file.content_type,
            "size": file_size,
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )
    finally:
        await file.close()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)