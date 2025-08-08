document.addEventListener('DOMContentLoaded', () => {
    // TTS Elements
    const ttsText = document.getElementById('ttsText');
    const voiceSelect = document.getElementById('voiceSelect');
    const ttsSubmitBtn = document.getElementById('ttsSubmitBtn');
    const ttsAudio = document.getElementById('ttsAudio');
    const ttsStatus = document.getElementById('ttsStatus');
    
    // Echo Bot Elements
    const startRecordingBtn = document.getElementById('startRecording');
    const stopRecordingBtn = document.getElementById('stopRecording');
    const echoAudio = document.getElementById('echoAudio');
    const echoTTSAudio = document.getElementById('echoTTSAudio');
    const recordingStatus = document.getElementById('recordingStatus');
    const uploadStatus = document.getElementById('uploadStatus');
    
    let mediaRecorder;
    let audioChunks = [];
    
    // Initialize audio elements
    const audioElements = [echoAudio, echoTTSAudio];

    // Configure audio elements
    audioElements.forEach(audio => {
        if (!audio) return;
        
        // Make sure audio elements are visible and have controls
        audio.controls = true;
        audio.style.display = 'block';
        audio.style.width = '100%';
        audio.style.margin = '10px 0';
        audio.preload = 'auto';
        
        // Add event listeners for better user feedback
        audio.addEventListener('play', () => {
            console.log('Audio playback started');
            const statusElement = audio === echoAudio ? 
                document.getElementById('recordingStatus') : 
                document.getElementById('ttsStatus');
            if (statusElement) {
                statusElement.textContent = 'Playing...';
                statusElement.classList.add('playing');
            }
        });
        
        audio.addEventListener('pause', () => {
            console.log('Audio playback paused');
            const statusElement = audio === echoAudio ? 
                document.getElementById('recordingStatus') : 
                document.getElementById('ttsStatus');
            if (statusElement) {
                statusElement.classList.remove('playing');
            }
        });
        
        audio.addEventListener('ended', () => {
            console.log('Audio playback ended');
            const statusElement = audio === echoAudio ? 
                document.getElementById('recordingStatus') : 
                document.getElementById('ttsStatus');
            if (statusElement) {
                statusElement.textContent = `Audio ready (${formatDuration(audio.duration)})`;
                statusElement.classList.remove('playing');
            }
        });
        
        audio.addEventListener('error', (e) => {
            console.error('Audio playback error:', e);
            const statusElement = audio === echoAudio ? 
                document.getElementById('recordingStatus') : 
                document.getElementById('ttsStatus');
            if (statusElement) {
                statusElement.textContent = 'Error: Could not play audio';
                statusElement.classList.add('error');
            }
        });
    });
    
    // Function to update the status
    function updateStatus(message, isError = false) {
        const statusElement = document.getElementById('echoBotStatus');
        if (statusElement) {
            statusElement.textContent = message;
            statusElement.className = isError ? 'status-message error' : 'status-message';
            console.log('Status:', message);
        }
    }
    
    // Function to process audio with echo TTS
    async function processEchoTTS(blob) {
        console.log('Starting processEchoTTS');
        const transcriptionText = document.getElementById('transcriptionText');
        const echoAudio = document.getElementById('echoAudio');
        
        // Update status
        updateStatus('Processing your recording...');
        
        try {
            // 1. Create form data with the audio blob
            const formData = new FormData();
            formData.append('file', blob, 'recording.wav');
            
            // Update status
            updateStatus('Sending to Echo TTS service...');
            
            // 3. Send to /tts/echo endpoint
            console.log('Sending audio for echo TTS processing...');
            const echoResponse = await fetch('/tts/echo', {
                method: 'POST',
                body: formData
            });
            
            console.log('Echo TTS response status:', echoResponse.status);
            const echoData = await echoResponse.json();
            
            if (!echoResponse.ok) {
                console.error('Echo TTS failed:', echoData);
                throw new Error(echoData.detail || 'Echo TTS processing failed');
            }
            
            console.log('Echo TTS result:', echoData);
            
            // 4. Update the TTS audio player with the generated TTS audio
            if (echoTTSAudio && echoData.audio_url) {
                echoTTSAudio.src = echoData.audio_url;
                echoTTSAudio.controls = true;
                
                // Try to play the TTS audio
                echoTTSAudio.play().catch(e => {
                    console.log('Auto-play prevented, user interaction required');
                });
            } else if (!echoData.audio_url) {
                console.warn('No TTS audio URL in response');
                updateStatus('Warning: No TTS audio was generated', true);
            }
            
            // 5. Update status and show transcription
            if (echoData.transcription) {
                const transcript = echoData.transcription.text || 'No transcription available';
                if (transcriptionText) {
                    transcriptionText.textContent = transcript;
                }
                updateStatus('Processing complete! Transcription ready.');
            } else {
                console.warn('No transcription in response');
                if (transcriptionText) {
                    transcriptionText.textContent = 'No transcription available';
                }
                updateStatus('Processing complete! (No transcription available)');
            }
            
            return { success: true, audioUrl: echoData.audio_url };
            
        } catch (error) {
            console.error('Error in processEchoTTS:', error);
            updateStatus(`Error: ${error.message}`, true);
            if (transcriptionText) {
                transcriptionText.textContent = 'Error processing recording';
            }
            throw error; // Re-throw to be caught by the caller
        }
    }
    
    // Function to process audio with TTS
    async function uploadAudio(blob) {
        try {
            // Process the audio with Murf TTS
            const result = await processEchoTTS(blob);
            console.log('TTS processing complete');
            return result;
        } catch (error) {
            console.error('Error uploading audio:', error);
            updateStatus(`Upload failed: ${error.message}`, true);
            throw error;
        }
    }
    
    // TTS functionality
    if (ttsSubmitBtn) {
        ttsSubmitBtn.addEventListener('click', async () => {
            const text = ttsText.value.trim();
            const voiceId = voiceSelect.value;
            const ttsStatus = document.getElementById('ttsStatus');
            
            if (!text) {
                updateStatus('Please enter some text to convert to speech.', true);
                return;
            }
            
            updateStatus('Generating audio...');
            ttsSubmitBtn.disabled = true;
            
            try {
                const response = await fetch('/tts', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        text: text,
                        voice_id: voiceId
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`Error: ${response.status} ${response.statusText}`);
                }
                
                const data = await response.json();
                
                if (data.audio_url) {
                    // Set the audio source and play
                    ttsAudio.src = data.audio_url;
                    ttsAudio.style.display = 'block';
                    ttsStatus.style.color = 'black';
                    ttsStatus.textContent = 'Audio generated successfully!';
                    
                    // Play the audio
                    ttsAudio.play();
                } else {
                    ttsStatus.textContent = 'No audio URL received from the server.';
                }
            } catch (error) {
                console.error('Error generating TTS:', error);
                ttsStatus.textContent = `Error: ${error.message}`;
            } finally {
                ttsSubmitBtn.disabled = false;
            }
        });
    }
    
    // Echo Bot functionality
    if (startRecordingBtn && stopRecordingBtn) {
        let mediaRecorder = null;
        let audioChunks = [];
        let stream = null;
        
        // Request access to the microphone
        async function startRecording() {
            try {
                // Reset previous state
                audioChunks = [];
                
                // Request microphone access
                stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                
                // Set up data available handler
                mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) {
                        audioChunks.push(event.data);
                        console.log('Collected audio chunk, size:', event.data.size, 'bytes');
                    }
                };
                
                // Set up stop handler
                mediaRecorder.onstop = async () => {
                    try {
                        if (audioChunks.length === 0) {
                            throw new Error('No audio data was recorded');
                        }
                        
                        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                        updateStatus('Processing your recording...');
                        
                        // Update the audio player with the recorded audio
                        const audioPlayer = document.getElementById('echoAudio');
                        if (audioPlayer) {
                            audioPlayer.src = URL.createObjectURL(audioBlob);
                            audioPlayer.controls = true;
                        }
                        
                        // Process the recording
                        await processEchoTTS(audioBlob);
                        
                    } catch (error) {
                        console.error('Error processing recording:', error);
                        updateStatus(`Error: ${error.message}`, true);
                    } finally {
                        // Clean up
                        if (window.mediaStream) {
                            window.mediaStream.getTracks().forEach(track => track.stop());
                            window.mediaStream = null;
                        }
                        audioChunks = [];
                    }
                };
                
                // Start recording
                mediaRecorder.start(100); // Collect data every 100ms
                startRecordingBtn.disabled = true;
                stopRecordingBtn.disabled = false;
                updateStatus('Recording... Speak now!');
                
                // Auto-stop after 30 seconds to prevent very long recordings
                window.recordingTimeout = setTimeout(() => {
                    if (mediaRecorder && mediaRecorder.state === 'recording') {
                        stopRecording();
                    }
                }, 30000);
                
            } catch (error) {
                console.error('Error accessing microphone:', error);
                updateStatus(`Error: ${error.message}`, true);
                startRecordingBtn.disabled = false;
                stopRecordingBtn.disabled = true;
                
                // Clean up on error
                if (window.mediaStream) {
                    window.mediaStream.getTracks().forEach(track => track.stop());
                    window.mediaStream = null;
                }
            }
        }
        
        function stopRecording() {
            const startRecordingBtn = document.getElementById('startRecording');
            const stopRecordingBtn = document.getElementById('stopRecording');
            
            if (mediaRecorder && mediaRecorder.state === 'recording') {
                mediaRecorder.stop();
                startRecordingBtn.disabled = false;
                stopRecordingBtn.disabled = true;
                updateStatus('Processing your recording...');
            }
        }
        
        // Event listeners for the recording buttons
        startRecordingBtn.addEventListener('click', startRecording);
        stopRecordingBtn.addEventListener('click', stopRecording);
        
        // Initially disable the stop button
        stopRecordingBtn.disabled = true;
        
        // Update the UI to show we're using Murf TTS
        if (recordingStatus) {
            recordingStatus.textContent = 'Click the microphone to record. Audio will be processed with Murf TTS.';
        }
        
        // Add transcription status element if it doesn't exist
        let transcriptionStatus = document.getElementById('transcriptionStatus');
        if (!transcriptionStatus) {
            const transcriptionBox = document.getElementById('transcriptionBox');
            if (transcriptionBox) {
                transcriptionStatus = document.createElement('div');
                transcriptionStatus.id = 'transcriptionStatus';
                transcriptionStatus.className = 'status-message';
                transcriptionStatus.textContent = 'Transcription will appear here';
                
                // Insert the status inside the transcription box
                const firstChild = transcriptionBox.firstChild;
                if (firstChild) {
                    transcriptionBox.insertBefore(transcriptionStatus, firstChild.nextSibling);
                } else {
                    transcriptionBox.appendChild(transcriptionStatus);
                }
            }
        }
    }
});