let ws;
let mediaRecorder;

document.getElementById('recordButton').addEventListener('click', async () => {
    const button = document.getElementById('recordButton');
    const transcriptionDiv = document.getElementById('transcription');

    if (button.textContent === 'Start Recording') {
        console.log('Starting recording...');
        transcriptionDiv.innerHTML = ''; // Clear previous transcriptions

        ws = new WebSocket('ws://localhost:8000/ws');

        ws.onopen = () => {
            console.log('WebSocket connection opened');
        };

        ws.onmessage = function(event) {
            console.log('Received transcript:', event.data);
            transcriptionDiv.innerHTML += `<p>${event.data}</p>`;
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        ws.onclose = () => {
            console.log('WebSocket connection closed');
        };

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);

            mediaRecorder.ondataavailable = function(event) {
                if (event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
                    ws.send(event.data);
                    console.log('Sent audio data');
                }
            };

            mediaRecorder.start(100); // send audio data every 100ms
            button.textContent = 'Stop Recording';
            console.log('Recording started');
        } catch (error) {
            console.error('Error accessing microphone:', error);
        }
    } else {
        console.log('Stopping recording...');
        mediaRecorder.stop();
        ws.close();
        button.textContent = 'Start Recording';
        console.log('Recording stopped');
    }
});
