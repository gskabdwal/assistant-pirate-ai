# 30 Days of Voice Agents


### Project Structure

```
├── main.py               # FastAPI server
├── requirements.txt      # Python dependencies
├── static/              # Static files
│   ├── css/
│   │   └── styles.css   # CSS styles
│   └── js/
│       └── app.js       # Frontend JavaScript
└── templates/
    └── index.html       # Main HTML page
```

### Setup Instructions

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Run the server**

   ```bash
   python main.py
   ```

3. **Access the application**

   Open your browser and navigate to: http://localhost:8000

### Features

#### Day 9 - The Full Non-Streaming Pipeline ✨
- **Complete AI Voice Agent**: Full audio-to-audio conversation pipeline
- **Updated `/llm/query` endpoint**: Now accepts audio input instead of text
- **Full Pipeline Flow**: Audio → AssemblyAI Transcription → Gemini LLM → Murf TTS → Audio Response
- **Character Limit Handling**: Automatic truncation for Murf's 3000 character limit
- **Enhanced UI**: New "AI Voice Agent" section with consistent styling
- **Smart Button States**: Recording buttons disabled during processing to prevent multiple submissions
- **Voice Selection**: Choose from multiple AI voices for responses
- **Auto-playback**: AI response audio plays automatically when ready

#### Day 8
- Integrated Google Gemini API for Large Language Model (LLM) capabilities
- Added POST `/llm/query` endpoint for text-based AI responses (now updated for audio input)
- Enhanced server with Gemini 1.5 Flash model integration
- Added proper error handling and API key validation for LLM functionality

#### Day 7
- Enhanced Echo Bot with Murf TTS integration
- Improved UI with consistent audio player styling
- Added real-time status updates for recording and processing
- Fixed JavaScript errors and improved error handling
- Streamlined status message display

#### Day 6
- Added audio transcription using AssemblyAI
- Display transcription results in the UI
- Improved error handling for transcription process
- Added status messages for transcription feedback

#### Day 5
- Implemented audio file saving functionality
- Added audio playback controls
- Enhanced Echo Bot with file handling
- Added upload status indicators

#### Day 4
- Voice recording and playback with Echo Bot
- Real-time recording status updates
- Browser-based audio recording using MediaRecorder API

#### Day 3
- Built UI for TTS endpoint
- Added voice selection dropdown
- Added audio playback functionality
- Added status messages for TTS endpoint


#### Day 2
- Text-to-Speech endpoint using Murf's TTS API
- Secure API key storage using environment variables
- JSON response with URL to generated audio file

#### Day 1
- Basic web interface with start/stop buttons for voice recognition
- Speech-to-text functionality using the Web Speech API
- Display of transcribed text
- Simple response echo

### Browser Compatibility

The application requires a modern browser that supports the following APIs:
- Web Speech API (for speech recognition)
- MediaRecorder API (for Echo Bot)

Recommended browsers:
- Google Chrome
- Microsoft Edge
- Firefox
- Safari (recent versions)

### Using the TTS Endpoint

You can use the FastAPI Swagger UI to test the endpoint at http://localhost:8000/docs

#### POST /tts

Request body:
```json
{
  "text": "Hello, this is a test of the text to speech API",
  "voice_id": "en-US-marcus"
}
```

Response:
```json
{
  "audio_url": "https://url-to-generated-audio-file.mp3"
}
```

#### Parameters

- `text`: The text to convert to speech (required)
- `voice_id`: The voice ID to use (optional, defaults to "en-US-marcus")

### Using the AI Voice Agent Endpoint (Day 9)

The `/llm/query` endpoint now accepts audio input for the full non-streaming pipeline.

#### POST /llm/query

**Request**: FormData with audio file
- `file`: Audio file (WAV, MP3, etc.)
- `voice_id`: Voice ID for AI response (optional, defaults to "en-US-natalie")

**Response**:
```json
{
  "transcription": "What is artificial intelligence?",
  "llm_response": "Artificial intelligence (AI) is...",
  "audio_url": "/uploads/llm_response_uuid.mp3",
  "status": "success"
}
```

**Pipeline Flow**:
1. **Audio Input** → AssemblyAI Transcription
2. **Transcription** → Gemini LLM Processing  
3. **LLM Response** → Murf TTS Generation
4. **Audio Response** → Client Playback

### Using the Legacy LLM Text Endpoint (Day 8)

For text-only LLM queries, you can still use the original format via the web interface.

**Original Query Format**:
  "response": "Artificial intelligence (AI) is a branch of computer science that aims to create intelligent machines that can think and act like humans...",
  "status": "success"
}
```

#### Parameters

- `text`: The text query to send to the LLM (required)

### Environment Setup

Create a `.env` file in the project root with your API keys:
```
# Required for TTS functionality
MURF_API_KEY=your_murf_api_key_here

# Required for speech-to-text functionality
ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here

# Required for LLM functionality (Day 8)
GEMINI_API_KEY=your_gemini_api_key_here
```

**Note:** Make sure to keep your API keys secure and never commit them to version control.
- Get your Murf API key from [Murf.ai](https://www.murf.ai/)
- Get your AssemblyAI API key from [AssemblyAI](https://www.assemblyai.com/)
- Get your Gemini API key from [Google AI Studio](https://ai.google.dev/gemini-api/docs/quickstart)

### How to Use the AI Voice Agent (Day 9)

1. **Navigate to the AI Voice Agent section** on the main page
2. **Select your preferred AI voice** from the dropdown (Rohan, Alia, Priya, or Natalie)
3. **Click "Start Recording"** and ask your question
4. **Click "Stop Recording"** when finished (buttons will be disabled during processing)
5. **Wait for the AI response** - you'll see:
   - Your transcribed question
   - The AI's text response
   - The AI's voice response (plays automatically)

**Processing Flow**:
- 🎤 **Record** → 📝 **Transcribe** → 🤖 **AI Think** → 🔊 **AI Speak**

### Browser Compatibility

The application requires a modern browser that supports the following APIs:
- Web Speech API (for speech recognition)
- MediaRecorder API (for Echo Bot)

Recommended browsers:
- Google Chrome
- Microsoft Edge
- Firefox
- Safari (recent versions)

### Next Steps

In the upcoming days, I'll enhance this application with more advanced voice agent capabilities.