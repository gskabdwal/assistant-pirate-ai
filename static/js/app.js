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
    const recordingStatus = document.getElementById('recordingStatus');
    const uploadStatus = document.getElementById('uploadStatus');
    
    let mediaRecorder;
    let audioChunks = [];
    
    // Function to update the upload status
    function updateUploadStatus(message, isError = false) {
        if (!uploadStatus) return;
        
        // Clear previous classes
        uploadStatus.className = 'status-message';
        
        // Set the message text
        uploadStatus.textContent = message;
        
        // Add appropriate class based on message type
        if (message.includes('Uploading')) {
            uploadStatus.classList.add('info');
        } else if (message.includes('successful')) {
            uploadStatus.classList.add('success');
        } else if (isError || message.includes('failed') || message.includes('Error')) {
            uploadStatus.classList.add('error');
        }
    }
    
    // Function to transcribe audio using the server
    async function transcribeAudio(blob) {
        updateUploadStatus('Transcribing audio...');
        
        try {
            const formData = new FormData();
            formData.append('file', blob, 'recording.wav');
            
            const response = await fetch('/transcribe/file', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.status === 'success') {
                updateUploadStatus('Transcription complete!');
                return result;
            } else {
                throw new Error(result.error || 'Unknown error during transcription');
            }
        } catch (error) {
            console.error('Error transcribing audio:', error);
            updateUploadStatus(`Transcription failed: ${error.message}`, true);
            throw error;
        }
    }
    
    // Function to upload audio to the server
    async function uploadAudio(blob) {
        updateUploadStatus('Uploading audio...');
        
        try {
            const formData = new FormData();
            formData.append('file', blob, 'recording.wav');
            
            const response = await fetch('/upload-audio/', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Upload failed: ${response.status} ${response.statusText}`);
            }
            
            const result = await response.json();
            updateUploadStatus(
                `Upload successful! File: ${result.filename}, ` +
                `Type: ${result.content_type}, Size: ${(result.size / 1024).toFixed(2)} KB`
            );
            return result;
        } catch (error) {
            console.error('Upload error:', error);
            updateUploadStatus(`Upload failed: ${error.message}`, true);
            throw error;
        }
    }
    
    // TTS functionality
    if (ttsSubmitBtn) {
        ttsSubmitBtn.addEventListener('click', async () => {
            const text = ttsText.value.trim();
            const voiceId = voiceSelect.value;
            
            if (!text) {
                ttsStatus.textContent = 'Please enter some text to convert to speech.';
                return;
            }
            
            ttsStatus.textContent = 'Generating audio...';
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
        // Request access to the microphone
        async function startRecording() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                
                mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) {
                        audioChunks.push(event.data);
                    }
                };
                
                mediaRecorder.onstop = async () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                    const audioUrl = URL.createObjectURL(audioBlob);
                    echoAudio.src = audioUrl;
                    recordingStatus.textContent = 'Recording complete! Processing...';
                    recordingStatus.style.color = 'black';
                    
                    // Enable the play button
                    echoAudio.controls = true;
                    
                    try {
                        // Transcribe the audio
                        const result = await transcribeAudio(audioBlob);
                        
                        // Display the transcription
                        const transcriptionStatus = document.getElementById('transcriptionStatus');
                        if (transcriptionStatus) {
                            let transcriptionText = 'No transcription available';
                            
                            if (result.transcript) {
                                if (result.speakers && result.speakers.length > 0) {
                                    // Format with speaker labels if available
                                    transcriptionText = result.speakers.map(utterance => 
                                        `Speaker ${utterance.speaker}: ${utterance.text}`
                                    ).join('\n\n');
                                } else {
                                    // Just show the plain transcript
                                    transcriptionText = result.transcript;
                                }
                                
                                // Update the status with the transcription
                                transcriptionStatus.textContent = transcriptionText;
                                transcriptionStatus.classList.remove('status-message');
                                transcriptionStatus.classList.add('transcription-result');
                            } else {
                                transcriptionStatus.textContent = 'No transcription available';
                                transcriptionStatus.className = 'status-message';
                            }
                        }
                        recordingStatus.textContent = 'Recording complete! Click play to hear your recording.';
                    } catch (error) {
                        console.error('Error processing recording:', error);
                        recordingStatus.textContent = 'Error processing recording. See upload status for details.';
                        recordingStatus.style.color = 'red';
                    }
                    
                    // Stop all tracks in the stream
                    stream.getTracks().forEach(track => track.stop());
                };
                
                mediaRecorder.start();
                startRecordingBtn.disabled = true;
                stopRecordingBtn.disabled = false;
                recordingStatus.textContent = 'Recording... Speak now!';
                recordingStatus.style.color = 'red';
                
                // Auto-stop after 30 seconds to prevent very long recordings
                setTimeout(() => {
                    if (mediaRecorder && mediaRecorder.state === 'recording') {
                        stopRecording();
                    }
                }, 30000);
                
            } catch (error) {
                console.error('Error accessing microphone:', error);
                recordingStatus.textContent = 'Error accessing microphone. Please check your permissions.';
                recordingStatus.style.color = 'red';
                startRecordingBtn.disabled = false;
                stopRecordingBtn.disabled = true;
            }
        }
        
        function stopRecording() {
            if (mediaRecorder && mediaRecorder.state === 'recording') {
                mediaRecorder.stop();
                startRecordingBtn.disabled = false;
                stopRecordingBtn.disabled = true;
                recordingStatus.textContent = 'Processing your recording...';
                recordingStatus.style.color = 'black';
            }
        }
        
        // Event listeners for the recording buttons
        startRecordingBtn.addEventListener('click', startRecording);
        stopRecordingBtn.addEventListener('click', stopRecording);
        
        // Add transcription status element
        const transcriptionStatus = document.createElement('div');
        transcriptionStatus.id = 'transcriptionStatus';
        transcriptionStatus.className = 'status-message';
        transcriptionStatus.textContent = 'Transcription will appear here';
        
        // Add it after the upload status in the audio player section
        const audioPlayer = document.querySelector('.audio-player');
        const uploadStatus = document.getElementById('uploadStatus');
        audioPlayer.insertBefore(transcriptionStatus, uploadStatus.nextSibling);
    }
});