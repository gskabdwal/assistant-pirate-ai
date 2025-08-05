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
    
    let mediaRecorder;
    let audioChunks = [];
    
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
                
                mediaRecorder.onstop = () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                    const audioUrl = URL.createObjectURL(audioBlob);
                    echoAudio.src = audioUrl;
                    recordingStatus.textContent = 'Recording complete! Click play to hear your recording.';
                    recordingStatus.style.color = 'black';
                    
                    // Enable the play button
                    echoAudio.controls = true;
                    
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
    }
});