# WebSocket Implementation - Days 20-15

## Table of Contents
- [Day 20 - Murf WebSocket TTS Streaming](#day-20---murf-websocket-tts-streaming)
- [Day 19 - Streaming LLM Responses](#day-19---streaming-llm-responses)
- [Day 18 - Enhanced WebSocket State Management](#day-18---enhanced-websocket-state-management)
- [Day 17 - Real-time Speech Transcription](#day-17---real-time-speech-transcription)
- [Day 16 - WebSocket Audio Streaming](#day-16---websocket-audio-streaming)
- [Day 15 - Basic WebSocket Implementation](#day-15---basic-websocket-implementation)

---

## Day 20 - Murf WebSocket TTS Streaming

### Overview
Implemented real-time streaming from LLM responses directly to Murf's WebSocket API for immediate text-to-speech generation. This creates a complete streaming pipeline where LLM chunks are processed in real-time by Murf TTS, returning base64 encoded audio chunks.

### WebSocket Endpoint
- **URL**: `ws://localhost:8000/ws/llm-to-murf`
- **Protocol**: WebSocket (JSON messages)
- **LLM Service**: Google Gemini 1.5 Flash with streaming support
- **TTS Service**: Murf WebSocket API for real-time audio generation
- **Audio Format**: Base64 encoded audio chunks

### Implementation Details

#### Backend
- **Streaming Pipeline**: LLM response chunks streamed directly to Murf WebSocket API
- **WebSocket Handler**: Manages both LLM streaming and TTS WebSocket connections
- **Message Types**: Handles `llm_chunk`, `llm_complete`, `tts_chunk`, `tts_complete`, and `error` messages
- **Session Management**: Maintains conversation context and chat history
- **Static Context ID**: Uses consistent context_id to prevent Murf API context limit errors
- **Base64 Output**: Prints base64 encoded audio to console as per requirements

#### Frontend
- **WebSocket Client**: Connects to `/ws/llm-to-murf` endpoint
- **Dual Stream Handling**: Processes both LLM text chunks and TTS audio chunks
- **Real-time Display**: Shows LLM response as it streams
- **Audio Processing**: Handles base64 encoded audio chunks from Murf
- **Error Handling**: Comprehensive error handling for both LLM and TTS failures

### Message Protocol

#### Input Message Format
```json
{
  "text": "User's question or input",
  "session_id": "unique_session_identifier",
  "voice_id": "selected_voice_for_tts"
}
```

#### Output Message Types

**LLM Chunk Message:**
```json
{
  "type": "llm_chunk",
  "text": "Partial LLM response text",
  "is_complete": false
}
```

**LLM Complete Message:**
```json
{
  "type": "llm_complete",
  "text": "Complete LLM response text"
}
```

**TTS Chunk Message:**
```json
{
  "type": "tts_chunk",
  "data": {
    "audio": "base64_encoded_audio_chunk",
    "final": false
  },
  "is_final": false
}
```

**TTS Complete Message:**
```json
{
  "type": "tts_complete",
  "message": "TTS generation completed"
}
```

**Error Message:**
```json
{
  "type": "error",
  "message": "Error description"
}
```

### Key Features
- **Real-time LLM to TTS**: Direct streaming from LLM chunks to Murf WebSocket API
- **Base64 Audio Output**: Receives and prints base64 encoded audio to console
- **Static Context Management**: Uses consistent context_id to avoid API limits
- **Parallel Processing**: LLM and TTS processing happen simultaneously
- **Session Context**: Maintains conversation history across interactions
- **Error Recovery**: Comprehensive error handling for both services
- **Console Logging**: Base64 audio chunks printed to console for debugging

### Pipeline Flow
1. **User Input** → WebSocket message with text and session info
2. **LLM Streaming** → Google Gemini streams response chunks in real-time
3. **TTS Processing** → Each LLM chunk sent to Murf WebSocket API
4. **Audio Generation** → Murf returns base64 encoded audio chunks
5. **Console Output** → Base64 audio printed to console
6. **Client Response** → Both text and audio data sent to client

### Testing

#### Test Script
```bash
python test_day20_murf_websocket.py
```

#### Expected Console Output
```
Testing Day 20: LLM Streaming + Murf WebSocket TTS
============================================================
✅ Connected to LLM streaming WebSocket
📤 Sending test message: {'text': 'Tell me a short joke...', 'session_id': 'test-day20-session', 'voice_id': 'en-US-natalie'}
LLM streaming started
LLM chunk: Here's a quick AI joke for you...
LLM streaming completed. Full response: [complete joke]
Murf WebSocket TTS started
Received TTS audio chunk: 1234 chars
================================================================================
MURF TTS BASE64 AUDIO (first 100 chars):
UklGRjQAAABXQVZFZm10IBAAAAABAAEAK...
================================================================================
Murf WebSocket TTS completed
📊 Test completed. Received 6 messages
```

#### Testing Steps
1. Start the server: `python main.py`
2. Run the test script: `python test_day20_murf_websocket.py`
3. Observe LLM streaming chunks in real-time
4. Watch base64 audio output in console
5. Verify TTS completion message

---

## Day 19 - Streaming LLM Responses

### Overview
Implemented real-time streaming of LLM responses using Google Gemini's streaming API through WebSocket connections. This provides immediate user feedback as AI responses generate in real-time.

### WebSocket Endpoint
- **URL**: `ws://localhost:8000/ws/llm-stream`
- **Protocol**: WebSocket (JSON messages)
- **LLM Service**: Google Gemini 1.5 Flash with streaming support
- **Integration**: Seamless pipeline with audio recording, transcription, and TTS

### Implementation Details

#### Backend
- **Streaming LLM Service**: Integrated Google Gemini's streaming API
- **WebSocket Handler**: Processes incoming requests and streams response chunks
- **Message Types**: Handles `start`, `chunk`, `end`, and `error` message types
- **Session Management**: Maintains conversation context across streaming sessions
- **Error Handling**: Comprehensive error handling with graceful fallbacks

#### Frontend
- **WebSocket Client**: Connects to `/ws/llm-stream` endpoint
- **Real-time Display**: Updates UI with streaming text as it arrives
- **Message Handling**: Processes different streaming message types
- **Fallback System**: Automatic fallback to non-streaming LLM if WebSocket unavailable
- **TTS Integration**: Generates speech after streaming completes

### Message Protocol

#### Input Message Format
```json
{
  "text": "User's transcribed question",
  "session_id": "unique_session_identifier",
  "voice_id": "selected_voice_for_tts",
  "chat_history": []
}
```

#### Output Message Types

**Start Message:**
```json
{
  "type": "start",
  "message": "Starting to generate response..."
}
```

**Chunk Message:**
```json
{
  "type": "chunk",
  "content": "Partial AI response text"
}
```

**End Message:**
```json
{
  "type": "end",
  "final_response": "Complete AI response text",
  "message": "Response generation completed"
}
```

**Error Message:**
```json
{
  "type": "error",
  "error": "Error description"
}
```

### Key Features
- **Real-time Streaming**: AI responses appear as they generate
- **Session Context**: Maintains conversation history across interactions
- **Error Recovery**: Automatic fallback to non-streaming mode
- **Visual Feedback**: Live UI updates during streaming
- **TTS Integration**: Seamless conversion to speech after streaming
- **Pipeline Integration**: Works with existing audio → STT → LLM → TTS flow

### Pipeline Flow
1. **Audio Recording** → User records question
2. **Speech-to-Text** → AssemblyAI transcribes audio
3. **Streaming LLM** → Google Gemini streams response chunks
4. **Real-time Display** → UI updates with each chunk
5. **TTS Generation** → Murf AI converts final response to speech
6. **Audio Playback** → AI voice response plays automatically

### Testing

#### Expected Console Output
```
📤 Sending to LLM streaming endpoint: {text: "your question"}
🚀 LLM streaming started
📝 Streaming chunk: [AI response text]
📝 Streaming chunk: [more AI response text]
✅ LLM streaming completed
🔊 Generating TTS for response
```

#### Testing Steps
1. Start the server: `python main.py`
2. Open http://localhost:8000
3. Click "Start Recording" in AI Voice Agent section
4. Ask a question (e.g., "Tell me about artificial intelligence")
5. Click "Stop Recording"
6. Watch real-time streaming response in UI
7. Listen to AI voice response after streaming completes

---

## Day 18 - Enhanced WebSocket State Management

### Overview
Enhanced WebSocket connection handling with improved state management and error recovery.

### Key Improvements
- **Connection Lifecycle**: Added proper connection state management
- **Error Recovery**: Automatic reconnection logic
- **Resource Cleanup**: Ensured proper cleanup of WebSocket resources
- **State Synchronization**: Improved client-server state sync
- **Message Handling**: Enhanced message queuing and retry mechanism

### Implementation Details
- WebSocket connection state tracking
- Exponential backoff for reconnection attempts
- Heartbeat mechanism for stale connection detection
- Improved error handling and recovery flows
- Connection status indicators in the UI

### Benefits
- More reliable WebSocket connections
- Better handling of network interruptions
- Improved user feedback during connection issues
- Cleaner resource management

---

## Day 17 - Real-time Speech Transcription

### WebSocket Endpoint
- **URL**: `ws://localhost:8000/ws/transcribe-stream`
- **Protocol**: WebSocket
- **Audio Format**: 16kHz, 16-bit, mono PCM
- **Transcription Service**: AssemblyAI Universal-Streaming API

### Implementation Details

#### Backend
- Integrated AssemblyAI's streaming API
- Processes 16kHz mono PCM audio data
- Handles real-time transcription
- Manages WebSocket connection lifecycle
- Implements error handling and reconnection logic

#### Frontend
- Captures audio using Web Audio API
- Converts to required 16kHz PCM format
- Streams audio chunks to WebSocket
- Displays partial and final transcripts
- Provides visual feedback for transcription status

### Key Features
- Real-time speech-to-text with live partial results
- Color-coded transcript display (yellow for partial, green for final)
- Automatic audio format conversion
- Comprehensive error handling
- Console logging for debugging

---

## Day 16 - WebSocket Audio Streaming

### WebSocket Endpoint
- **URL**: `ws://localhost:8000/ws/audio-stream`
- **Protocol**: WebSocket (binary + text commands)
- **Audio Format**: WebM with Opus codec
- **Chunk Size**: 100ms intervals
- **Commands**:
  - `START_RECORDING` - Begin new recording session
  - `STOP_RECORDING` - Save accumulated audio chunks to file

### Implementation Details

#### Backend
- Added new WebSocket endpoint `/ws/audio-stream`
- Handles binary audio data streaming
- Saves audio to files in `uploads/` directory
- Generates unique session IDs for each recording

#### Frontend
- Uses MediaRecorder API with 100ms time slices
- Streams audio chunks in real-time
- Sends binary WebSocket messages
- Manages recording state

### File Output
Audio files are saved to the `uploads/` directory with the naming pattern:
```
streamed_audio_{unique_session_id}_{timestamp}.wav
```
Example: `streamed_audio_7d47a72f-8dc0-4163-a21a-914fb6e3de15_1755437664.wav`

---

## Day 17 - Real-time Speech Transcription

### WebSocket Endpoint
- **URL**: `ws://localhost:8000/ws/transcribe-stream`
- **Protocol**: WebSocket
- **Audio Format**: 16kHz, 16-bit, mono PCM
- **Transcription Service**: AssemblyAI Universal-Streaming API

### Implementation Details

#### Backend
- Integrated AssemblyAI's streaming API
- Processes 16kHz mono PCM audio data
- Handles real-time transcription
- Manages WebSocket connection lifecycle
- Implements error handling and reconnection logic

#### Frontend
- Captures audio using Web Audio API
- Converts to required 16kHz PCM format
- Streams audio chunks to WebSocket
- Displays partial and final transcripts
- Provides visual feedback for transcription status

### Key Features
- Real-time speech-to-text with live partial results
- Color-coded transcript display (yellow for partial, green for final)
- Automatic audio format conversion
- Comprehensive error handling
- Console logging for debugging

---

## Summary

The WebSocket implementation has evolved through multiple days:

- **Day 15**: Basic echo WebSocket for testing connectivity
- **Day 16**: Real-time audio streaming with binary data support
- **Day 17**: Live speech transcription using AssemblyAI streaming API
- **Day 18**: Enhanced state management and error recovery
- **Day 19**: Streaming LLM responses with Google Gemini integration
- **Day 20**: Murf WebSocket TTS streaming with base64 audio output

### Current WebSocket Endpoints

1. **`/ws/llm-to-murf`** - LLM streaming to Murf WebSocket TTS (Day 20)
2. **`/ws/llm-stream`** - Streaming LLM responses (Day 19)
3. **`/ws/transcribe-stream`** - Real-time transcription (Day 17)
4. **`/ws/audio-stream`** - Audio streaming (Day 16)
5. **`/ws`** - Basic echo server (Day 15)

### Complete Pipeline Integration

The Day 20 implementation provides the most advanced real-time voice agent pipeline:

**Audio Recording** → **Speech-to-Text** → **Streaming LLM** → **Streaming TTS** → **Base64 Audio Output**

All components work together seamlessly through WebSocket connections with real-time LLM-to-TTS streaming for optimal performance and immediate audio generation.
