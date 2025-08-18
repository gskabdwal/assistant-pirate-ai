// Global variables
let sessionId;
let isAutoRecordingEnabled = false;
let llmMediaRecorder;
let llmAudioChunks = [];
let audioWebSocket;
let isStreaming = false;

// Streaming transcription variables
let transcribeWebSocket;
let streamMediaRecorder;
let isTranscribing = false;

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

// Streaming transcription DOM elements
let startStreamRecordingBtn;
let stopStreamRecordingBtn;
let streamStatus;
let partialTranscript;
let finalTranscript;

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

// Streaming Transcription Functions
function connectTranscribeWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/transcribe-stream`;
    
    transcribeWebSocket = new WebSocket(wsUrl);
    
    transcribeWebSocket.onopen = () => {
        console.log('Transcription WebSocket connected');
        if (streamStatus) {
            streamStatus.textContent = 'Connected - Ready for real-time transcription';
        }
    };
    
    transcribeWebSocket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log('Transcription message:', data);
            
            if (data.type === 'turn_transcript') {
                if (data.end_of_turn) {
                    // Final transcript - move to final display
                    if (finalTranscript) {
                        finalTranscript.textContent = data.text || 'No speech detected';
                    }
                    if (partialTranscript) {
                        partialTranscript.textContent = 'Listening...';
                    }
                } else {
                    // Partial transcript - show in partial display
                    if (partialTranscript) {
                        partialTranscript.textContent = data.text || 'Listening...';
                    }
                }
            } else if (data.error) {
                if (streamStatus) {
                    streamStatus.textContent = `Error: ${data.error}`;
                }
            } else if (data.status) {
                if (streamStatus) {
                    streamStatus.textContent = data.message || data.status;
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

async function startStreamRecording() {
    if (streamStatus) {
        streamStatus.textContent = 'Preparing to start real-time transcription...';
    }
    
    try {
        // Connect WebSocket if not connected
        if (!transcribeWebSocket || transcribeWebSocket.readyState !== WebSocket.OPEN) {
            connectTranscribeWebSocket();
            // Wait for connection
            await new Promise((resolve, reject) => {
                const timeout = setTimeout(() => reject(new Error('WebSocket connection timeout')), 5000);
                transcribeWebSocket.onopen = () => {
                    clearTimeout(timeout);
                    resolve();
                };
                transcribeWebSocket.onerror = () => {
                    clearTimeout(timeout);
                    reject(new Error('WebSocket connection failed'));
                };
            });
        }
        
        // Send start command
        transcribeWebSocket.send('START_TRANSCRIPTION');
        
        // Request microphone access with specific constraints for AssemblyAI
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                sampleRate: 16000,
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true
            }
        });
        
        // Use Web Audio API to get raw PCM data for AssemblyAI
        const audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: 16000
        });
        const source = audioContext.createMediaStreamSource(stream);
        const processor = audioContext.createScriptProcessor(4096, 1, 1);
        
        processor.onaudioprocess = (event) => {
            if (transcribeWebSocket && transcribeWebSocket.readyState === WebSocket.OPEN) {
                const inputBuffer = event.inputBuffer;
                const inputData = inputBuffer.getChannelData(0);
                
                // Convert float32 to int16 PCM
                const pcmData = new Int16Array(inputData.length);
                for (let i = 0; i < inputData.length; i++) {
                    pcmData[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
                }
                
                // Send PCM data as ArrayBuffer
                transcribeWebSocket.send(pcmData.buffer);
            }
        };
        
        source.connect(processor);
        processor.connect(audioContext.destination);
        
        // Store references for cleanup
        streamMediaRecorder = {
            audioContext,
            source,
            processor,
            stream,
            start: () => {
                // Audio processing starts immediately when connected
                console.log('Audio processing started');
            },
            stop: () => {
                processor.disconnect();
                source.disconnect();
                audioContext.close();
                stream.getTracks().forEach(track => track.stop());
            }
        };
        
        streamMediaRecorder.onstop = async () => {
            if (transcribeWebSocket && transcribeWebSocket.readyState === WebSocket.OPEN) {
                transcribeWebSocket.send('STOP_TRANSCRIPTION');
            }
            
            // Stop all tracks
            stream.getTracks().forEach(track => track.stop());
            
            if (streamStatus) {
                streamStatus.textContent = 'Transcription stopped';
            }
            
            isTranscribing = false;
            setStreamButtonStates(false, true);
        };
        
        // Start recording with short time slices for real-time streaming
        streamMediaRecorder.start(100);
        isTranscribing = true;
        
        // Update UI
        setStreamButtonStates(true, false);
        if (streamStatus) {
            streamStatus.textContent = 'Streaming audio for real-time transcription...';
        }
        
        // Clear previous transcripts
        if (partialTranscript) {
            partialTranscript.textContent = 'Listening...';
        }
        if (finalTranscript) {
            finalTranscript.textContent = 'Waiting for speech...';
        }
        
    } catch (error) {
        console.error('Error starting stream recording:', error);
        if (streamStatus) {
            streamStatus.textContent = 'Error: ' + (error.message || 'Could not start transcription');
        }
        setStreamButtonStates(false, true);
        isTranscribing = false;
    }
}

function stopStreamRecording() {
    if (streamMediaRecorder && streamMediaRecorder.state === 'recording') {
        streamMediaRecorder.stop();
    }
    
    if (streamStatus) {
        streamStatus.textContent = 'Stopping transcription...';
    }
}

function setStreamButtonStates(startDisabled, stopDisabled) {
    if (startStreamRecordingBtn) {
        startStreamRecordingBtn.disabled = startDisabled;
    }
    if (stopStreamRecordingBtn) {
        stopStreamRecordingBtn.disabled = stopDisabled;
    }
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
    
    // Initialize streaming transcription DOM elements
    startStreamRecordingBtn = document.getElementById('startStreamRecording');
    stopStreamRecordingBtn = document.getElementById('stopStreamRecording');
    streamStatus = document.getElementById('streamStatus');
    partialTranscript = document.getElementById('partialTranscript');
    finalTranscript = document.getElementById('finalTranscript');
    
    // Setup event listeners
    setupEventListeners();
    
    // Set initial button states
    setLLMButtonStates(false, true);
    setStreamButtonStates(false, true);
    
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
    
    // Streaming transcription event listeners
    if (startStreamRecordingBtn) {
        startStreamRecordingBtn.addEventListener('click', startStreamRecording);
    }
    
    if (stopStreamRecordingBtn) {
        stopStreamRecordingBtn.addEventListener('click', stopStreamRecording);
    }
}

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize LLM app
    initApp();
});
