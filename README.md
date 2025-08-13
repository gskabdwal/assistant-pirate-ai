# 30 Days of Voice Agents


### Project Structure

```
├── main.py                  # FastAPI server
├── test_error_handling.py   # Test suite for error handling
├── requirements.txt         # Python dependencies
├── static/                 # Static files
│   ├── css/
│   │   └── styles.css      # CSS styles
│   └── js/
│       └── app.js          # Frontend JavaScript
└── templates/
    └── index.html          # Main HTML page
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

### Features

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