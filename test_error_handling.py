import os
import pytest
import httpx
from unittest.mock import patch, MagicMock, AsyncMock
import shutil
from pathlib import Path

# We must import the app and other components from main *after* patching the environment.
# So we will import them inside the test functions or fixtures where needed.

# Test configuration
TEST_UPLOAD_DIR = Path(__file__).parent / "test_uploads"
TEST_AUDIO_FILE = TEST_UPLOAD_DIR / "test_audio.wav"

@pytest.fixture
async def async_client():
    """
    Provides an AsyncClient for the FastAPI app using ASGITransport.
    """
    from main import app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c

@pytest.fixture(autouse=True)
def setup_and_teardown():
    """
    Ensures the upload directory exists before each test and cleans it up after.
    """
    # Create test upload directory
    TEST_UPLOAD_DIR.mkdir(exist_ok=True)
    
    # Create a dummy audio file for testing
    create_dummy_audio_file()
    
    yield
    
    # Cleanup
    if TEST_UPLOAD_DIR.exists():
        shutil.rmtree(TEST_UPLOAD_DIR, ignore_errors=True)

def create_dummy_audio_file(filename: str = "test_audio.wav") -> Path:
    """Creates a dummy wav file for testing uploads."""
    file_path = TEST_UPLOAD_DIR / filename
    # A minimal valid WAV header
    wav_header = b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80\x3e\x00\x00\x00\xfa\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
    with open(file_path, 'wb') as f:
        f.write(wav_header)
    return file_path

@pytest.mark.anyio
async def test_404_not_found(async_client):
    """Test that a request to a non-existent endpoint returns 404."""
    response = await async_client.get("/non-existent-endpoint")
    assert response.status_code == 404
    json_response = response.json()
    assert "detail" in json_response
    assert "Not Found" in str(json_response["detail"])

@pytest.mark.anyio
@patch.dict(os.environ, {"ASSEMBLYAI_API_KEY": "", "GEMINI_API_KEY": "dummy", "MURF_API_KEY": "dummy"}, clear=True)
async def test_missing_assemblyai_key():
    """Test fallback response when AssemblyAI API key is missing."""
    from main import app
    
    # Create a test client
    transport = httpx.ASGITransport(app=app)
    
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Create a test audio file
        test_audio_path = create_dummy_audio_file()
        
        # Prepare the request
        with open(test_audio_path, "rb") as audio_file:
            files = {
                "file": ("test.wav", audio_file, "audio/wav")
            }
            data = {"voice_id": "test-voice"}
            
            # Make the request
            response = await client.post(
                "/agent/chat/test-session",
                files=files,
                data=data
            )
            
        # Check the response
        assert response.status_code == 500
        json_response = response.json()
        assert "detail" in json_response
        assert "Error processing chat request" in json_response["detail"]

@pytest.mark.anyio
@patch.dict(os.environ, {"ASSEMBLYAI_API_KEY": "dummy", "GEMINI_API_KEY": "", "MURF_API_KEY": "dummy"}, clear=True)
@patch('main.aai.Transcriber')
async def test_missing_gemini_key(mock_transcriber):
    """Test fallback response when Gemini API key is missing."""
    # Set up mock transcript
    mock_transcript = AsyncMock()
    mock_transcript.status = 'completed'
    mock_transcript.text = 'This is a test transcription.'
    
    # Set up mock transcriber
    mock_transcriber.return_value.transcribe.return_value = mock_transcript

    from main import app
    
    # Create a test client
    transport = httpx.ASGITransport(app=app)
    
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Create a test audio file
        test_audio_path = create_dummy_audio_file()
        
        # Prepare the request
        with open(test_audio_path, "rb") as audio_file:
            files = {
                "file": ("test.wav", audio_file, "audio/wav")
            }
            data = {"voice_id": "test-voice"}
            
            # Make the request
            response = await client.post(
                "/agent/chat/test-session",
                files=files,
                data=data
            )
            
        # Check the response
        assert response.status_code == 500
        json_response = response.json()
        assert "detail" in json_response
        assert "Error processing chat request" in json_response["detail"]

@pytest.mark.anyio
@patch.dict(os.environ, {"ASSEMBLYAI_API_KEY": "dummy", "GEMINI_API_KEY": "dummy", "MURF_API_KEY": ""}, clear=True)
@patch('main.aai.Transcriber')
@patch('main.genai.GenerativeModel')
async def test_missing_murf_key(mock_gemini, mock_transcriber):
    """Test fallback response when Murf API key is missing."""
    # Set up mock transcript
    mock_transcript = AsyncMock()
    mock_transcript.status = 'completed'
    mock_transcript.text = 'This is a test transcription.'
    mock_transcriber.return_value.transcribe.return_value = mock_transcript
    
    # Set up mock Gemini response
    mock_gemini_response = AsyncMock()
    mock_gemini_response.text = 'This is a test LLM response.'
    mock_gemini.return_value.start_chat.return_value.send_message.return_value = mock_gemini_response

    from main import app
    
    # Create a test client
    transport = httpx.ASGITransport(app=app)
    
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Create a test audio file
        test_audio_path = create_dummy_audio_file()
        
        # Prepare the request
        with open(test_audio_path, "rb") as audio_file:
            files = {
                "file": ("test.wav", audio_file, "audio/wav")
            }
            data = {"voice_id": "test-voice"}
            
            # Make the request
            response = await client.post(
                "/agent/chat/test-session",
                files=files,
                data=data
            )
            
        # Check the response
        assert response.status_code == 500
        json_response = response.json()
        assert "detail" in json_response
        assert "Error processing chat request" in json_response["detail"]

@pytest.mark.anyio
@patch.dict(os.environ, {"ASSEMBLYAI_API_KEY": "dummy", "GEMINI_API_KEY": "dummy", "MURF_API_KEY": "dummy"}, clear=True)
@patch('main.aai.Transcriber')
@patch('main.genai.GenerativeModel')
@patch('main.requests.post')
async def test_invalid_audio_file(mock_post, mock_gemini, mock_transcriber):
    """Test handling of invalid audio file upload."""
    # Set up mock transcript
    mock_transcript = AsyncMock()
    mock_transcript.status = 'completed'
    mock_transcript.text = 'This is a test transcription.'
    mock_transcriber.return_value.transcribe.return_value = mock_transcript
    
    # Set up mock Gemini response
    mock_gemini_response = AsyncMock()
    mock_gemini_response.text = 'This is a test LLM response.'
    mock_gemini.return_value.start_chat.return_value.send_message.return_value = mock_gemini_response
    
    # Set up mock Murf API response
    mock_response = MagicMock()
    mock_response.json.return_value = {"audio_url": "https://example.com/audio.mp3"}
    mock_post.return_value = mock_response

    from main import app
    
    # Create a test client
    transport = httpx.ASGITransport(app=app)
    
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Create an invalid audio file (empty)
        invalid_audio_path = TEST_UPLOAD_DIR / "invalid.wav"
        with open(invalid_audio_path, 'wb') as f:
            f.write(b'Not a valid WAV file')
        
        # Prepare the request
        with open(invalid_audio_path, "rb") as audio_file:
            files = {
                "file": ("invalid.wav", audio_file, "audio/wav")
            }
            data = {"voice_id": "test-voice"}
            
            # Make the request
            response = await client.post(
                "/agent/chat/test-session",
                files=files,
                data=data
            )
            
            # Check the response
            assert response.status_code == 500
            json_response = response.json()
            assert "detail" in json_response
            assert "Error processing chat request" in json_response["detail"]
