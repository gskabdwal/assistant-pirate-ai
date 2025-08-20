# 30 Days of Voice Agents

## Overview

This project evolves over 30 days to build a fully functional AI Voice Agent. As of Day 19, we've implemented streaming LLM responses for real-time AI conversations. The latest updates include WebSocket-based streaming responses from Google Gemini with seamless integration into the voice pipeline.

### Project Structure

```
├── main.py                  # Application entry point
├── app/                     # Main application package
│   ├── __init__.py         # Package initialization
│   ├── main.py             # FastAPI application with routes
│   ├── config.py           # Configuration settings
│   ├── schemas.py          # Pydantic models for API schemas
│   └── services/           # Service layer for 3rd party integrations
│       ├── __init__.py     # Services package initialization
│       ├── stt_service.py  # Speech-to-Text service (AssemblyAI)
│       ├── tts_service.py  # Text-to-Speech service (Murf AI)
│       ├── llm_service.py  # LLM service (Google Gemini)
│       └── chat_service.py # Chat history management
├── requirements.txt         # Python dependencies
├── static/                 # Static files
│   ├── css/
│   │   └── styles.css      # CSS styles
│   └── js/
│       └── app.js          # Frontend JavaScript
├── templates/
│   └── index.html          # Main HTML page
└── uploads/                # Directory for uploaded files
```

### Setup Instructions

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables**

   Create a `.env` file in the project root with your API keys:
   ```
   MURF_API_KEY=your_murf_api_key_here
   ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

3. **Run the server**

   ```bash
   python main.py
   ```

4. **Run tests**

   ```bash
   python -m pytest test_error_handling.py -v
   ```

5. **Access the application**

   Open your browser and navigate to: http://localhost:8000

### Error Handling & Testing (Day 11) 🛡️

The application includes comprehensive error handling and a test suite to ensure reliability:

#### Server-Side Error Handling:
- **API Key Validation**: Graceful handling of missing or invalid API keys
- **Audio Processing**: Robust error handling for audio file operations
- **API Failures**: Automatic fallback to error responses when external services fail
- **Session Management**: Safe handling of session data and conversation history

#### Client-Side Error Handling:
- **User Feedback**: Clear error messages displayed in the UI
- **Fallback Audio**: Plays "I'm having trouble connecting right now" when errors occur
- **Recovery**: Automatic retry mechanisms where appropriate
- **Loading States**: Visual indicators during API calls

#### Error Cases Handled:
- Missing or invalid API keys (AssemblyAI, Gemini, Murf)
- Invalid or corrupted audio files
- Network timeouts and API rate limits
- Session management errors
- External API failures
- Audio processing and playback issues

#### Running Tests

To run the test suite:
```bash
python -m pytest test_error_handling.py -v
```

#### Test Coverage:
- API key validation
- Audio file validation
- Session management
- Error response formats
- Endpoint availability

### WebSocket Streaming Usage

#### Day 19 - LLM Response Streaming

**Testing the Streaming LLM Pipeline:**

1. **Start the server**:
   ```bash
   python main.py
   ```

2. **Open the application**: Navigate to http://localhost:8000

3. **Test streaming LLM responses**:
   - Click "Start Recording" in the AI Voice Agent section
   - Ask a question (e.g., "Tell me about artificial intelligence")
   - Click "Stop Recording"
   - Watch the real-time streaming response appear in the UI
   - Listen to the AI voice response after streaming completes

**Expected Console Output:**
```
📤 Sending to LLM streaming endpoint: {text: "your question"}
🚀 LLM streaming started
📝 Streaming chunk: [AI response text]
📝 Streaming chunk: [more AI response text]
✅ LLM streaming completed
🔊 Generating TTS for response
```

#### WebSocket Endpoints

- **`/ws/llm-stream`**: Streaming LLM responses (Day 19)
- **`/ws/audio-stream`**: Real-time audio streaming (Day 16)
- **`/ws/transcribe-stream`**: Real-time transcription (Day 17)

#### Day 16 - Audio Streaming

#### Testing the WebSocket Audio Streaming

1. **Start the server**:
   ```bash
   python main.py
   ```

2. **Open the application**: Navigate to http://localhost:8000

3. **Test audio streaming**:
   - Click "Start Recording" to begin streaming audio chunks via WebSocket
   - Speak into your microphone (audio streams in real-time)
   - Click "Stop Recording" to finish and save the audio file
   - Check the `uploads/` directory for saved files like `streamed_audio_{session_id}_{timestamp}.wav`

#### WebSocket Endpoint Details

**LLM Streaming (`/ws/llm-stream`):**
- **Protocol**: WebSocket (JSON messages)
- **Input**: `{text, session_id, voice_id, chat_history}`
- **Output**: Streaming message types:
  - `start` - Streaming begins
  - `chunk` - Response text chunks
  - `end` - Streaming complete with final response
  - `error` - Error messages

**Audio Streaming (`/ws/audio-stream`):**
- **Protocol**: WebSocket (binary + text commands)
- **Audio Format**: WebM with Opus codec
- **Chunk Size**: 100ms intervals
- **Commands**: 
  - `START_RECORDING` - Begin new recording session
  - `STOP_RECORDING` - Save accumulated audio chunks to file

#### File Output

Audio files are saved to the `uploads/` directory with the naming pattern:
```
streamed_audio_{unique_session_id}_{timestamp}.wav
```

Example: `streamed_audio_7d47a72f-8dc0-4163-a21a-914fb6e3de15_1755437664.wav`

### Features

#### Day 19 - Streaming LLM Responses 🚀

**Real-time AI Response Streaming:**
- **WebSocket Integration**: New `/ws/llm-stream` endpoint for streaming LLM responses in real-time
- **Google Gemini Streaming**: Integrated Google Gemini's streaming API for live AI responses
- **Seamless Pipeline**: Complete audio → transcription → streaming LLM → TTS pipeline
- **Real-time UI Updates**: Live display of streaming AI responses as they generate
- **Error Handling**: Comprehensive error handling for streaming failures with fallback to non-streaming
- **Session Management**: Maintains conversation context across streaming sessions

**Technical Implementation:**
- **Frontend**: WebSocket client handles streaming message types (start, chunk, end, error)
- **Backend**: Google Gemini streaming API yields response chunks asynchronously
- **UI Components**: Real-time text updates during streaming with final response display
- **Fallback System**: Automatic fallback to non-streaming LLM if WebSocket unavailable
- **TTS Integration**: Automatic TTS generation after streaming completes

**Key Features:**
- Real-time streaming of AI responses for immediate user feedback
- Maintains full conversation context and session management
- Seamless integration with existing voice pipeline (audio → STT → streaming LLM → TTS)
- Visual feedback with streaming text display and completion indicators
- Robust error handling and automatic fallback mechanisms

**Pipeline Flow:**
1. **Record Audio** → AssemblyAI Transcription
2. **Send to Streaming LLM** → Google Gemini streaming response
3. **Real-time Display** → Live text updates as AI responds
4. **Generate TTS** → Murf AI converts final response to speech
5. **Auto-playback** → AI voice response plays automatically

#### Day 18 - Enhanced Transcription UI & State Management 🎛️

**UI and State Management Improvements:**
- **Centered Layout**: Implemented a clean, centered design for better user experience
- **Responsive Container**: Added proper flexbox centering for the transcription interface
- **State Management**: Enhanced recording state handling for more reliable start/stop functionality
- **Resource Cleanup**: Improved cleanup of WebSocket connections and audio resources
- **UI Feedback**: Better visual feedback during different transcription states

**Technical Implementation:**
- **Flexbox Layout**: Used `justify-content: center` and `align-items: center` for perfect centering
- **State Cleanup**: Properly reset UI elements and states when stopping transcription
- **Error Handling**: Enhanced error states and recovery mechanisms
- **Code Organization**: Improved separation of concerns in the frontend JavaScript

**Key Benefits:**
- More polished and professional user interface
- Smoother user experience with proper state transitions
- More reliable cleanup of resources
- Better error handling and user feedback


#### Day 17 - Real-time Speech Transcription 🎙️

**AssemblyAI Streaming Transcription Implementation:**
- **WebSocket Endpoint**: New `/ws/transcribe-stream` endpoint for real-time audio transcription
- **Universal-Streaming API**: Integrated AssemblyAI's latest streaming API for live transcription
- **Real-time Processing**: Streams 16kHz mono PCM audio data for optimal transcription quality
- **Live Display**: Shows both partial and final transcripts in real-time
- **Event Loop Fix**: Resolved asyncio threading issues for stable WebSocket communication
- **Audio Format Optimization**: Implemented Web Audio API for proper PCM data streaming

**Technical Implementation:**
- **Frontend**: Web Audio API captures raw PCM audio data at 16kHz sample rate
- **Backend**: AssemblyAI Universal-Streaming client processes audio chunks in real-time
- **UI Components**: Separate display areas for partial (yellow) and final (green) transcripts
- **Error Handling**: Comprehensive error handling for WebSocket and transcription failures
- **Audio Processing**: Converts float32 audio to int16 PCM format required by AssemblyAI

**Key Features:**
- Real-time speech-to-text with live partial results
- Proper audio format handling (16kHz, 16-bit, mono PCM)
- Visual feedback with color-coded transcript display
- Console logging for debugging transcription events
- Seamless integration with existing Voice Agent functionality

#### Day 16 - WebSocket Audio Streaming 🎵

**Real-time Audio Streaming Implementation:**
- **WebSocket Endpoint**: New `/ws/audio-stream` endpoint for real-time audio data transmission
- **Client Streaming**: Modified recording logic to stream 100ms audio chunks via WebSocket instead of accumulating
- **File Saving**: Server receives binary audio data and saves to unique files in uploads/ directory
- **Session Management**: Each recording session gets a unique UUID for file identification
- **Audio Format**: Uses WebM with Opus codec for efficient streaming
- **Command Handling**: START_RECORDING and STOP_RECORDING commands for session control

**Technical Implementation:**
- **Frontend**: MediaRecorder with 100ms time slices streams audio chunks in real-time
- **Backend**: WebSocket handler accumulates chunks and saves to files like `streamed_audio_{session_id}_{timestamp}.wav`
- **No Processing**: Pure audio streaming without transcription, LLM, or TTS processing
- **File Management**: Automatic cleanup and unique naming with session IDs and timestamps

**Note**: This implementation intentionally breaks the existing UI to focus on the core WebSocket streaming functionality.

#### Day 15 - WebSocket Connection 🔌

**Basic WebSocket Implementation:**
- **WebSocket Endpoint**: Created `/ws` endpoint for real-time bidirectional communication
- **Echo Functionality**: Server echoes back any messages received from clients
- **Client Testing**: Tested with WebSocket clients like Postman for message exchange
- **Connection Management**: Proper WebSocket connection lifecycle handling (open, message, close, error)
- **Real-time Communication**: Foundation for streaming capabilities and real-time features

**Technical Implementation:**
- **FastAPI WebSocket**: Used FastAPI's built-in WebSocket support
- **Message Handling**: Text message reception and echo response
- **Error Handling**: Graceful handling of WebSocket disconnections and errors
- **Logging**: Connection events and message exchanges logged for debugging

**Note**: This was the foundational WebSocket implementation before advancing to audio streaming in Day 16.

#### Day 14 Refactoring Highlights

- **Modular Architecture**: Separated concerns into distinct modules (services, schemas, config)
- **Pydantic Models**: Added comprehensive request/response schemas for type safety
- **Service Layer**: Isolated 3rd party API integrations (STT, TTS, LLM) into dedicated services
- **Configuration Management**: Centralized configuration with proper validation
- **Comprehensive Logging**: Added structured logging throughout the application
- **Dependency Injection**: Used FastAPI's dependency system for better testability
- **Error Handling**: Improved error handling with proper HTTP status codes

#### Day 13 - Documentation Enhancements 📝
- **README Improvements**:
  - Clarified current scope and architecture with an Overview
  - Documented UI focus on AI Voice Agent and deprecation of Echo Bot/speech UI
  - Consolidated and updated browser compatibility notes
  - Linked feature history for quick navigation

#### Day 12 - UI Revamp: AI Voice Agent Only 🎛️
- **UI Changes**:
  - Removed Echo Bot and legacy browser speech-recognition sections from `templates/index.html`
  - Streamlined layout to highlight the AI Voice Agent flow and chat history
  - Clearer status messages and guidance on conversation flow
- **Notes**:
  - Echo Bot endpoints and references are deprecated at the UI level. The focus is the session-based AI Voice Agent.

#### Day 11 - Robust Error Handling 🛡️
- **Server Improvements**:
  - Added comprehensive try-except blocks in all API endpoints
  - Implemented consistent error response format
  - Added fallback error messages for all external service calls
  - Proper cleanup of temporary files even when errors occur

- **Client Improvements**:
  - Added error state handling in the UI
  - Implemented fallback audio response for TTS failures
  - Added user-friendly error messages
  - Improved loading states and disabled buttons during processing

- **Testing**:
  - Added test cases for error scenarios
  - Simulated API failures by removing API keys
  - Verified fallback behavior
  - Tested network failure scenarios

#### Day 10 - Chat History with Session Management 💬
- **New Endpoint**: Added `POST /agent/chat/{session_id}` for session-based conversations
- **Session Management**:
  - Unique session IDs generated for each conversation
  - Session ID stored in URL for persistence
  - In-memory chat history storage
- **Conversation Flow**:
  - Audio input → Speech-to-Text → Context-aware LLM response → Text-to-Speech
  - Maintains full conversation context within each session
- **Auto-Recording**:
  - Automatically starts recording after TTS playback completes
  - 1-second delay added for better user experience
- **UI Enhancements**:
  - Session ID visible in the URL
  - Chat history display in the UI
  - Visual distinction between user and assistant messages

#### Day 9 - Bug Fixes and Code Cleanup 🐛
- Added history feature to the UI
- Added session management to the backend
- Added backend api endpoint for history

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

The application requires a modern browser that supports:
- MediaRecorder API (for recording audio queries for the AI Voice Agent)

Notes:
- Web Speech API-based browser recognition UI has been deprecated as of Day 12.

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
Note: As of Day 10+, the preferred endpoint for conversations with session memory is `POST /agent/chat/{session_id}`. The `/llm/query` endpoint remains for historical reference and simple single-turn processing.

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

### Testing Error Scenarios (Day 11)

To test the error handling capabilities added in Day 11:

1. **Missing API Keys**:
   - Comment out any of the API keys in the `.env` file
   - The application will show appropriate error messages in the UI
   - A fallback audio message will play when TTS services are unavailable

2. **Invalid Audio Files**:
   - Try uploading a non-audio file (e.g., .txt, .jpg)
   - The application will detect the invalid format
   - A user-friendly error message will appear

3. **Network Issues**:
   - Test with a simulated slow network (using browser dev tools)
   - The application handles timeouts gracefully
   - Loading indicators are visible during processing

4. **API Rate Limits**:
   - Simulate rate limit responses from any of the APIs
   - The application shows appropriate error messages
   - Automatic retry logic is triggered where applicable

### Next Steps

In the upcoming days, I'll enhance this application with more advanced voice agent capabilities.