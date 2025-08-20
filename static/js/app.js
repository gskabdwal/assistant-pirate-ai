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
let llmStreamingText;

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
    console.log('Setting LLM buttons - startDisabled:', startDisabled, 'stopDisabled:', stopDisabled);
    if (startLLMRecordingBtn) {
        startLLMRecordingBtn.disabled = startDisabled;
    } else {
        console.error('startLLMRecordingBtn not found');
    }
    if (stopLLMRecordingBtn) {
        stopLLMRecordingBtn.disabled = stopDisabled;
    } else {
        console.error('stopLLMRecordingBtn not found');
    }
}

// Streaming button state management
function setStreamButtonStates(startDisabled, stopDisabled) {
    console.log('Setting Stream buttons - startDisabled:', startDisabled, 'stopDisabled:', stopDisabled);
    if (startStreamRecordingBtn) {
        startStreamRecordingBtn.disabled = startDisabled;
    } else {
        console.error('startStreamRecordingBtn not found');
    }
    if (stopStreamRecordingBtn) {
        stopStreamRecordingBtn.disabled = stopDisabled;
    } else {
        console.error('stopStreamRecordingBtn not found');
    }
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

async function startStreamRecording() {
    // Reset any previous state
    if (isTranscribing) {
        await stopStreamRecording();
    }
    
    // Reset UI
    if (streamStatus) {
        streamStatus.textContent = 'Preparing to start real-time transcription...';
        streamStatus.className = '';
    }
    
    if (partialTranscript) {
        partialTranscript.textContent = 'Listening...';
        partialTranscript.className = '';
    }
    
    if (finalTranscript) {
        finalTranscript.textContent = 'Waiting for speech...';
        finalTranscript.className = '';
    }
    
    try {
        // Close any existing WebSocket connection
        if (transcribeWebSocket) {
            transcribeWebSocket.close();
        }
        
        // Create new WebSocket connection
        connectTranscribeWebSocket();
        
        // Wait for connection with timeout
        await new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('WebSocket connection timeout'));
            }, 5000);
            
            const onOpen = () => {
                clearTimeout(timeout);
                transcribeWebSocket.removeEventListener('open', onOpen);
                transcribeWebSocket.removeEventListener('error', onError);
                resolve();
            };
            
            const onError = (error) => {
                clearTimeout(timeout);
                transcribeWebSocket.removeEventListener('open', onOpen);
                transcribeWebSocket.removeEventListener('error', onError);
                reject(new Error('WebSocket connection failed'));
            };
            
            transcribeWebSocket.addEventListener('open', onOpen);
            transcribeWebSocket.addEventListener('error', onError);
        });
        
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
    // Stop the media recorder if it's active
    if (streamMediaRecorder && streamMediaRecorder.state === 'recording') {
        streamMediaRecorder.stop();
        
        // Stop all tracks in the stream
        if (streamMediaRecorder.stream) {
            streamMediaRecorder.stream.getTracks().forEach(track => track.stop());
        }
    }
    
    // Send stop command to the WebSocket if connected
    if (transcribeWebSocket && transcribeWebSocket.readyState === WebSocket.OPEN) {
        transcribeWebSocket.send('STOP_TRANSCRIPTION');
    }
    
    // Reset UI state
    if (streamStatus) {
        streamStatus.textContent = 'Transcription stopped';
        streamStatus.className = ''; // Remove any status classes
    }
    
    // Reset transcription displays
    if (partialTranscript) {
        partialTranscript.textContent = 'Start a new transcription to begin...';
        partialTranscript.className = '';
    }
    
    if (finalTranscript) {
        finalTranscript.className = '';
    }
    
    // Reset button states
    setStreamButtonStates(false, true);
    
    // Close the WebSocket connection
    if (transcribeWebSocket) {
        transcribeWebSocket.close();
        transcribeWebSocket = null;
    }
    
    // Reset the flag
    isTranscribing = false;
}

// Connect to LLM WebSocket
function connectLLMWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/llm-stream`;
    
    llmWebSocket = new WebSocket(wsUrl);
    
    llmWebSocket.onopen = () => {
        console.log('LLM WebSocket connected');
        isLLMStreaming = true;
    };
    
    llmWebSocket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log('🔄 LLM WebSocket message:', data); // Day 19: Log streaming responses
            
            // Handle different message types for Day 19 streaming
            if (data.type === 'start') {
                console.log('🚀 LLM streaming started');
                if (llmStatus) {
                    llmStatus.textContent = 'AI is thinking...';
                }
                // Clear previous responses
                const streamingText = document.getElementById('llmStreamingText');
                const responseText = document.getElementById('llmResponseText');
                if (streamingText) streamingText.textContent = '';
                if (responseText) responseText.textContent = '';
            }
            else if (data.type === 'chunk') {
                // Day 19: Handle streaming chunks
                console.log('📝 Streaming chunk:', data.text);
                const streamingText = document.getElementById('llmStreamingText');
                if (streamingText) {
                    streamingText.textContent += data.text || '';
                    streamingText.scrollTop = streamingText.scrollHeight;
                }
                if (llmStatus) {
                    llmStatus.textContent = 'AI is responding...';
                }
            }
            else if (data.type === 'end') {
                // Day 19: Handle end of streaming
                console.log('✅ LLM streaming completed. Full response:', data.text);
                const streamingText = document.getElementById('llmStreamingText');
                const responseText = document.getElementById('llmResponseText');
                
                if (streamingText && responseText) {
                    // Move final response to response text area
                    responseText.textContent = data.text || streamingText.textContent;
                    streamingText.textContent = '';
                    responseText.scrollTop = responseText.scrollHeight;
                }
                
                if (llmStatus) {
                    llmStatus.textContent = 'Generating voice response...';
                }
                
                // Generate TTS for the complete response
                if (data.text) {
                    generateTTSForResponse(data.text);
                }
            }
            else if (data.type === 'error') {
                console.error('❌ LLM WebSocket error:', data.message);
                if (llmStatus) {
                    llmStatus.textContent = `Error: ${data.message || 'Unknown error occurred'}`;
                }
            }
        } catch (error) {
            console.error('Error processing WebSocket message:', error);
        }
    };
    
    llmWebSocket.onclose = () => {
        console.log('LLM WebSocket disconnected');
        isLLMStreaming = false;
    };
    
    llmWebSocket.onerror = (error) => {
        console.error('LLM WebSocket error:', error);
        isLLMStreaming = false;
    };
}

async function startLLMRecording() {
    console.log('startLLMRecording called');
    
    // Prevent multiple recordings
    if (isStreaming) {
        console.log('Recording already in progress');
        return;
    }

    try {
        if (llmStatus) {
            llmStatus.textContent = 'Requesting microphone access...';
        }
        
        console.log('Requesting microphone access...');
    
        // First, request microphone access
        const constraints = {
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                sampleRate: 16000
            },
            video: false
        };
        
        console.log('Requesting media with constraints:', constraints);
        
        const stream = await navigator.mediaDevices.getUserMedia(constraints)
            .catch(error => {
                console.error('Error getting user media:', error);
                throw new Error(`Could not access microphone: ${error.message}`);
            });
            
        console.log('Microphone access granted, stream active:', stream.active);
        
        // Update status to show we're connecting to WebSocket
        if (llmStatus) {
            llmStatus.textContent = 'Connecting to server...';
        }
        
        console.log('Checking WebSocket connection...');
        
        // Connect WebSocket if not connected
        if (!audioWebSocket || audioWebSocket.readyState !== WebSocket.OPEN) {
            console.log('WebSocket not connected, connecting...');
            connectAudioWebSocket();
            
            // Wait for connection with a timeout
            await new Promise((resolve, reject) => {
                const timeout = setTimeout(() => {
                    console.error('WebSocket connection timeout');
                    reject(new Error('Connection to server timed out'));
                }, 5000);
                
                const checkConnection = () => {
                    console.log('WebSocket state:', audioWebSocket ? audioWebSocket.readyState : 'not initialized');
                    
                    if (audioWebSocket && audioWebSocket.readyState === WebSocket.OPEN) {
                        console.log('WebSocket connected successfully');
                        clearTimeout(timeout);
                        resolve();
                    } else if (!audioWebSocket || 
                              audioWebSocket.readyState === WebSocket.CLOSED || 
                              audioWebSocket.readyState === WebSocket.CLOSING) {
                        console.error('WebSocket connection failed');
                        clearTimeout(timeout);
                        reject(new Error('Failed to connect to server'));
                    } else {
                        setTimeout(checkConnection, 100);
                    }
                };
                
                checkConnection();
            });
        } else {
            console.log('WebSocket already connected');
        }
        
        // Clear previous audio chunks
        llmAudioChunks = [];
        
        // Create media recorder with shorter time slices for streaming
        llmMediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm;codecs=opus',
            audioBitsPerSecond: 128000 // 128kbps
        });
        
        // Set up event handlers before starting
        setupMediaRecorderEvents(llmMediaRecorder, stream);
        
        // Send start recording command
        audioWebSocket.send('START_RECORDING');
        
        // Start recording with 100ms chunks
        llmMediaRecorder.start(100);
        isStreaming = true;
        
        // Update UI
        setLLMButtonStates(true, false);
        if (llmStatus) {
            llmStatus.textContent = 'Listening... Click Stop when done';
        }
        
        console.log('✅ Recording started successfully');
        console.log('Button states after start - Start disabled:', startLLMRecordingBtn?.disabled, 'Stop disabled:', stopLLMRecordingBtn?.disabled);
        console.log('MediaRecorder state:', llmMediaRecorder?.state);
        console.log('isStreaming flag:', isStreaming);
        
    } catch (error) {
        console.error('❌ Error in startLLMRecording:', error);
        console.log('Error occurred, resetting button states');
        if (llmStatus) {
            llmStatus.textContent = 'Error: ' + (error.message || 'Could not start audio streaming');
        }
        setLLMButtonStates(false, true);
        isStreaming = false;
        
        // Clean up stream if it was created
        if (typeof stream !== 'undefined' && stream) {
            stream.getTracks().forEach(track => track.stop());
        }
        
        // Don't re-throw the error to prevent further issues
        console.log('Error handled, not re-throwing');
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

// Initialize the application
function initApp() {
    try {
        console.log('Initializing application...');
        
        // Initialize session
        sessionId = getOrCreateSessionId();
        console.log('Session ID:', sessionId);
        
        // Initialize DOM elements
        console.log('Initializing DOM elements...');
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
            llmVoiceSelect: !!llmVoiceSelect
        });
        
        // Set initial button states
        setLLMButtonStates(false, true);
        setStreamButtonStates(false, true);
        
        // Set up event listeners
        setupEventListeners();
        
        // Initialize WebSocket connections after a short delay
        setTimeout(() => {
            console.log('Initializing WebSocket connections...');
            connectAudioWebSocket();
            connectTranscribeWebSocket();
            connectLLMWebSocket();
        }, 500);
        
        console.log('Application initialization complete');
        
    } catch (error) {
        console.error('Error initializing application:', error);
        if (llmStatus) {
            llmStatus.textContent = `Initialization error: ${error.message}`;
        }
    }
}

// Set up all event listeners
function setupEventListeners() {
    if (startLLMRecordingBtn) {
        startLLMRecordingBtn.addEventListener('click', async (e) => {
            try {
                await startLLMRecording();
            } catch (error) {
                console.error('Error in startLLMRecording:', error);
                if (llmStatus) {
                    llmStatus.textContent = `Error: ${error.message}`;
                }
            }
        });
    }
    
    if (stopLLMRecordingBtn) {
        stopLLMRecordingBtn.addEventListener('click', () => {
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
        startStreamRecordingBtn.addEventListener('click', async (e) => {
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

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize LLM app
    initApp();
});
