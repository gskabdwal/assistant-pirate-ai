// Global variables
let sessionId;
let isAutoRecordingEnabled = false;
let llmMediaRecorder;
let llmAudioChunks = [];
let audioWebSocket;
let llmWebSocket;
let isStreaming = false;
let isLLMStreaming = false;
let chatService = null; // Initialize chat service

// Mobile-specific variables
let isMobile = false;
let mobileAudioContext = null;
let mobileWebSocketRetryCount = 0;
let maxMobileRetries = 3;

// Day 27: API Configuration variables
let apiConfigSidebar = null;
let apiKeyInputs = {};
let apiStatusIndicators = {};

// Session management
function generateSessionId() {
    return 'session_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
}

// Clear current session API keys
async function clearSessionKeys() {
    try {
        const response = await fetch(`/api/config/session/${sessionId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showNotification('Session API keys cleared', 'success');
            // Clear the input fields
            Object.values(apiKeyInputs).forEach(input => {
                if (input) {
                    input.value = '';
                    input.dataset.hadValue = 'false';
                }
            });
            // Reload status
            await loadAPIStatus();
        } else {
            throw new Error('Failed to clear session keys');
        }
    } catch (error) {
        console.error('Error clearing session keys:', error);
        showNotification('Error clearing session keys', 'error');
    }
}

// Streaming transcription variables
let transcribeWebSocket;
let streamMediaRecorder;
let isTranscribing = false;

// Day 21: Base64 audio streaming variables
let base64AudioWebSocket;
let base64AudioChunks = [];
let isBase64Streaming = false;

// Day 22: Streaming Audio Playback Variables (Murf-optimized)
let streamingAudioWebSocket = null;
let audioContext = null;
let audioChunks = []; // Store raw Float32 audio chunks
let isStreamingAudio = false;
let playheadTime = 0;
let totalPlaybackTime = 0;
let chunkCount = 0;
let isFirstChunk = true;
let isPlaying = false;
let wavHeaderSet = true;
let chunksReceived = 0;

// Active DOM Elements (Complete Voice Agent + API Config only)
// Legacy DOM elements removed - only keeping active Complete Voice Agent elements
let chunksReceivedDisplay;
let audioProgressDisplay;
let playbackTimeDisplay;
let audioCanvas;
let audioCanvasContext;
let visualizerBars = [];

// LLM Recording DOM Elements
let llmStartBtn = null;
let llmStopBtn = null;
let llmStatus = null;
let llmResponseText = null;
let llmResponseAudio = null;
let llmVoiceSelect = null;

// Streaming Transcription DOM Elements
let startStreamRecordingBtn = null;
let stopStreamRecordingBtn = null;
let streamStatus = null;
let partialTranscript = null;
let finalTranscript = null;

// Base64 Audio Streaming DOM Elements
let startBase64StreamBtn = null;
let base64Status = null;
let base64ChunksDisplay = null;

// Day 22 Streaming Audio DOM Elements
let startStreamingAudioBtn = null;
let stopStreamingAudioBtn = null;
let streamingAudioStatus = null;
let streamingChunksDisplay = null;
let streamingPlaybackTime = null;

// Legacy LLM Recording DOM Elements (for compatibility)
let startLLMRecordingBtn = null;
let stopLLMRecordingBtn = null;
let llmChatHistory = null;
let llmTranscriptionText = null;
let llmStreamingText = null;
let llmQuestionAudio = null;

// Complete Voice Agent WebSocket
let completeVoiceWs = null;

// Session management functions
function getOrCreateSessionId() {
    const urlParams = new URLSearchParams(window.location.search);
    let sessionId = urlParams.get('session_id');
    
    if (!sessionId) {
        sessionId = generateSessionId();
        const newUrl = new URL(window.location);
        newUrl.searchParams.set('session_id', sessionId);
        window.history.replaceState({}, '', newUrl);
    }
    
    return sessionId;
}

// WebSocket connection functions
function connectAudioWebSocket() {
    try {
        // Close existing connection if any
        if (audioWebSocket) {
            try {
                if (audioWebSocket.readyState === WebSocket.OPEN) {
                    audioWebSocket.close(1000, 'Reconnecting...');
                }
            } catch (e) {
                console.warn('Error closing existing WebSocket:', e);
            }
            audioWebSocket = null;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/audio-stream`;
        
        console.log('Connecting to WebSocket:', wsUrl);
        audioWebSocket = new WebSocket(wsUrl);
        
        audioWebSocket.onopen = () => {
            console.log('Audio WebSocket connected');
            if (llmStatus) {
                llmStatus.textContent = 'WebSocket connected - Ready to stream';
            }
            // Re-enable buttons after successful connection
            setLLMButtonStates(false, true);
        };
        
        audioWebSocket.onmessage = (event) => {
            console.log('WebSocket message:', event.data);
            if (llmStatus && typeof event.data === 'string') {
                llmStatus.textContent = event.data;
            }
        };
        
        audioWebSocket.onclose = (event) => {
            console.log(`Audio WebSocket disconnected. Code: ${event.code}, Reason: ${event.reason}`);
            if (llmStatus) {
                llmStatus.textContent = 'Disconnected from server';
            }
            isStreaming = false;
            
            // Attempt to reconnect if this wasn't an intentional close
            if (event.code !== 1000) {
                console.log('Attempting to reconnect in 2 seconds...');
                setTimeout(() => {
                    console.log('Reconnecting WebSocket...');
                    connectAudioWebSocket();
                }, 2000);
            }
        };
        
        audioWebSocket.onerror = (error) => {
            console.error('WebSocket error:', error);
            if (llmStatus) {
                llmStatus.textContent = 'Connection error';
            }
            isStreaming = false;
        };
    } catch (error) {
        console.error('Error in connectAudioWebSocket:', error);
        if (llmStatus) {
            llmStatus.textContent = 'Connection failed';
        }
        isStreaming = false;
        
        // Attempt to reconnect after delay
        setTimeout(() => {
            console.log('Retrying WebSocket connection...');
            connectAudioWebSocket();
        }, 3000);
    }
}

// Streaming Transcription Functions
function connectTranscriptionWebSocket() {
    const sessionId = getOrCreateSessionId();
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/transcribe-stream?session_id=${sessionId}`;
    
    transcribeWebSocket = new WebSocket(wsUrl);
    
    transcribeWebSocket.onopen = () => {
        console.log('Transcription WebSocket connected');
        if (streamStatus) {
            streamStatus.textContent = 'Connected - Ready for real-time transcription';
        }
    };
    
    // Add CSS for the transcription UI if not already added
    if (!document.getElementById('transcription-styles')) {
        const style = document.createElement('style');
        style.id = 'transcription-styles';
        style.textContent = `
            #transcription-container {
                margin: 20px 0;
                padding: 15px;
                border: 1px solid #ddd;
                border-radius: 8px;
                background-color: #f9f9f9;
            }
            #final-transcript {
                min-height: 60px;
                padding: 10px;
                margin-bottom: 10px;
                background-color: #e8f5e9;
                border-radius: 4px;
                white-space: pre-wrap;
                transition: background-color 0.5s ease;
            }
            #final-transcript.turn-end {
                background-color: #c8e6c9;
                transition: background-color 1s ease;
            }
            #partial-transcript {
                min-height: 20px;
                padding: 10px;
                color: #666;
                font-style: italic;
                transition: all 0.3s ease;
            }
            #partial-transcript.active-transcription {
                background-color: #fffde7;
            }
            #stream-status {
                margin: 10px 0;
                padding: 5px;
                font-weight: bold;
                transition: all 0.3s ease;
            }
            #stream-status.turn-detected {
                color: #2e7d32;
                font-weight: bold;
            }
            #stream-status.error {
                color: #c62828;
            }
        `;
        document.head.appendChild(style);
    }

    transcribeWebSocket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log('Transcription message:', data);
            
            if (data.type === 'turn_transcript') {
                if (data.end_of_turn) {
                    // End of turn - show final transcript with visual feedback
                    if (finalTranscript) {
                        finalTranscript.textContent = data.text || 'No speech detected';
                        // Add visual feedback for end of turn
                        finalTranscript.classList.add('turn-end');
                        setTimeout(() => finalTranscript.classList.remove('turn-end'), 1000);
                    }
                    if (partialTranscript) {
                        partialTranscript.textContent = 'Listening...';
                    }
                    // Scroll to show the latest transcription
                    finalTranscript.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                } else {
                    // Partial transcript - show in partial display with visual feedback
                    if (partialTranscript) {
                        partialTranscript.textContent = data.text || 'Listening...';
                        // Add visual feedback for active transcription
                        partialTranscript.classList.add('active-transcription');
                        setTimeout(() => partialTranscript.classList.remove('active-transcription'), 300);
                    }
                }
            } else if (data.type === 'turn_detected') {
                // Visual feedback when a new turn is detected
                console.log('Turn detected:', data);
                if (streamStatus) {
                    streamStatus.textContent = 'Turn detected - speaking...';
                    streamStatus.classList.add('turn-detected');
                    setTimeout(() => streamStatus.classList.remove('turn-detected'), 1000);
                }
            } else if (data.error) {
                if (streamStatus) {
                    streamStatus.textContent = `Error: ${data.error}`;
                    streamStatus.classList.add('error');
                }
            } else if (data.status) {
                if (streamStatus) {
                    streamStatus.textContent = data.message || data.status;
                    streamStatus.classList.remove('error');
                }
            }
        } catch (e) {
            console.log('Non-JSON message:', event.data);
            if (streamStatus) {
                streamStatus.textContent = event.data;
            }
        }
    };
    
    transcribeWebSocket.onclose = () => {
        console.log('Transcription WebSocket disconnected');
        if (streamStatus) {
            streamStatus.textContent = 'Disconnected';
        }
        isTranscribing = false;
    };
    
    transcribeWebSocket.onerror = (error) => {
        console.error('Transcription WebSocket error:', error);
        if (streamStatus) {
            streamStatus.textContent = 'Connection error';
        }
        isTranscribing = false;
    };
}

// Day 17: Streaming Transcription Functions
async function startStreamRecording() {
    if (isStreamRecording) {
        console.log('📝 Day 17: Recording already in progress');
        return;
    }

    try {
        // Request microphone access with specific constraints for AssemblyAI
        const constraints = {
            audio: {
                sampleRate: 16000,
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true
            }
        };

        streamMediaRecorder = null;
        streamAudioChunks = [];
        isStreamRecording = true;

        // Get user media
        streamUserMedia = await navigator.mediaDevices.getUserMedia(constraints);
        
        // Create MediaRecorder
        streamMediaRecorder = new MediaRecorder(streamUserMedia, {
            mimeType: 'audio/webm;codecs=opus'
        });

        // Handle data available
        streamMediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                streamAudioChunks.push(event.data);
            }
        };

        // Handle stop
        streamMediaRecorder.onstop = async () => {
            console.log('📝 Day 17: MediaRecorder stopped, processing audio...');
            
            if (streamAudioChunks.length > 0) {
                const audioBlob = new Blob(streamAudioChunks, { type: 'audio/webm' });
                
                // Send via WebSocket for streaming transcription
                if (transcriptionWs && transcriptionWs.readyState === WebSocket.OPEN) {
                    const reader = new FileReader();
                    reader.onload = () => {
                        const arrayBuffer = reader.result;
                        transcriptionWs.send(arrayBuffer);
                    };
                    reader.readAsArrayBuffer(audioBlob);
                }
            }
        };

        // Start recording
        streamMediaRecorder.start();
        
        // Update UI
        if (streamStatus) streamStatus.textContent = 'Recording... Speak now!';
        
        console.log('📝 Day 17: Streaming transcription started');
        
    } catch (error) {
        console.error('📝 Day 17: Error starting streaming transcription:', error);
        isStreamRecording = false;
        if (streamStatus) streamStatus.textContent = `Error: ${error.message}`;
        throw error;
    }
}

function stopStreamRecording() {
    console.log('📝 Day 17: Stopping streaming transcription...');
    
    isStreamRecording = false;
    
    if (streamMediaRecorder && streamMediaRecorder.state !== 'inactive') {
        streamMediaRecorder.stop();
    }
    
    if (streamUserMedia) {
        streamUserMedia.getTracks().forEach(track => track.stop());
        streamUserMedia = null;
    }
    
    if (streamStatus) streamStatus.textContent = 'Processing transcription...';
    
    console.log('📝 Day 17: Streaming transcription stopped');
}

// Day 21: Base64 Audio Streaming Functions
function connectBase64AudioWebSocket() {
    try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/audio-stream-base64`;
        
        base64AudioWs = new WebSocket(wsUrl);
        
        base64AudioWs.onopen = () => {
            console.log('🎵 Day 21: Base64 Audio WebSocket connected');
            if (base64Status) {
                base64Status.textContent = 'Connected - Ready to stream';
            }
        };
        
        base64AudioWs.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                
                if (data.type === 'audio_chunk') {
                    base64AudioChunks.push(data.data);
                    console.log(`Audio data acknowledgement - Chunk ${base64AudioChunks.length} received by client`);
                    
                    // Update UI with chunk statistics
                    if (base64ChunksDisplay) {
                        const totalChars = base64AudioChunks.join('').length;
                        base64ChunksDisplay.textContent = `Chunks: ${base64AudioChunks.length} | Total Characters: ${totalChars}`;
                    }
                } else if (data.type === 'streaming_complete') {
                    console.log('🎵 Day 21: Base64 audio streaming complete');
                    if (base64Status) {
                        base64Status.textContent = 'Streaming complete';
                    }
                }
            } catch (error) {
                console.error('🎵 Day 21: Error processing base64 audio message:', error);
            }
        };
        
        base64AudioWs.onerror = (error) => {
            console.error('🎵 Day 21: Base64 Audio WebSocket error:', error);
            if (base64Status) {
                base64Status.textContent = 'Connection error';
            }
        };
        
        base64AudioWs.onclose = () => {
            console.log('🎵 Day 21: Base64 Audio WebSocket disconnected');
            if (base64Status) {
                base64Status.textContent = 'Disconnected';
            }
        };
        
    } catch (error) {
        console.error('🎵 Day 21: Error connecting Base64 Audio WebSocket:', error);
    }
}

function startBase64AudioStreaming() {
    const textInput = document.getElementById('base64TextInput');
    if (!textInput || !textInput.value.trim()) {
        console.error('🎵 Day 21: No text input provided');
        return;
    }
    
    if (!base64AudioWs || base64AudioWs.readyState !== WebSocket.OPEN) {
        console.error('🎵 Day 21: WebSocket not connected');
        if (base64Status) {
            base64Status.textContent = 'Error: Not connected';
        }
        return;
    }
    
    // Reset chunks array
    base64AudioChunks = [];
    
    // Send streaming request
    const request = {
        type: 'stream_request',
        text: textInput.value.trim(),
        voice_id: 'natalie'
    };
    
    base64AudioWs.send(JSON.stringify(request));
    
    if (base64Status) {
        base64Status.textContent = 'Streaming audio...';
    }
    
    console.log('🎵 Day 21: Base64 audio streaming started');
}

// Day 22: Streaming Audio Playback Functions
function connectStreamingAudioWebSocket() {
    try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/audio-stream-base64`;
        
        streamingAudioWs = new WebSocket(wsUrl);
        
        streamingAudioWs.onopen = () => {
            console.log('🎶 Day 22: Streaming Audio WebSocket connected');
            if (streamingAudioStatus) {
                streamingAudioStatus.textContent = 'Connected - Ready to stream';
            }
        };
        
        streamingAudioWs.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                
                if (data.type === 'audio_chunk') {
                    streamingAudioChunks.push(data.data);
                    
                    // Update UI
                    if (streamingChunksDisplay) {
                        streamingChunksDisplay.textContent = `Chunks received: ${streamingAudioChunks.length}`;
                    }
                    
                    // Play audio chunk immediately
                    playAudioChunk(data.data, streamingAudioChunks.length === 1);
                    
                } else if (data.type === 'streaming_complete') {
                    console.log('🎶 Day 22: Streaming audio complete');
                    if (streamingAudioStatus) {
                        streamingAudioStatus.textContent = 'Streaming complete';
                    }
                }
            } catch (error) {
                console.error('🎶 Day 22: Error processing streaming audio message:', error);
            }
        };
        
        streamingAudioWs.onerror = (error) => {
            console.error('🎶 Day 22: Streaming Audio WebSocket error:', error);
            if (streamingAudioStatus) {
                streamingAudioStatus.textContent = 'Connection error';
            }
        };
        
        streamingAudioWs.onclose = () => {
            console.log('🎶 Day 22: Streaming Audio WebSocket disconnected');
            if (streamingAudioStatus) {
                streamingAudioStatus.textContent = 'Disconnected';
            }
        };
        
    } catch (error) {
        console.error('🎶 Day 22: Error connecting Streaming Audio WebSocket:', error);
    }
}

function startStreamingAudioPlayback() {
    const textInput = document.getElementById('streamingAudioTextInput');
    if (!textInput || !textInput.value.trim()) {
        console.error('🎶 Day 22: No text input provided');
        return;
    }
    
    if (!streamingAudioWs || streamingAudioWs.readyState !== WebSocket.OPEN) {
        console.error('🎶 Day 22: WebSocket not connected');
        if (streamingAudioStatus) {
            streamingAudioStatus.textContent = 'Error: Not connected';
        }
        return;
    }
    
    // Initialize audio playback
    initializeAudioPlayback();
    
    // Reset chunks and playhead
    streamingAudioChunks = [];
    playheadTime = 0;
    
    // Send streaming request
    const request = {
        type: 'stream_request',
        text: textInput.value.trim(),
        voice_id: 'natalie'
    };
    
    streamingAudioWs.send(JSON.stringify(request));
    
    if (streamingAudioStatus) {
        streamingAudioStatus.textContent = 'Streaming and playing audio...';
    }
    
    console.log('🎶 Day 22: Streaming audio playback started');
}

function initializeAudioPlayback() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: 44100
        });
    }
    
    if (audioContext.state === 'suspended') {
        audioContext.resume();
    }
    
    console.log('🎶 Day 22: Audio context initialized');
}

function playAudioChunk(base64Audio, isFirstChunk) {
    try {
        const pcmData = base64ToPCMFloat32(base64Audio, isFirstChunk);
        if (!pcmData) return;
        
        const audioBuffer = audioContext.createBuffer(1, pcmData.length, audioContext.sampleRate);
        audioBuffer.copyToChannel(pcmData, 0);
        
        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext.destination);
        
        const startTime = audioContext.currentTime + playheadTime;
        source.start(startTime);
        
        playheadTime += audioBuffer.duration;
        
        // Update UI
        if (streamingPlaybackTime) {
            streamingPlaybackTime.textContent = `${playheadTime.toFixed(2)}s`;
        }
        
    } catch (error) {
        console.error('🎶 Day 22: Error playing audio chunk:', error);
    }
}

function base64ToPCMFloat32(base64Audio, isFirstChunk) {
    try {
        const binaryString = atob(base64Audio);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        
        let offset = 0;
        if (isFirstChunk) {
            offset = 44; // Skip WAV header
        }
        
        const pcmData = new Float32Array((bytes.length - offset) / 2);
        for (let i = 0; i < pcmData.length; i++) {
            const sample = (bytes[offset + i * 2] | (bytes[offset + i * 2 + 1] << 8));
            pcmData[i] = sample < 32768 ? sample / 32768 : (sample - 65536) / 32768;
        }
        
        return pcmData;
    } catch (error) {
        console.error('🎶 Day 22: Error converting base64 to PCM:', error);
        return null;
    }
}

function stopStreamingAudioPlayback() {
    if (audioContext) {
        audioContext.suspend();
    }
    
    streamingAudioChunks = [];
    playheadTime = 0;
    
    if (streamingAudioStatus) {
        streamingAudioStatus.textContent = 'Stopped';
    }
    
    console.log('🎶 Day 22: Streaming audio playback stopped');
}

// Removed remaining unused Day 22 audio playback functions - legacy code not used in current Complete Voice Agent workflow

// Removed remaining unused Day 22 streaming audio playback functions - legacy code not used in current Complete Voice Agent workflow

// Removed unused Day 22 audio visualizer functions - legacy code not used in current Complete Voice Agent workflow

// Button State Management Functions
function setLLMButtonStates(recording, ready) {
    if (llmStartBtn) {
        llmStartBtn.disabled = recording || !ready;
        llmStartBtn.textContent = recording ? 'Recording...' : 'Start Recording';
    }
    if (llmStopBtn) {
        llmStopBtn.disabled = !recording;
    }
}

function setStreamButtonStates(recording, ready) {
    if (startStreamRecordingBtn) {
        startStreamRecordingBtn.disabled = recording || !ready;
        startStreamRecordingBtn.textContent = recording ? 'Recording...' : 'Start Stream Recording';
    }
    if (stopStreamRecordingBtn) {
        stopStreamRecordingBtn.disabled = !recording;
    }
}

// LLM WebSocket Connection Function
function connectLLMWebSocket() {
    try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/audio-stream`;
        
        audioWebSocket = new WebSocket(wsUrl);
        
        audioWebSocket.onopen = () => {
            console.log('🎤 LLM WebSocket connected');
            if (llmStatus) {
                llmStatus.textContent = 'WebSocket connected - Ready to stream';
            }
            // Re-enable buttons after successful connection
            setLLMButtonStates(false, true);
        };
        
        audioWebSocket.onmessage = (event) => {
            console.log('🎤 LLM WebSocket message received:', event.data);
        };
        
        audioWebSocket.onerror = (error) => {
            console.error('🎤 LLM WebSocket error:', error);
            if (llmStatus) {
                llmStatus.textContent = 'Connection error';
            }
            setLLMButtonStates(false, false);
        };
        
        audioWebSocket.onclose = () => {
            console.log('🎤 LLM WebSocket disconnected');
            if (llmStatus) {
                llmStatus.textContent = 'Disconnected - Click to reconnect';
            }
            setLLMButtonStates(false, false);
        };
        
    } catch (error) {
        console.error('🎤 Error connecting LLM WebSocket:', error);
        if (llmStatus) {
            llmStatus.textContent = 'Connection failed';
        }
        setLLMButtonStates(false, false);
    }
}

async function processLLMVoiceAgent(audioBlob, voiceId) {
    if (!audioBlob) {
        throw new Error('No audio data available');
    }

    const formData = new FormData();
    formData.append('file', audioBlob, 'recording.webm');
    formData.append('voice_id', voiceId);

    try {
        // Show loading state
        if (llmStatus) {
            llmStatus.textContent = 'Processing your question...';
        }

        // First, transcribe the audio
        const transcriptionResponse = await fetch('/transcribe', {
            method: 'POST',
            body: formData
        });

        if (!transcriptionResponse.ok) {
            const error = await transcriptionResponse.json();
            throw new Error(error.detail || 'Failed to transcribe audio');
        }

        const transcriptionResult = await transcriptionResponse.json();
        const transcription = transcriptionResult.transcription;

        // Update UI with transcription
        if (llmTranscriptionText) {
            llmTranscriptionText.textContent = transcription || 'No transcription available';
        }

        // Add user message to chat history (using backend session management)
        // Note: Chat history is managed on the backend, no frontend chatService needed
        
        // Get chat history for context (empty for now, backend manages this)
        const chatHistory = [];

        // Clear previous response
        const streamingText = document.getElementById('llmStreamingText');
        const responseText = document.getElementById('llmResponseText');
        if (streamingText) streamingText.textContent = '';
        if (responseText) responseText.textContent = 'Generating response...';

        // Check if WebSocket is connected and ready
        if (!llmWebSocket || llmWebSocket.readyState !== WebSocket.OPEN) {
            // Fall back to non-streaming if WebSocket is not available
            console.warn('WebSocket not available, falling back to non-streaming');
            return processNonStreamingLLM(transcription, voiceId, chatHistory);
        }

        // Day 19: Send the request to the streaming LLM endpoint
        console.log('📤 Sending to LLM streaming endpoint:', {
            text: transcription,
            session_id: sessionId || 'default-session'
        });
        
        llmWebSocket.send(JSON.stringify({
            text: transcription,
            session_id: sessionId || 'default-session',
            voice_id: voiceId,
            chat_history: chatHistory
        }));

        // Return a promise that resolves when the streaming is complete
        return new Promise((resolve) => {
            // The actual response will be handled by the WebSocket message handler
            // We'll resolve with a minimal response object for compatibility
            resolve({
                transcription,
                response: '', // Will be updated by WebSocket
                audio_url: ''  // Will be set when TTS is complete
            });
        });

    } catch (error) {
        console.error('Error in processLLMVoiceAgent:', error);
        if (llmStatus) {
            llmStatus.textContent = `Error: ${error.message}`;
        }
        throw error;
    }
}

// Fallback function for non-streaming LLM responses
async function processNonStreamingLLM(transcription, voiceId, chatHistory) {
    try {
        const response = await fetch(`/llm/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: transcription,
                chat_history: chatHistory
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to get LLM response');
        }

        const result = await response.json();

        // Update UI with response
        if (llmResponseText) {
            llmResponseText.textContent = result.response || 'No response generated';
        }

        // Get TTS for the response
        if (result.response) {
            const ttsResponse = await fetch('/tts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: result.response,
                    voice_id: voiceId
                })
            });

            if (ttsResponse.ok) {
                const ttsResult = await ttsResponse.json();
                if (ttsResult.audio_url && llmResponseAudio) {
                    llmResponseAudio.src = ttsResult.audio_url;
                    llmResponseAudio.play().catch(e => console.error('Error playing audio:', e));
                }
            }
        }

        return result;
    } catch (error) {
        console.error('Error in processNonStreamingLLM:', error);
        throw error;
    }
}

function updateChatHistory(messages) {
    if (!llmChatHistory || !messages) {
        return;
    }
    // Clear existing content
    llmChatHistory.innerHTML = '';
    
    // Add each message to the chat history
    messages.forEach(msg => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${msg.role}`;
        messageDiv.innerHTML = `
            <div class="message-role">${msg.role === 'user' ? 'You' : 'AI'}</div>
            <div class="message-content">${msg.content || ''}</div>
        `;
        llmChatHistory.appendChild(messageDiv);
    });
    
    // Scroll to bottom
    llmChatHistory.scrollTop = llmChatHistory.scrollHeight;
}

// Day 23: Complete Voice Agent Variables
let completeVoiceWebSocket = null;
let completeVoiceMediaRecorder = null;
let completeVoiceStream = null;
let isCompleteVoiceRecording = false;
let completeVoiceAudioContext = null;
let completeVoiceAudioChunks = [];
let completeVoiceIsPlaying = false;
let completeVoicePlayheadTime = 0;
let completeVoiceChunksReceived = 0;
let completeVoiceTotalPlaybackTime = 0;
let completeVoiceWavHeaderSet = true;

// Day 23: Complete Voice Agent DOM Elements
let startRecordingBtn = null;
let stopRecordingBtn = null;
let voiceSelect = null;
let connectionStatus = null;
let partialTranscriptDiv = null;
let finalTranscriptDiv = null;
let chunksReceivedDiv = null;
let audioProgressDiv = null;
let playbackTimeDiv = null;
let audioPlaybackStatusDiv = null;
// Removed conversationDisplay - using single chat history only
let chatHistory = null;
let chatCount = null;
let clearChatBtn = null;

// Pipeline status elements
let stepRecording = null;
let stepSTT = null;
let stepAI = null;
let stepTTS = null;
let recordingStatus = null;
let sttStatus = null;
let aiStatus = null;
let ttsStatus = null;

// Initialize the application
function initApp() {
    try {
        console.log('Initializing application...');
        
        // Initialize session
        sessionId = getOrCreateSessionId();
        console.log('Session ID:', sessionId);
        
        // Initialize DOM elements
        console.log('Initializing DOM elements...');
        llmStartBtn = document.getElementById('startLLMRecording');
        llmStopBtn = document.getElementById('stopLLMRecording');
        startLLMRecordingBtn = document.getElementById('startLLMRecording');
        stopLLMRecordingBtn = document.getElementById('stopLLMRecording');
        llmStatus = document.getElementById('llmStatus');
        llmChatHistory = document.getElementById('llmChatHistory');
        llmTranscriptionText = document.getElementById('llmTranscriptionText');
        llmResponseText = document.getElementById('llmResponseText');
        llmStreamingText = document.getElementById('llmStreamingText');
        llmQuestionAudio = document.getElementById('llmQuestionAudio');
        llmResponseAudio = document.getElementById('llmResponseAudio');
        llmVoiceSelect = document.getElementById('llmVoiceSelect');
        
        // Initialize streaming transcription DOM elements
        startStreamRecordingBtn = document.getElementById('startStreamRecording');
        stopStreamRecordingBtn = document.getElementById('stopStreamRecording');
        streamStatus = document.getElementById('streamStatus');
        partialTranscript = document.getElementById('partialTranscript');
        finalTranscript = document.getElementById('finalTranscript');
        
        // Day 21: Initialize base64 audio streaming DOM elements
        startBase64StreamBtn = document.getElementById('startBase64Stream');
        stopBase64StreamBtn = document.getElementById('stopBase64Stream');
        base64Status = document.getElementById('base64Status');
        base64Input = document.getElementById('base64Input');
        base64AudioChunksDisplay = document.getElementById('base64AudioChunks');
        
        // Day 22: Initialize streaming audio playback DOM elements
        startStreamingAudioBtn = document.getElementById('startStreamingAudio');
        stopStreamingAudioBtn = document.getElementById('stopStreamingAudio');
        streamingAudioStatus = document.getElementById('streamingAudioStatus');
        streamingAudioInput = document.getElementById('streamingAudioInput');
        audioPlaybackStatus = document.getElementById('audioPlaybackStatus');
        chunksReceivedDisplay = document.getElementById('chunksReceived');
        audioProgressDisplay = document.getElementById('audioProgress');
        playbackTimeDisplay = document.getElementById('playbackTime');
        
        // Day 23: Initialize Complete Voice Agent DOM elements
        startRecordingBtn = document.getElementById('startRecording');
        stopRecordingBtn = document.getElementById('stopRecording');
        voiceSelect = document.getElementById('voiceSelect');
        connectionStatus = document.getElementById('connectionStatus');
        partialTranscriptDiv = document.getElementById('partialTranscript');
        finalTranscriptDiv = document.getElementById('finalTranscript');
        chunksReceivedDiv = document.getElementById('chunksReceived');
        audioProgressDiv = document.getElementById('audioProgress');
        playbackTimeDiv = document.getElementById('playbackTime');
        audioPlaybackStatusDiv = document.getElementById('audioPlaybackStatus');
        // conversationDisplay removed - using single chat history only
        chatHistory = document.getElementById('chatHistory');
        chatCount = document.getElementById('chatCount');
        clearChatBtn = document.getElementById('clearChat');
        
        // Pipeline status elements
        stepRecording = document.getElementById('step-recording');
        stepSTT = document.getElementById('step-stt');
        stepAI = document.getElementById('step-ai');
        stepTTS = document.getElementById('step-tts');
        recordingStatus = document.getElementById('recording-status');
        sttStatus = document.getElementById('stt-status');
        aiStatus = document.getElementById('ai-status');
        ttsStatus = document.getElementById('tts-status');
        
        // Initialize audio visualizer
        audioCanvas = document.getElementById('audioCanvas');
        if (audioCanvas) {
            audioCanvasContext = audioCanvas.getContext('2d');
        }
        visualizerBars = [
            document.getElementById('bar1'),
            document.getElementById('bar2'),
            document.getElementById('bar3'),
            document.getElementById('bar4'),
            document.getElementById('bar5')
        ];
        
        // Log element initialization
        console.log('Elements initialized:', {
            startLLMRecordingBtn: !!startLLMRecordingBtn,
            stopLLMRecordingBtn: !!stopLLMRecordingBtn,
            llmStatus: !!llmStatus,
            llmChatHistory: !!llmChatHistory,
            llmTranscriptionText: !!llmTranscriptionText,
            llmResponseText: !!llmResponseText,
            llmStreamingText: !!llmStreamingText,
            llmQuestionAudio: !!llmQuestionAudio,
            llmResponseAudio: !!llmResponseAudio,
            llmVoiceSelect: !!llmVoiceSelect,
            // Day 23 elements
            startRecordingBtn: !!startRecordingBtn,
            stopRecordingBtn: !!stopRecordingBtn,
            voiceSelect: !!voiceSelect,
            connectionStatus: !!connectionStatus
        });
        
        // Set initial button states
        setLLMButtonStates(false, true);
        setStreamButtonStates(false, true);
        
        // Set Complete Voice Agent button states (disabled until WebSocket connects)
        if (startRecordingBtn) {
            startRecordingBtn.disabled = false;
            startRecordingBtn.textContent = 'Start Server Connection';
        }
        if (stopRecordingBtn) {
            stopRecordingBtn.disabled = true;
        }
        if (connectionStatus) {
            connectionStatus.textContent = 'Ready to Connect';
            connectionStatus.className = 'connection-status connecting';
        }
        
        // Set up event listeners
        setupEventListeners();
        
        // Initialize WebSocket connections after a short delay
        setTimeout(() => {
            console.log('Initializing WebSocket connections...');
            connectAudioWebSocket();
            connectTranscriptionWebSocket();
            connectLLMWebSocket();
            connectBase64AudioWebSocket(); // Day 21: Initialize base64 audio WebSocket
            connectStreamingAudioWebSocket(); // Day 22: Initialize streaming audio WebSocket
            connectCompleteVoiceWebSocket(); // Day 23: Initialize complete voice agent WebSocket
        }, 500);
        
        console.log('Application initialization complete');
        
    } catch (error) {
        console.error('Error initializing application:', error);
        if (llmStatus) {
            llmStatus.textContent = `Initialization error: ${error.message}`;
        }
    }
}

// Day 23: Complete Voice Agent Functions

// Connect to Complete Voice Agent WebSocket
function connectCompleteVoiceWebSocket() {
    try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/complete-voice-agent?session_id=${sessionId}`;
        
        console.log('🤖 Day 23: Connecting to Complete Voice Agent WebSocket:', wsUrl);
        console.log('🤖 Day 23: Protocol:', protocol, 'Host:', window.location.host);
        
        // Check if WebSocket is supported
        if (!window.WebSocket) {
            console.error('🤖 Day 23: WebSocket not supported by this browser');
            return;
        }
        
        console.log('🤖 Day 23: Creating WebSocket instance...');
        completeVoiceWs = new WebSocket(wsUrl);
        console.log('🤖 Day 23: WebSocket instance created successfully');
    } catch (error) {
        console.error('🤖 Day 23: Error creating WebSocket:', error);
        return;
    }
    
    completeVoiceWs.onopen = () => {
        console.log('🤖 Day 23: Complete Voice Agent WebSocket connected');
        if (connectionStatus) {
            connectionStatus.textContent = 'Connected';
            connectionStatus.className = 'connection-status connected';
        }
        
        // Enable start button only when WebSocket is ready
        if (startRecordingBtn) {
            startRecordingBtn.disabled = false;
            startRecordingBtn.textContent = 'Start Conversation';
        }
    };
    
    completeVoiceWs.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log('🤖 Day 23: WebSocket message:', data);
            
            handleCompleteVoiceMessage(data);
            
        } catch (error) {
            console.error('🤖 Day 23: Error processing WebSocket message:', error);
        }
    };
    
    completeVoiceWs.onclose = (event) => {
        console.log('🤖 Day 23: Complete Voice Agent WebSocket disconnected');
        console.log('🤖 Day 23: Close event details:', {
            code: event.code,
            reason: event.reason,
            wasClean: event.wasClean
        });
        
        if (connectionStatus) {
            connectionStatus.textContent = 'Disconnected';
            connectionStatus.className = 'connection-status disconnected';
        }
        
        // Clean up all recording resources on disconnect
        if (isCompleteVoiceRecording) {
            console.log('🤖 Day 23: Cleaning up recording resources due to WebSocket disconnect');
            
            // Stop recording flag
            isCompleteVoiceRecording = false;
            
            // Clean up media stream and tracks
            if (completeVoiceStream) {
                completeVoiceStream.getTracks().forEach(track => {
                    track.stop();
                    console.log('🤖 Day 23: Stopped audio track on disconnect:', track.label);
                });
                completeVoiceStream = null;
            }
            
            // Clean up audio context
            if (completeVoiceAudioContext) {
                try {
                    if (completeVoiceAudioContext.state !== 'closed') {
                        completeVoiceAudioContext.close();
                        console.log('🤖 Day 23: Closed audio context on disconnect');
                    }
                } catch (error) {
                    console.warn('🤖 Day 23: Error closing audio context on disconnect:', error);
                }
                completeVoiceAudioContext = null;
            }
            
            // Clean up script processor
            if (completeVoiceScriptProcessor) {
                completeVoiceScriptProcessor.disconnect();
                completeVoiceScriptProcessor = null;
                console.log('🤖 Day 23: Disconnected script processor on disconnect');
            }
            
            // Reset media recorder
            completeVoiceMediaRecorder = null;
        }
        
        // Enable start button for reconnection, disable stop button
        if (startRecordingBtn) {
            startRecordingBtn.disabled = false;
            startRecordingBtn.textContent = 'Disconnected - Click to Reconnect';
        }
        if (stopRecordingBtn) stopRecordingBtn.disabled = true;
        
        // Reset pipeline status
        resetPipelineStatus();
    };
    
    completeVoiceWs.onerror = (error) => {
        console.error('🤖 Day 23: Complete Voice Agent WebSocket error:', error);
        console.error('🤖 Day 23: Error details:', {
            type: error.type,
            target: error.target,
            readyState: completeVoiceWs.readyState
        });
        
        if (connectionStatus) {
            connectionStatus.textContent = 'Error';
            connectionStatus.className = 'connection-status error';
        }
    };
}

// Handle Complete Voice Agent WebSocket messages
function handleCompleteVoiceMessage(data) {
    switch (data.type) {
        case 'ready':
            console.log('🤖 Day 23: Complete Voice Agent ready');
            break;
            
        case 'pipeline_status':
            updatePipelineStatus(data.step, data.status);
            break;
            
        case 'recording_started':
            console.log('🤖 Day 23: Recording started:', data.message);
            updatePipelineStatus('recording', 'active');
            break;
            
        case 'recording_stopped':
            console.log('🤖 Day 23: Recording stopped:', data.message);
            updatePipelineStatus('recording', 'complete');
            break;
            
        case 'stt_started':
            console.log('🤖 Day 23: STT started:', data.message);
            updatePipelineStatus('stt', 'processing');
            break;
            
        case 'partial_transcript':
            updatePartialTranscript(data.text);
            if (data.text && data.text.trim()) {
                updatePipelineStatus('stt', 'processing');
            }
            break;
            
        case 'final_transcript':
            updateFinalTranscript(data.text);
            updatePipelineStatus('stt', 'complete');
            
            // Don't add unrefined final transcripts to chat history
            // Wait for refined_final_transcript instead
            
            // Reset pipeline if no speech detected
            if (!data.text || !data.text.trim() || data.text.includes('No speech detected')) {
                console.log('🤖 Day 23: No speech detected, resetting pipeline');
                setTimeout(() => {
                    resetPipelineStatus();
                }, 2000);
            }
            break;
            
        case 'refined_final_transcript':
            // This is the refined transcript - add to chat history
            if (data.text && data.text.trim()) {
                // Check if this transcript is already in chat history
                const existingMessages = document.querySelectorAll('.chat-message.user .message-text');
                const isDuplicate = Array.from(existingMessages).some(msg => 
                    msg.textContent.trim().toLowerCase() === data.text.trim().toLowerCase()
                );
                
                if (!isDuplicate) {
                    addMessageToChatHistory('user', data.text);
                    updatePipelineStatus('ai', 'thinking');
                    console.log('🤖 Day 23: Added refined transcript to chat:', data.text);
                }
            }
            break;
            
        case 'llm_chunk':
            updatePipelineStatus('ai', 'processing');
            // Just show streaming chunks in real-time, don't save to chat yet
            // updateCurrentAIMessage(data.text);
            break;
            
        case 'llm_complete':
            updatePipelineStatus('ai', 'complete');
            updatePipelineStatus('tts', 'generating');
            
            // Add final complete response to chat history
            if (data.text && data.text.trim()) {
                addMessageToChatHistory('assistant', data.text);
            }
            break;
            
        case 'tts_complete':
            console.log('🤖 Day 23: TTS complete:', data.message);
            // TTS is complete, audio playback will continue
            break;
            
        case 'audio_chunk':
            // Backend sends audio data in "data" field
            if (data.data) {
                playCompleteVoiceAudioChunk(data.data, data.chunk_index, data.is_final);
            } else {
                console.error('🤖 Day 23: No audio data found in message:', data);
            }
            updatePipelineStatus('tts', 'streaming');
            break;
            
        case 'conversation_update':
            // Handle via chat history - no separate conversation display
            break;
            
        case 'chat_history':
            updateChatHistoryDisplay(data.messages, data.count);
            break;
            
        case 'pipeline_complete':
            console.log('🤖 Day 23: Pipeline complete:', data.message);
            updatePipelineStatus('tts', 'complete');
            
            // Finalize the current AI message
            finalizeCurrentAIMessage();
            
            // Reset pipeline after a short delay
            setTimeout(() => {
                resetPipelineStatus();
            }, 3000);
            break;
            
        case 'pipeline_error':
        case 'error':
            handlePipelineError(data.message, data.step);
            break;
            
        default:
            console.log('🤖 Day 23: Unknown message type:', data.type, data);
    }
}

// Update pipeline status
function updatePipelineStatus(step, status) {
    const stepElement = document.getElementById(`step-${step}`);
    const statusElement = document.getElementById(`${step}-status`);
    
    if (stepElement && statusElement) {
        // Remove all status classes
        stepElement.classList.remove('active', 'completed', 'error');
        
        // Add appropriate status class
        if (status === 'active' || status === 'processing' || status === 'thinking' || status === 'generating' || status === 'streaming') {
            stepElement.classList.add('active');
        } else if (status === 'complete' || status === 'completed') {
            stepElement.classList.add('completed');
        } else if (status === 'error') {
            stepElement.classList.add('error');
        }
        
        // Update status text
        statusElement.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    }
    
    console.log(`🤖 Day 23: Pipeline ${step} status: ${status}`);
}

// Reset pipeline status
function resetPipelineStatus() {
    const steps = ['recording', 'stt', 'ai', 'tts'];
    steps.forEach(step => {
        const stepElement = document.getElementById(`step-${step}`);
        const statusElement = document.getElementById(`${step}-status`);
        
        if (stepElement) {
            stepElement.classList.remove('active', 'completed', 'error');
        }
        
        if (statusElement) {
            statusElement.textContent = step === 'recording' ? 'Ready' : 'Waiting';
        }
    });
    
    // Reset audio playback status
    const audioPlaybackStatusDiv = document.getElementById('audio-playback-status');
    if (audioPlaybackStatusDiv) {
        audioPlaybackStatusDiv.textContent = 'Ready to play audio...';
    }
    
    // Clear transcription displays
    if (partialTranscriptDiv) {
        partialTranscriptDiv.textContent = 'Start speaking to see live transcription...';
    }
    if (finalTranscriptDiv) {
        finalTranscriptDiv.textContent = 'Your final transcription will appear here...';
    }
    
    // Chat history persists - no clearing needed
}

// Update partial transcript
function updatePartialTranscript(text) {
    if (partialTranscriptDiv) {
        partialTranscriptDiv.textContent = text;
        partialTranscriptDiv.scrollTop = partialTranscriptDiv.scrollHeight;
    }
}

// Update final transcript
function updateFinalTranscript(text) {
    if (finalTranscriptDiv) {
        finalTranscriptDiv.textContent = text;
        finalTranscriptDiv.scrollTop = finalTranscriptDiv.scrollHeight;
    }
    
    // Clear partial transcript
    if (partialTranscriptDiv) {
        partialTranscriptDiv.textContent = 'Start speaking to see live transcription...';
    }
}

// Global variable to track current AI message being typed
let currentAIMessageElement = null;

// Add message to chat history
function addMessageToChatHistory(role, text) {
    if (!chatHistory) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;
    messageDiv.innerHTML = `
        <div class="message-role">${role === 'user' ? 'You' : 'AI'}</div>
        <div class="message-content">${text}</div>
        <div class="message-time">${new Date().toLocaleTimeString()}</div>
    `;
    
    chatHistory.appendChild(messageDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    
    // Update chat count
    const messageCount = chatHistory.children.length;
    if (chatCount) {
        chatCount.textContent = `${messageCount} messages`;
    }
}

// Update current AI message being typed (for streaming)
function updateCurrentAIMessage(text) {
    if (!chatHistory) return;
    
    // Find or create current AI message element
    if (!currentAIMessageElement) {
        currentAIMessageElement = document.createElement('div');
        currentAIMessageElement.className = 'chat-message assistant typing';
        currentAIMessageElement.innerHTML = `
            <div class="message-role">AI</div>
            <div class="message-content"></div>
            <div class="message-time">${new Date().toLocaleTimeString()}</div>
        `;
        chatHistory.appendChild(currentAIMessageElement);
    }
    
    // Update the content
    const contentDiv = currentAIMessageElement.querySelector('.message-content');
    if (contentDiv) {
        contentDiv.textContent = text;
    }
    
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Finalize current AI message (remove typing indicator)
function finalizeCurrentAIMessage() {
    if (currentAIMessageElement) {
        currentAIMessageElement.classList.remove('typing');
        currentAIMessageElement = null;
        
        // Update chat count
        const messageCount = chatHistory.children.length;
        if (chatCount) {
            chatCount.textContent = `${messageCount} messages`;
        }
    }
}

// Clear chat history
function clearChatHistory() {
    if (chatHistory) {
        chatHistory.innerHTML = '';
    }
    if (chatCount) {
        chatCount.textContent = '0 messages';
    }
    currentAIMessageElement = null;
}

// Update chat history display
function updateChatHistoryDisplay(messages, count) {
    if (chatCount) {
        chatCount.textContent = `${count} messages`;
    }
    
    if (chatHistory && messages) {
        chatHistory.innerHTML = '';
        
        messages.forEach(msg => {
            const messageDiv = document.createElement('div');
            messageDiv.className = `chat-message ${msg.role}`;
            messageDiv.innerHTML = `
                <div class="message-role">${msg.role === 'user' ? 'You' : 'AI'}</div>
                <div class="message-content">${msg.content}</div>
                <div class="message-time">${new Date(msg.timestamp).toLocaleTimeString()}</div>
            `;
            chatHistory.appendChild(messageDiv);
        });
        
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
}

// Handle pipeline errors
function handlePipelineError(message, step) {
    console.error(`🤖 Day 23: Pipeline error in ${step}:`, message);
    
    // Update pipeline status to error
    if (step) {
        updatePipelineStatus(step, 'error');
    }
    
    // Show error in appropriate UI element
    if (connectionStatus) {
        connectionStatus.textContent = `Error: ${message}`;
        connectionStatus.className = 'connection-status error';
    }
    
    // Stop recording if active
    if (isCompleteVoiceRecording) {
        stopCompleteVoiceRecording();
    }
}

// Initialize Complete Voice Agent audio context
function initCompleteVoiceAudioContext() {
    if (!completeVoiceAudioContext) {
        completeVoiceAudioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: 44100
        });
        console.log('🤖 Day 23: Audio context initialized for Complete Voice Agent');
    }
}

// Convert base64 to PCM Float32 for Complete Voice Agent
// Day 22 working implementation - Convert base64 to PCM Float32 (fixed for proper audio quality)
function completeVoiceBase64ToPCMFloat32(base64Audio) {
    try {
        // Validate input
        if (!base64Audio || typeof base64Audio !== 'string') {
            console.error('🤖 Day 23: Invalid base64Audio input:', base64Audio);
            return null;
        }
        
        // Clean the base64 string - remove any whitespace and line breaks
        const cleanBase64 = base64Audio.replace(/\s+/g, '');
        
        let binary = atob(cleanBase64);
        const offset = completeVoiceWavHeaderSet ? 44 : 0; // Skip WAV header if present
        if (completeVoiceWavHeaderSet) {
            console.log('🤖 Day 23: Skipping WAV header for first chunk');
            completeVoiceWavHeaderSet = false;
        }
        const length = binary.length - offset;

        const buffer = new ArrayBuffer(length);
        const byteArray = new Uint8Array(buffer);
        for (let i = 0; i < byteArray.length; i++) {
            byteArray[i] = binary.charCodeAt(i + offset);
        }

        const view = new DataView(byteArray.buffer);
        const sampleCount = byteArray.length / 2;
        const float32Array = new Float32Array(sampleCount);

        for (let i = 0; i < sampleCount; i++) {
            const int16 = view.getInt16(i * 2, true);
            float32Array[i] = int16 / 32768;
        }

        console.log(`🤖 Day 23: Converted ${sampleCount} samples from base64`);
        return float32Array;
        
    } catch (error) {
        console.error('🤖 Day 23: Error converting base64 to PCM:', error);
        return null;
    }
}

// Play audio chunk for Complete Voice Agent
function playCompleteVoiceAudioChunk(base64Audio, chunkIndex, isFinal) {
    try {
        initCompleteVoiceAudioContext();
        
        const float32Array = completeVoiceBase64ToPCMFloat32(base64Audio);
        if (!float32Array) {
            return;
        }
        
        completeVoiceAudioChunks.push(float32Array);
        
        // Start playing immediately when we have chunks and not already playing
        if (!completeVoiceIsPlaying && completeVoiceAudioChunks.length >= 1) {
            completeVoiceIsPlaying = true;
            if (completeVoiceAudioContext.state === 'suspended') {
                completeVoiceAudioContext.resume();
            }
            playNextCompleteVoiceChunk();
        }
        
        // Update UI
        updateCompleteVoicePlaybackUI(chunkIndex, isFinal);
        
        console.log(`🤖 Day 23: Audio chunk queued - ${completeVoiceAudioChunks.length} chunks in buffer`);
        
    } catch (error) {
        console.error('🤖 Day 23: Error in playCompleteVoiceAudioChunk:', error);
    }
}

// Play next chunk in queue for Complete Voice Agent
function playNextCompleteVoiceChunk() {
    if (completeVoiceAudioChunks.length > 0) {
        const chunk = completeVoiceAudioChunks.shift();
        
        if (completeVoiceAudioContext.state === 'suspended') {
            completeVoiceAudioContext.resume();
        }
        
        const buffer = completeVoiceAudioContext.createBuffer(1, chunk.length, 44100);
        buffer.copyToChannel(chunk, 0);
        const source = completeVoiceAudioContext.createBufferSource();
        source.buffer = buffer;
        
        // Add gain node for volume control
        const gainNode = completeVoiceAudioContext.createGain();
        gainNode.gain.value = 0.8;
        source.connect(gainNode);
        gainNode.connect(completeVoiceAudioContext.destination);
        
        const now = completeVoiceAudioContext.currentTime;
        if (completeVoicePlayheadTime < now) {
            completeVoicePlayheadTime = now + 0.05;
        }
        source.start(completeVoicePlayheadTime);
        completeVoicePlayheadTime += buffer.duration;
        
        completeVoiceTotalPlaybackTime += buffer.duration;
        
        console.log(`🤖 Day 23: Playing chunk - Duration: ${buffer.duration.toFixed(3)}s, Buffer: ${completeVoiceAudioChunks.length} chunks`);
        
        if (completeVoiceAudioChunks.length > 0) {
            playNextCompleteVoiceChunk();
        } else {
            completeVoiceIsPlaying = false;
        }
    }
}

// Update playback UI for Complete Voice Agent
function updateCompleteVoicePlaybackUI(chunkIndex, isFinal) {
    completeVoiceChunksReceived = chunkIndex + 1;
    
    if (chunksReceivedDiv) {
        chunksReceivedDiv.textContent = `${completeVoiceChunksReceived}`;
        chunksReceivedDiv.classList.add('audio-chunk-received');
        setTimeout(() => chunksReceivedDiv.classList.remove('audio-chunk-received'), 300);
    }
    
    if (playbackTimeDiv) {
        playbackTimeDiv.textContent = `${completeVoiceTotalPlaybackTime.toFixed(1)}s`;
    }
    
    if (audioProgressDiv) {
        const progress = isFinal ? 100 : Math.min(98, completeVoiceChunksReceived * 3);
        audioProgressDiv.textContent = `${progress}%`;
    }
    
    if (audioPlaybackStatusDiv) {
        if (isFinal) {
            audioPlaybackStatusDiv.textContent = `Playback complete - ${completeVoiceChunksReceived} chunks played seamlessly`;
        } else {
            audioPlaybackStatusDiv.textContent = `Playing chunk ${completeVoiceChunksReceived} - Seamless streaming audio`;
        }
    }
}

// Start Complete Voice Agent recording
async function startCompleteVoiceRecording() {
    if (isCompleteVoiceRecording) {
        console.log('🤖 Day 23: Recording already in progress');
        return;
    }
    
    try {
        console.log('🤖 Day 23: Starting Complete Voice Agent recording...');
        
        // Check WebSocket connection
        if (!completeVoiceWs || completeVoiceWs.readyState !== WebSocket.OPEN) {
            throw new Error('WebSocket not connected');
        }
        
        // Request microphone access with EXACT Day 17 constraints
        const constraints = {
            audio: {
                sampleRate: 16000,
                channelCount: 1,
                autoGainControl: true,
                noiseSuppression: false,
                echoCancellation: false,
                volume: 1.0
            }
        };
        
        console.log('🤖 Day 23: Requesting microphone access with constraints:', constraints);
        
        completeVoiceStream = await navigator.mediaDevices.getUserMedia(constraints);
        console.log('🤖 Day 23: Microphone access granted, stream active:', completeVoiceStream.active);
        
        // Log detailed microphone information
        const audioTracks = completeVoiceStream.getAudioTracks();
        if (audioTracks.length > 0) {
            const track = audioTracks[0];
            const settings = track.getSettings();
            console.log('🤖 Day 23: Microphone details:', {
                label: track.label,
                enabled: track.enabled,
                readyState: track.readyState,
                deviceId: settings.deviceId,
                sampleRate: settings.sampleRate,
                channelCount: settings.channelCount,
                autoGainControl: settings.autoGainControl,
                noiseSuppression: settings.noiseSuppression,
                echoCancellation: settings.echoCancellation
            });
        }
        
        // Reset state
        completeVoiceAudioChunks = [];
        completeVoiceChunksReceived = 0;
        completeVoiceTotalPlaybackTime = 0;
        completeVoicePlayheadTime = 0;
        
        // Clear previous conversation
        if (partialTranscriptDiv) {
            partialTranscriptDiv.textContent = 'Listening...';
        }
        if (finalTranscriptDiv) {
            finalTranscriptDiv.textContent = 'Your final speech will appear here';
        }
        
        // Create audio context for level monitoring
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const source = audioContext.createMediaStreamSource(completeVoiceStream);
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        source.connect(analyser);
        
        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        
        // Monitor audio levels with more detailed logging
        let audioLevelCount = 0;
        const monitorAudio = () => {
            if (isCompleteVoiceRecording) {
                analyser.getByteFrequencyData(dataArray);
                const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
                const max = Math.max(...dataArray);
                
                audioLevelCount++;
                // Log every 50th reading (about once per second) or when audio detected
                if (audioLevelCount % 50 === 0 || average > 5) {
                    console.log(`🤖 Day 23: Audio levels - Avg: ${average.toFixed(2)}, Max: ${max}, Samples: ${dataArray.length}`);
                }
                
                if (average > 10) { // Threshold for detecting speech
                    console.log(`🤖 Day 23: Speech detected! Level: ${average.toFixed(2)}`);
                }
                
                requestAnimationFrame(monitorAudio);
            }
        };
        monitorAudio();
        
        // Use Web Audio API to get raw PCM data for AssemblyAI (like Day 17)
        completeVoiceAudioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: 16000
        });
        const source16k = completeVoiceAudioContext.createMediaStreamSource(completeVoiceStream);
        completeVoiceScriptProcessor = completeVoiceAudioContext.createScriptProcessor(4096, 1, 1);
        
        completeVoiceScriptProcessor.onaudioprocess = (event) => {
            console.log(`🤖 Day 23: onaudioprocess fired - Recording: ${isCompleteVoiceRecording}, WebSocket: ${completeVoiceWs?.readyState}`);
            
            if (completeVoiceWs && completeVoiceWs.readyState === WebSocket.OPEN && isCompleteVoiceRecording) {
                const inputBuffer = event.inputBuffer;
                const inputData = inputBuffer.getChannelData(0);
                
                // Check audio levels
                const maxLevel = Math.max(...inputData.map(Math.abs));
                console.log(`🤖 Day 23: Audio level: ${maxLevel.toFixed(4)}, Samples: ${inputData.length}`);
                
                // Convert float32 to int16 PCM (EXACT Day 17 implementation)
                const pcmData = new Int16Array(inputData.length);
                for (let i = 0; i < inputData.length; i++) {
                    pcmData[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
                }
                
                console.log(`🤖 Day 23: Sending ${pcmData.buffer.byteLength} bytes to WebSocket`);
                completeVoiceWs.send(pcmData.buffer);
            } else {
                console.log(`🤖 Day 23: Skipping - conditions not met`);
            }
        };
        
        source16k.connect(completeVoiceScriptProcessor);
        completeVoiceScriptProcessor.connect(completeVoiceAudioContext.destination);
        
        // CRITICAL FIX: Ensure audio context is resumed (required for Chrome)
        if (completeVoiceAudioContext.state === 'suspended') {
            console.log('🤖 Day 23: Audio context suspended, resuming...');
            completeVoiceAudioContext.resume().then(() => {
                console.log('🤖 Day 23: Audio context resumed successfully');
            }).catch(err => {
                console.error('🤖 Day 23: Failed to resume audio context:', err);
            });
        } else {
            console.log(`🤖 Day 23: Audio context state: ${completeVoiceAudioContext.state}`);
        }
        
        // Set recording flag immediately - don't wait for MediaRecorder events
        isCompleteVoiceRecording = true;
        console.log('🤖 Day 23: Recording flag set to true');
        
        // Store references for cleanup
        completeVoiceMediaRecorder = {
            audioContext: completeVoiceAudioContext,
            source: source16k,
            completeVoiceScriptProcessor,
            stream: completeVoiceStream,
            start: () => {
                console.log('🤖 Day 23: PCM audio processing started');
            },
            stop: () => {
                completeVoiceScriptProcessor.disconnect();
                source16k.disconnect();
                completeVoiceAudioContext.close();
                completeVoiceStream.getTracks().forEach(track => track.stop());
            }
        };
        
        completeVoiceMediaRecorder.onstart = () => {
            console.log('🤖 Day 23: MediaRecorder started');
            updatePipelineStatus('recording', 'active');
        };
        
        completeVoiceMediaRecorder.onstop = () => {
            console.log('🤖 Day 23: MediaRecorder stopped');
            isCompleteVoiceRecording = false;
            updatePipelineStatus('recording', 'complete');
            
            // Clean up stream
            if (completeVoiceStream) {
                completeVoiceStream.getTracks().forEach(track => track.stop());
                completeVoiceStream = null;
            }
        };
        
        // Send start command with voice selection
        const voiceId = voiceSelect ? voiceSelect.value : 'en-US-natalie';
        completeVoiceWs.send(JSON.stringify({
            type: 'start_recording',
            session_id: sessionId || 'default-session',
            voice_id: voiceId
        }));
        
        // Start recording with 100ms chunks
        completeVoiceMediaRecorder.start(100);
        
        // Update UI
        if (startRecordingBtn) startRecordingBtn.disabled = true;
        if (stopRecordingBtn) stopRecordingBtn.disabled = false;
        
        console.log('🤖 Day 23: Recording started successfully');
        
    } catch (error) {
        console.error('🤖 Day 23: Error starting recording:', error);
        handlePipelineError(error.message, 'recording');
        
        // Clean up on error
        if (completeVoiceStream) {
            completeVoiceStream.getTracks().forEach(track => track.stop());
            completeVoiceStream = null;
        }
        isCompleteVoiceRecording = false;
    }
}

// Stop Complete Voice Agent recording
function stopCompleteVoiceRecording() {
    console.log('🤖 Day 23: Stopping Complete Voice Agent recording...');
    
    // Stop recording flag first
    isCompleteVoiceRecording = false;
    
    // Stop media recorder
    if (completeVoiceMediaRecorder && completeVoiceMediaRecorder.state !== 'inactive') {
        completeVoiceMediaRecorder.stop();
    }
    
    // Clean up media stream and tracks
    if (completeVoiceStream) {
        completeVoiceStream.getTracks().forEach(track => {
            track.stop();
            console.log('🤖 Day 23: Stopped audio track:', track.label);
        });
        completeVoiceStream = null;
    }
    
    // Clean up audio context
    if (completeVoiceAudioContext) {
        try {
            if (completeVoiceAudioContext.state !== 'closed') {
                completeVoiceAudioContext.close();
                console.log('🤖 Day 23: Closed audio context');
            }
        } catch (error) {
            console.warn('🤖 Day 23: Error closing audio context:', error);
        }
        completeVoiceAudioContext = null;
    }
    
    // Clean up script processor
    if (completeVoiceScriptProcessor) {
        completeVoiceScriptProcessor.disconnect();
        completeVoiceScriptProcessor = null;
        console.log('🤖 Day 23: Disconnected script processor');
    }
    
    // Reset media recorder
    completeVoiceMediaRecorder = null;
    
    // Reset audio playback variables
    completeVoiceAudioChunks = [];
    completeVoiceChunksReceived = 0;
    completeVoiceTotalPlaybackTime = 0;
    completeVoicePlayheadTime = 0;
    
    // Send stop command to server
    if (completeVoiceWs && completeVoiceWs.readyState === WebSocket.OPEN) {
        completeVoiceWs.send(JSON.stringify({
            type: 'stop_recording'
        }));
    }
    
    // Update UI
    if (startRecordingBtn) startRecordingBtn.disabled = false;
    if (stopRecordingBtn) stopRecordingBtn.disabled = true;
    
    console.log('🤖 Day 23: Complete Voice Agent recording stopped and resources cleaned up');
}

// Clear chat history
function clearCompleteVoiceChatHistory() {
    if (completeVoiceWs && completeVoiceWs.readyState === WebSocket.OPEN) {
        completeVoiceWs.send(JSON.stringify({
            type: 'clear_chat',
            session_id: sessionId || 'default-session'
        }));
    }
    
    // Clear UI
    if (chatHistory) {
        chatHistory.textContent = 'No conversation history yet.';
    }
    if (chatCount) {
        chatCount.textContent = '0 messages';
    }
    // conversationDisplay removed - using single chat history only
}

// Mobile touch detection
function isMobileDevice() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
           (navigator.maxTouchPoints && navigator.maxTouchPoints > 2);
}

// Mobile-specific audio context initialization
function initMobileAudioContext() {
    if (isMobile && !mobileAudioContext) {
        try {
            mobileAudioContext = new (window.AudioContext || window.webkitAudioContext)();
            
            // Resume audio context on user interaction for mobile browsers
            if (mobileAudioContext.state === 'suspended') {
                document.addEventListener('touchstart', () => {
                    mobileAudioContext.resume();
                }, { once: true });
            }
            
            console.log('Mobile audio context initialized:', mobileAudioContext.state);
        } catch (error) {
            console.error('Failed to initialize mobile audio context:', error);
        }
    }
}

// Mobile-specific WebSocket connection with retry logic
function createMobileWebSocket(url, protocols = []) {
    return new Promise((resolve, reject) => {
        try {
            const ws = new WebSocket(url, protocols);
            
            // Mobile-specific timeout handling
            const connectionTimeout = setTimeout(() => {
                ws.close();
                reject(new Error('WebSocket connection timeout on mobile'));
            }, isMobile ? 10000 : 5000); // Longer timeout for mobile
            
            ws.onopen = () => {
                clearTimeout(connectionTimeout);
                mobileWebSocketRetryCount = 0;
                console.log('Mobile WebSocket connected successfully');
                resolve(ws);
            };
            
            ws.onerror = (error) => {
                clearTimeout(connectionTimeout);
                console.error('Mobile WebSocket error:', error);
                
                // Retry logic for mobile
                if (isMobile && mobileWebSocketRetryCount < maxMobileRetries) {
                    mobileWebSocketRetryCount++;
                    console.log(`Retrying mobile WebSocket connection (${mobileWebSocketRetryCount}/${maxMobileRetries})`);
                    setTimeout(() => {
                        createMobileWebSocket(url, protocols).then(resolve).catch(reject);
                    }, 2000 * mobileWebSocketRetryCount);
                } else {
                    reject(error);
                }
            };
            
        } catch (error) {
            reject(error);
        }
    });
}

// Mobile-specific MediaRecorder configuration
function getMobileMediaRecorderOptions() {
    if (!isMobile) {
        return { mimeType: 'audio/webm;codecs=opus' };
    }
    
    // Mobile-specific codec preferences
    const mobileCodecs = [
        'audio/webm;codecs=opus',
        'audio/mp4;codecs=mp4a.40.2',
        'audio/mpeg',
        'audio/wav'
    ];
    
    for (const codec of mobileCodecs) {
        if (MediaRecorder.isTypeSupported(codec)) {
            console.log('Using mobile codec:', codec);
            return { mimeType: codec };
        }
    }
    
    console.warn('No supported mobile codecs found, using default');
    return {};
}

// Mobile-specific error handling and user feedback
function showMobileError(message, fallbackAction = null) {
    console.error('Mobile error:', message);
    
    // Show user-friendly mobile error message
    const errorMsg = isMobile ? 
        `Mobile Browser Issue: ${message}${fallbackAction ? ` Try: ${fallbackAction}` : ''}` : 
        message;
    
    // Use notification system if available, otherwise alert
    if (typeof showNotification === 'function') {
        showNotification(errorMsg, 'error');
    } else {
        alert(errorMsg);
    }
}

// Mobile-specific getUserMedia with fallbacks
async function getMobileUserMedia(constraints) {
    try {
        // Standard getUserMedia
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            return await navigator.mediaDevices.getUserMedia(constraints);
        }
        
        // Fallback for older mobile browsers
        const getUserMedia = navigator.getUserMedia || 
                           navigator.webkitGetUserMedia || 
                           navigator.mozGetUserMedia || 
                           navigator.msGetUserMedia;
        
        if (getUserMedia) {
            return new Promise((resolve, reject) => {
                getUserMedia.call(navigator, constraints, resolve, reject);
            });
        }
        
        throw new Error('getUserMedia not supported on this mobile browser');
        
    } catch (error) {
        console.error('Mobile getUserMedia error:', error);
        
        // Provide mobile-specific error messages and solutions
        if (error.name === 'NotAllowedError') {
            showMobileError('Microphone access denied. Please enable microphone permissions in your browser settings.', 'Check browser permissions');
        } else if (error.name === 'NotFoundError') {
            showMobileError('No microphone found. Please check your device has a working microphone.', 'Try refreshing the page');
        } else if (error.name === 'NotSupportedError') {
            showMobileError('Audio recording not supported on this mobile browser.', 'Try using Chrome or Safari');
        } else {
            showMobileError(`Audio access failed: ${error.message}`, 'Try refreshing the page');
        }
        
        throw error;
    }
}

// Add both click and touch events for mobile compatibility
function addMobileCompatibleEvent(element, callback) {
    if (!element) return;
    
    // Add click event for all devices
    element.addEventListener('click', callback);
    
    // Add touch events for mobile devices
    if (isMobileDevice()) {
        element.addEventListener('touchstart', (e) => {
            e.preventDefault();
            callback(e);
        }, { passive: false });
    }
}

// Set up all event listeners
function setupEventListeners() {
    if (startLLMRecordingBtn) {
        addMobileCompatibleEvent(startLLMRecordingBtn, async (e) => {
            try {
                await startLLMRecording();
            } catch (error) {
                console.error('Error starting LLM recording:', error);
                updateLLMStatus('Error starting recording: ' + error.message);
            }
        });
    }
    
    if (stopLLMRecordingBtn) {
        addMobileCompatibleEvent(stopLLMRecordingBtn, () => {
            try {
                stopLLMRecording();
            } catch (error) {
                console.error('Error in stopLLMRecording:', error);
                if (llmStatus) {
                    llmStatus.textContent = `Error: ${error.message}`;
                }
            }
        });
    }
    
    // Streaming transcription event listeners
    if (startStreamRecordingBtn) {
        addMobileCompatibleEvent(startStreamRecordingBtn, async (e) => {
            try {
                await startStreamRecording();
            } catch (error) {
                console.error('Error in startStreamRecording:', error);
                if (streamStatus) {
                    streamStatus.textContent = `Error: ${error.message}`;
                }
            }
        });
    }
    
    if (stopStreamRecordingBtn) {
        stopStreamRecordingBtn.addEventListener('click', () => {
            try {
                stopStreamRecording();
            } catch (error) {
                console.error('Error in stopStreamRecording:', error);
                if (streamStatus) {
                    streamStatus.textContent = `Error: ${error.message}`;
                }
            }
        });
    }
    
    // Day 21: Base64 audio streaming event listeners
    if (startBase64StreamBtn) {
        startBase64StreamBtn.addEventListener('click', () => {
            try {
                startBase64AudioStreaming();
            } catch (error) {
                console.error('Error in startBase64AudioStreaming:', error);
                if (base64Status) {
                    base64Status.textContent = `Error: ${error.message}`;
                }
            }
        });
    }
    
    // Day 22: Streaming audio playback event listeners
    if (startStreamingAudioBtn) {
        startStreamingAudioBtn.addEventListener('click', () => {
            try {
                startStreamingAudioPlayback();
            } catch (error) {
                console.error('Error in startStreamingAudioPlayback:', error);
                if (streamingAudioStatus) {
                    streamingAudioStatus.textContent = `Error: ${error.message}`;
                }
            }
        });
    }
    
    if (stopStreamingAudioBtn) {
        stopStreamingAudioBtn.addEventListener('click', () => {
            try {
                stopStreamingAudioPlayback();
            } catch (error) {
                console.error('Error in stopStreamingAudioPlayback:', error);
                if (streamingAudioStatus) {
                    streamingAudioStatus.textContent = `Error: ${error.message}`;
                }
            }
        });
    }
    
    // Day 23: Complete Voice Agent event listeners
    if (startRecordingBtn) {
        startRecordingBtn.addEventListener('click', async () => {
            try {
                // Check if we need to reconnect WebSocket first
                if (startRecordingBtn.textContent.includes('Disconnected') || 
                    startRecordingBtn.textContent.includes('Connecting') ||
                    !completeVoiceWs || completeVoiceWs.readyState !== WebSocket.OPEN) {
                    console.log('🤖 Day 23: Reconnecting WebSocket...');
                    startRecordingBtn.textContent = 'Connecting...';
                    connectCompleteVoiceWebSocket();
                    return;
                }
                
                await startCompleteVoiceRecording();
            } catch (error) {
                console.error('🤖 Day 23: Error in startCompleteVoiceRecording:', error);
                handlePipelineError(error.message, 'recording');
            }
        });
    }
    
    if (stopRecordingBtn) {
        stopRecordingBtn.addEventListener('click', () => {
            try {
                stopCompleteVoiceRecording();
            } catch (error) {
                console.error('🤖 Day 23: Error in stopCompleteVoiceRecording:', error);
            }
        });
    }
    
    if (clearChatBtn) {
        clearChatBtn.addEventListener('click', () => {
            try {
                clearCompleteVoiceChatHistory();
            } catch (error) {
                console.error('🤖 Day 23: Error in clearCompleteVoiceChatHistory:', error);
            }
        });
    }
}

function setupMediaRecorderEvents(mediaRecorder, stream) {
    // Clear any existing event listeners
    mediaRecorder.ondataavailable = null;
    mediaRecorder.onstop = null;
    mediaRecorder.onerror = null;
    
    // Event handler for data available - collect chunks
    mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
            llmAudioChunks.push(event.data);
            
            // Stream the chunk if WebSocket is connected
            if (audioWebSocket && audioWebSocket.readyState === WebSocket.OPEN) {
                audioWebSocket.send(event.data);
            }
        }
    };
    
    // Event handler for when recording stops
    mediaRecorder.onstop = async () => {
        try {
            if (audioWebSocket && audioWebSocket.readyState === WebSocket.OPEN) {
                audioWebSocket.send('STOP_RECORDING');
            }
            
            // Stop all tracks in the stream
            stream.getTracks().forEach(track => track.stop());
            
            if (llmStatus) {
                llmStatus.textContent = 'Processing your question...';
            }
            
            // Process the recorded audio
            const voiceId = llmVoiceSelect ? llmVoiceSelect.value : 'en-IN-rohan';
            const audioBlob = new Blob(llmAudioChunks, { type: 'audio/webm;codecs=opus' });
            await processLLMVoiceAgent(audioBlob, voiceId);
            
        } catch (error) {
            console.error('Error in onstop handler:', error);
            if (llmStatus) {
                llmStatus.textContent = `Error: ${error.message}`;
            }
        } finally {
            isStreaming = false;
            setLLMButtonStates(false, true);
        }
    };
    
    // Error handler
    mediaRecorder.onerror = (event) => {
        console.error('MediaRecorder error:', event.error);
        if (llmStatus) {
            llmStatus.textContent = `Recording error: ${event.error.message}`;
        }
        isStreaming = false;
        setLLMButtonStates(false, true);
        
        // Clean up
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
    };
}

// Day 19: Generate TTS for the streaming LLM response
async function generateTTSForResponse(responseText) {
    try {
        console.log('🔊 Generating TTS for response:', responseText.substring(0, 100) + '...');
        
        const voiceId = llmVoiceSelect ? llmVoiceSelect.value : 'en-IN-rohan';
        
        const ttsResponse = await fetch('/tts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: responseText,
                voice_id: voiceId
            })
        });

        if (ttsResponse.ok) {
            const ttsResult = await ttsResponse.json();
            if (ttsResult.audio_url && llmResponseAudio) {
                llmResponseAudio.src = ttsResult.audio_url;
                llmResponseAudio.play().catch(e => console.error('Error playing audio:', e));
                
                if (llmStatus) {
                    llmStatus.textContent = 'Response complete - Playing audio';
                }
            }
        } else {
            console.error('TTS generation failed');
            if (llmStatus) {
                llmStatus.textContent = 'Response complete - TTS failed';
            }
        }
    } catch (error) {
        console.error('Error generating TTS:', error);
        if (llmStatus) {
            llmStatus.textContent = 'Response complete - TTS error';
        }
    }
}

function stopLLMRecording() {
    console.log('🛑 stopLLMRecording called');
    console.log('MediaRecorder state:', llmMediaRecorder?.state);
    console.log('isStreaming flag:', isStreaming);
    
    if (llmMediaRecorder && llmMediaRecorder.state === 'recording') {
        try {
            console.log('Stopping MediaRecorder...');
            // Stop the recording (this will trigger the onstop event)
            llmMediaRecorder.stop();
            console.log('MediaRecorder.stop() called successfully');
            return true;
        } catch (error) {
            console.error('❌ Error stopping recording:', error);
            if (llmStatus) {
                llmStatus.textContent = `Error stopping recording: ${error.message}`;
            }
            isStreaming = false;
            setLLMButtonStates(false, true);
            return false;
        }
    } else {
        console.log('⚠️ MediaRecorder not in recording state or not initialized');
        // Reset states anyway
        isStreaming = false;
        setLLMButtonStates(false, true);
        return false;
    }
}

// Day 27: API Configuration Functions
function initAPIConfiguration() {
    console.log('Initializing API Configuration...');
    
    apiConfigSidebar = document.getElementById('api-config-sidebar');
    if (!apiConfigSidebar) {
        console.error('API config sidebar not found');
        return;
    }
    
    // Initialize API key inputs and status indicators
    const services = ['assemblyai', 'gemini', 'murf', 'tavily', 'openweather', 'news', 'google_translate'];
    services.forEach(service => {
        apiKeyInputs[service] = document.getElementById(`${service}-key`);
        apiStatusIndicators[service] = document.getElementById(`${service}-status`);
        
        if (!apiKeyInputs[service]) {
            console.warn(`API key input for ${service} not found`);
        }
        if (!apiStatusIndicators[service]) {
            console.warn(`Status indicator for ${service} not found`);
        }
    });
    
    // Load current API status
    loadAPIStatus();
    
    // Set up event listeners with error checking
    const configBtn = document.getElementById('config-btn');
    if (configBtn) {
        configBtn.addEventListener('click', (e) => {
            console.log('Config button clicked!');
            e.preventDefault();
            toggleAPIConfig();
        });
        console.log('Config button listener added');
    } else {
        console.error('Config button not found');
    }
    
    const closeBtn = document.getElementById('close-config');
    if (closeBtn) {
        closeBtn.addEventListener('click', closeAPIConfig);
    } else {
        console.warn('Close config button not found');
    }
    
    const saveBtn = document.getElementById('save-config');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveAPIKeys);
    } else {
        console.warn('Save config button not found');
    }
    
    const testBtn = document.getElementById('test-config');
    if (testBtn) {
        testBtn.addEventListener('click', testAPIKeys);
    } else {
        console.warn('Test config button not found');
    }
    
    const clearSessionBtn = document.getElementById('clear-session');
    if (clearSessionBtn) {
        clearSessionBtn.addEventListener('click', clearSessionKeys);
    } else {
        console.warn('Clear session button not found');
    }
    
    const resetBtn = document.getElementById('reset-config');
    if (resetBtn) {
        resetBtn.addEventListener('click', resetAPIKeys);
    } else {
        console.warn('Reset config button not found');
    }
    
    // Theme toggle (placeholder for future implementation)
    const themeBtn = document.getElementById('theme-toggle');
    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            console.log('Theme toggle clicked - feature coming soon!');
        });
    } else {
        console.warn('Theme toggle button not found');
    }
}

function toggleAPIConfig() {
    console.log('toggleAPIConfig called');
    console.log('apiConfigSidebar:', apiConfigSidebar);
    
    if (apiConfigSidebar.classList.contains('open')) {
        console.log('Closing sidebar');
        closeAPIConfig();
    } else {
        console.log('Opening sidebar');
        openAPIConfig();
    }
}

function openAPIConfig() {
    console.log('Opening API config sidebar');
    console.log('Sidebar element:', apiConfigSidebar);
    apiConfigSidebar.classList.add('open');
    console.log('Added open class, current classes:', apiConfigSidebar.className);
    loadAPIStatus(); // Refresh status when opening
}

function closeAPIConfig() {
    apiConfigSidebar.classList.remove('open');
}

async function loadAPIStatus() {
    try {
        console.log('Loading API status...');
        const response = await fetch(`/api/config/status?session_id=${sessionId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const status = await response.json();
        console.log('API Status Response:', status);
        
        // Define the mapping between service names in the UI and backend
        const serviceMap = {
            'assemblyai': 'assemblyai',
            'murf': 'murf',
            'gemini': 'gemini',
            'tavily': 'tavily',
            'openweather': 'openweather',
            'news': 'news',
            'google_translate': 'google_translate'
        };
        
        // Update status indicators and skills overview
        Object.entries(serviceMap).forEach(([uiService, backendService]) => {
            const serviceInfo = status[backendService] || { configured: false, source: 'missing' };
            const indicator = document.getElementById(`${uiService}-status`);
            const inputElement = document.getElementById(`${uiService}-key`);
            
            console.log(`Processing ${uiService} (backend: ${backendService}):`, serviceInfo);
            
            // Update status indicator
            if (indicator) {
                // Clear existing classes
                indicator.className = 'status-indicator';
                
                // Update status based on configuration
                if (serviceInfo.configured) {
                    indicator.classList.add('configured');
                    indicator.title = 'API key is configured';
                    console.log(`✅ ${uiService} is configured`);
                } else {
                    indicator.classList.add('missing');
                    indicator.title = 'API key not configured';
                    console.log(`❌ ${uiService} is missing`);
                    
                    // Clear any saved key from the input for security
                    if (inputElement) {
                        inputElement.value = '';
                    }
                }
            }
            
            // Update input field with current key if it exists
            if (inputElement && serviceInfo.configured) {
                // Get the key from the server response if available
                const currentKey = serviceInfo.api_key || '';
                if (currentKey) {
                    // Show first 4 and last 4 characters of the key for security
                    const displayKey = currentKey.length > 8 
                        ? `${currentKey.substring(0, 4)}...${currentKey.substring(currentKey.length - 4)}`
                        : '********';
                    inputElement.value = displayKey;
                    // Keep input type as password for security
                }
            }
        });
        
        // Update skill card statuses
        updateSkillCardStatuses(status);
        
        // Run initial test of API keys to validate them
        await testAPIKeys();
        
        console.log('API status loaded successfully');
        
    } catch (error) {
        console.error('Error loading API status:', error);
        showNotification(`Error loading API status: ${error.message}`, 'error');
    }
}

async function saveAPIKeys() {
    const apiKeys = {};
    let hasKeys = false;
    
    // Collect all non-empty API keys
    Object.entries(apiKeyInputs).forEach(([service, input]) => {
        if (input && input.value.trim()) {
            apiKeys[service] = input.value.trim();
            hasKeys = true;
        }
    });
    
    if (!hasKeys) {
        showNotification('Please enter at least one API key', 'warning');
        return;
    }
    
    console.log('Saving API keys:', Object.keys(apiKeys));
    
    try {
        let successCount = 0;
        let errorCount = 0;
        
        // Save each API key individually
        for (const [service, apiKey] of Object.entries(apiKeys)) {
            try {
                const response = await fetch(`/api/config/key?session_id=${sessionId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ 
                        service: service.toUpperCase(), 
                        api_key: apiKey 
                    })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    if (result.success) {
                        console.log(`✅ ${service} API key saved successfully`);
                        successCount++;
                    } else {
                        console.error(`❌ Failed to save ${service} API key:`, result);
                        showNotification(`${service}: ${result.message || 'Save failed'}`, 'error');
                        errorCount++;
                    }
                } else {
                    // Handle HTTP error responses (like 400 for validation errors)
                    const errorResult = await response.json();
                    const errorMessage = errorResult.detail || `HTTP ${response.status} error`;
                    console.error(`❌ Validation error for ${service}:`, errorMessage);
                    showNotification(`${service}: ${errorMessage}`, 'error');
                    errorCount++;
                }
            } catch (error) {
                console.error(`❌ Network error saving ${service} API key:`, error);
                showNotification(`${service}: Network error`, 'error');
                errorCount++;
            }
        }
        
        // Also handle clearing empty keys (when user clears a field)
        const allServices = ['assemblyai', 'murf', 'gemini', 'tavily', 'openweather', 'news', 'google_translate'];
        for (const service of allServices) {
            const input = apiKeyInputs[service];
            if (input && !input.value.trim() && input.dataset.hadValue === 'true') {
                // This field was cleared, send empty key to remove it
                try {
                    const response = await fetch(`/api/config/key?session_id=${sessionId}`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ 
                            service: service.toUpperCase(), 
                            api_key: '' 
                        })
                    });
                    
                    const result = await response.json();
                    if (result.success) {
                        console.log(`🗑️ ${service} API key cleared successfully`);
                        input.dataset.hadValue = 'false';
                    }
                } catch (error) {
                    console.error(`❌ Error clearing ${service} API key:`, error);
                }
            } else if (input && input.value.trim()) {
                input.dataset.hadValue = 'true';
            }
        }
        
        // Show summary message
        if (successCount > 0) {
            showNotification(`Successfully saved ${successCount} API key(s)`, 'success');
            // Refresh the API status display and skill cards
            await loadAPIStatus();
        }
        
        // Don't show generic error count since specific errors are already shown above
        
    } catch (error) {
        console.error('Error saving API keys:', error);
        showNotification('Error saving API keys', 'error');
    }
}

async function testAPIKeys() {
    const testBtn = document.getElementById('test-config');
    const originalText = testBtn.innerHTML;
    testBtn.disabled = true;
    testBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
    
    showNotification('Testing API keys...', 'info');
    
    try {
        const response = await fetch(`/api/config/test?session_id=${sessionId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const results = await response.json();
        
        // Update UI with test results
        Object.entries(results).forEach(([service, info]) => {
            const statusElement = document.getElementById(`${service}-status`);
            if (statusElement) {
                // Clear existing classes
                statusElement.className = 'status-indicator';
                
                // Add status class
                if (info.status === 'valid') {
                    statusElement.classList.add('configured');
                    statusElement.title = info.message || 'API key is valid';
                } else if (info.status === 'error') {
                    statusElement.classList.add('error');
                    statusElement.title = info.message || 'API key validation failed';
                } else {
                    statusElement.classList.add('missing');
                    statusElement.title = info.message || 'API key not configured';
                }
                
                // Update skill cards
                const skillCard = document.querySelector(`.skill-card[data-service="${service}"]`);
                if (skillCard) {
                    skillCard.classList.remove('configured', 'error', 'missing');
                    skillCard.classList.add(info.status || 'missing');
                    
                    const statusBadge = skillCard.querySelector('.skill-status');
                    if (statusBadge) {
                        statusBadge.textContent = info.status === 'valid' ? '✓ Configured' : 
                                               info.status === 'error' ? '✗ Error' : '⚠ Missing';
                    }
                }
            }
        });
        
        // Show summary notification
        const validCount = Object.values(results).filter(r => r.status === 'valid').length;
        const total = Object.keys(results).length;
        showNotification(`Test complete: ${validCount} of ${total} services configured successfully`, 
                       validCount === total ? 'success' : validCount > 0 ? 'warning' : 'error');
        
    } catch (error) {
        console.error('Error testing API keys:', error);
        showNotification(`Error testing API keys: ${error.message}`, 'error');
    } finally {
        testBtn.disabled = false;
        testBtn.innerHTML = originalText;
    }
}

function resetAPIKeys() {
    if (confirm('Are you sure you want to clear all API key inputs?')) {
        Object.values(apiKeyInputs).forEach(input => {
            if (input) input.value = '';
        });
        showNotification('API key inputs cleared', 'info');
    }
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas ${getNotificationIcon(type)}"></i>
            <span>${message}</span>
        </div>
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Show notification
    setTimeout(() => notification.classList.add('show'), 100);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

function getNotificationIcon(type) {
    switch (type) {
        case 'success': return 'fa-check-circle';
        case 'error': return 'fa-exclamation-circle';
        case 'warning': return 'fa-exclamation-triangle';
        default: return 'fa-info-circle';
    }
}

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', () => {
    // Detect mobile device
    isMobile = isMobileDevice();
    console.log('Mobile device detected:', isMobile);
    
    // Initialize mobile-specific features
    if (isMobile) {
        initMobileAudioContext();
        
        // Add mobile-specific viewport handling
        const viewport = document.querySelector('meta[name="viewport"]');
        if (viewport) {
            viewport.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no');
        }
        
        // Prevent zoom on input focus for iOS
        document.addEventListener('touchstart', () => {}, { passive: true });
    }
    
    // Initialize LLM app
    initApp();
    
    // Initialize Day 27: API Configuration
    initAPIConfiguration();
});

function updateSkillCardStatuses(apiStatus) {
    console.log('Updating skill card statuses with:', apiStatus);
    
    // Map skill cards to their corresponding API services
    const skillToServiceMap = {
        'search': 'tavily',
        'weather': 'openweather', 
        'news': 'news',
        'translate': 'google_translate'
    };
    
    // Update each skill card
    Object.entries(skillToServiceMap).forEach(([skillName, serviceName]) => {
        const skillCard = document.querySelector(`[data-skill="${skillName}"]`);
        if (!skillCard) {
            console.warn(`Skill card not found for: ${skillName}`);
            return;
        }
        
        const statusElement = skillCard.querySelector('.skill-status span');
        if (!statusElement) {
            console.warn(`Status element not found for skill: ${skillName}`);
            return;
        }
        
        const serviceStatus = apiStatus[serviceName];
        console.log(`🔍 Checking ${skillName} -> ${serviceName}:`, serviceStatus);
        
        // Always reset all classes first
        skillCard.classList.remove('configured', 'error', 'missing');
        statusElement.className = '';
        
        if (serviceStatus && serviceStatus.configured) {
            statusElement.textContent = 'Configured';
            statusElement.className = 'configured';
            skillCard.classList.add('configured');
            console.log(`✅ ${skillName} skill marked as configured`);
        } else {
            statusElement.textContent = 'Not Configured';
            statusElement.className = 'not-configured';
            skillCard.classList.add('missing');
            console.log(`❌ ${skillName} skill marked as not configured`);
        }
    });
}
