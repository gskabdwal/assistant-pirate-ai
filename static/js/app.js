// Global variables
let sessionId;
let isAutoRecordingEnabled = false;
let llmMediaRecorder;
let llmAudioChunks = [];

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

// LLM Recording Functions
async function startLLMRecording() {
    if (llmStatus) {
        llmStatus.textContent = 'Preparing to record...';
    }
    
    try {
        // Clear previous recording chunks
        llmAudioChunks = [];
        
        // Request microphone access
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        // Create media recorder
        llmMediaRecorder = new MediaRecorder(stream);
        
        // Event handlers for data available
        llmMediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                llmAudioChunks.push(event.data);
            }
        };
        
        // Event handler for when recording stops
        llmMediaRecorder.onstop = async () => {
            if (llmStatus) {
                llmStatus.textContent = 'Processing your question...';
            }
            
            // Create audio blob
            const audioBlob = new Blob(llmAudioChunks, { type: 'audio/wav' });
            
            // Create form data
            const formData = new FormData();
            formData.append('file', audioBlob, 'recording.wav');
            formData.append('voice_id', llmVoiceSelect ? llmVoiceSelect.value : 'en-US-natalie');
            
            // Call the API
            try {
                const response = await fetch(`/agent/chat/${sessionId}`, {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                
                // Update UI with response
                if (llmTranscriptionText) {
                    llmTranscriptionText.textContent = data.transcription || 'No transcription available';
                }
                
                if (llmResponseText) {
                    llmResponseText.textContent = data.response || 'No response available';
                }
                
                // Play the response audio if available
                if (data.audio_url && llmResponseAudio) {
                    llmResponseAudio.src = data.audio_url;
                    llmResponseAudio.play().catch(e => {});
                }
                
                // Update chat history if available
                if (data.recent_messages && llmChatHistory) {
                    updateChatHistory(data.recent_messages);
                }
                
                if (llmStatus) {
                    llmStatus.textContent = 'Ready';
                }
                
            } catch (error) {
                if (llmStatus) {
                    llmStatus.textContent = 'Error: ' + (error.message || 'Failed to process recording');
                }
            }
            
            // Re-enable auto-recording if enabled
            if (isAutoRecordingEnabled) {
                setTimeout(() => {
                    if (startLLMRecordingBtn && !startLLMRecordingBtn.disabled) {
                        startLLMRecordingBtn.click();
                    }
                }, 1000);
            }
        };
        
        // Start recording
        llmMediaRecorder.start();
        
        // Update UI
        setLLMButtonStates(true, false);
        if (llmStatus) {
            llmStatus.textContent = 'Recording... Click Stop when done';
        }
        
    } catch (error) {
        if (llmStatus) {
            llmStatus.textContent = 'Error: Could not access microphone. Please check permissions.';
        }
        setLLMButtonStates(false, true);
        throw error;
    }
}

function stopLLMRecording() {
    if (llmMediaRecorder && llmMediaRecorder.state === 'recording') {
        llmMediaRecorder.stop();
    }
    // Stop all tracks in the stream
    if (llmMediaRecorder.stream) {
        llmMediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
    
    setLLMButtonStates(false, true);
    
    if (llmStatus) {
        llmStatus.textContent = 'Processing your question...';
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
