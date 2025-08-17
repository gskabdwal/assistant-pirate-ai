// Global variables
let sessionId;
let isAutoRecordingEnabled = false;
let llmMediaRecorder;
let llmAudioChunks = [];
let audioWebSocket;
let isStreaming = false;

// DOM Elements
let startLLMRecordingBtn;
let stopLLMRecordingBtn;
let llmStatus;
let llmChatHistory;
let llmTranscriptionText;
let llmResponseText;
let llmQuestionAudio;
let llmResponseAudio;
let llmVoiceSelect;

// Session management functions
function getOrCreateSessionId() {
    const urlParams = new URLSearchParams(window.location.search);
    let sessionId = urlParams.get('session_id');
    
    if (!sessionId) {
        sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        const newUrl = new URL(window.location);
        newUrl.searchParams.set('session_id', sessionId);
        window.history.replaceState({}, '', newUrl);
    }
    
    return sessionId;
}

// Button state management
function setLLMButtonStates(startDisabled, stopDisabled) {
    if (startLLMRecordingBtn) {
        startLLMRecordingBtn.disabled = startDisabled;
    }
    if (stopLLMRecordingBtn) {
        stopLLMRecordingBtn.disabled = stopDisabled;
    }
}

// WebSocket connection functions
function connectAudioWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/audio-stream`;
    
    audioWebSocket = new WebSocket(wsUrl);
    
    audioWebSocket.onopen = () => {
        console.log('Audio WebSocket connected');
        if (llmStatus) {
            llmStatus.textContent = 'WebSocket connected - Ready to stream';
        }
    };
    
    audioWebSocket.onmessage = (event) => {
        console.log('WebSocket message:', event.data);
        if (llmStatus) {
            llmStatus.textContent = event.data;
        }
    };
    
    audioWebSocket.onclose = () => {
        console.log('Audio WebSocket disconnected');
        if (llmStatus) {
            llmStatus.textContent = 'WebSocket disconnected';
        }
        isStreaming = false;
    };
    
    audioWebSocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        if (llmStatus) {
            llmStatus.textContent = 'WebSocket error';
        }
        isStreaming = false;
    };
}

// Streaming Recording Functions
async function startLLMRecording() {
    if (llmStatus) {
        llmStatus.textContent = 'Preparing to stream audio...';
    }
    
    try {
        // Connect WebSocket if not connected
        if (!audioWebSocket || audioWebSocket.readyState !== WebSocket.OPEN) {
            connectAudioWebSocket();
            // Wait for connection
            await new Promise((resolve, reject) => {
                const timeout = setTimeout(() => reject(new Error('WebSocket connection timeout')), 5000);
                audioWebSocket.onopen = () => {
                    clearTimeout(timeout);
                    resolve();
                };
                audioWebSocket.onerror = () => {
                    clearTimeout(timeout);
                    reject(new Error('WebSocket connection failed'));
                };
            });
        }
        
        // Send start recording command
        audioWebSocket.send('START_RECORDING');
        
        // Request microphone access
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        // Create media recorder with shorter time slices for streaming
        llmMediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm;codecs=opus'
        });
        
        // Event handlers for data available - stream chunks immediately
        llmMediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0 && audioWebSocket && audioWebSocket.readyState === WebSocket.OPEN) {
                // Convert blob to array buffer and send via WebSocket
                event.data.arrayBuffer().then(buffer => {
                    audioWebSocket.send(buffer);
                });
            }
        };
        
        // Event handler for when recording stops
        llmMediaRecorder.onstop = async () => {
            if (audioWebSocket && audioWebSocket.readyState === WebSocket.OPEN) {
                audioWebSocket.send('STOP_RECORDING');
            }
            
            // Stop all tracks in the stream
            stream.getTracks().forEach(track => track.stop());
            
            if (llmStatus) {
                llmStatus.textContent = 'Audio streaming completed';
            }
            
            isStreaming = false;
        };
        
        // Start recording with time slices for streaming (100ms chunks)
        llmMediaRecorder.start(100);
        isStreaming = true;
        
        // Update UI
        setLLMButtonStates(true, false);
        if (llmStatus) {
            llmStatus.textContent = 'Streaming audio... Click Stop when done';
        }
        
    } catch (error) {
        if (llmStatus) {
            llmStatus.textContent = 'Error: ' + (error.message || 'Could not start audio streaming');
        }
        setLLMButtonStates(false, true);
        isStreaming = false;
        throw error;
    }
}

function stopLLMRecording() {
    if (llmMediaRecorder && llmMediaRecorder.state === 'recording') {
        llmMediaRecorder.stop();
    }
    
    setLLMButtonStates(false, true);
    
    if (llmStatus) {
        llmStatus.textContent = 'Stopping audio stream...';
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

// Initialize the application
function initApp() {
    // Initialize session
    sessionId = getOrCreateSessionId();
    
    // Initialize DOM elements
    startLLMRecordingBtn = document.getElementById('startLLMRecording');
    stopLLMRecordingBtn = document.getElementById('stopLLMRecording');
    llmStatus = document.getElementById('llmStatus');
    llmChatHistory = document.getElementById('llmChatHistory');
    llmTranscriptionText = document.getElementById('llmTranscriptionText');
    llmResponseText = document.getElementById('llmResponseText');
    llmQuestionAudio = document.getElementById('llmQuestionAudio');
    llmResponseAudio = document.getElementById('llmResponseAudio');
    llmVoiceSelect = document.getElementById('llmVoiceSelect');
    
    // Setup event listeners
    setupEventListeners();
    
    // Set initial button states
    setLLMButtonStates(false, true);
    
    // Connect WebSocket for audio streaming
    connectAudioWebSocket();
}

// Set up all event listeners
function setupEventListeners() {
    if (startLLMRecordingBtn) {
        startLLMRecordingBtn.addEventListener('click', startLLMRecording);
    }
    
    if (stopLLMRecordingBtn) {
        stopLLMRecordingBtn.addEventListener('click', stopLLMRecording);
    }
}

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize LLM app
    initApp();
});
