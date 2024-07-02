import asyncio
import sounddevice as sd

from fastapi import FastAPI, WebSocket
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent

app = FastAPI()

CHUNK_SIZE = 1024  # Define chunk size for audio data


class MyEventHandler(TranscriptResultStreamHandler):
    def __init__(self, websocket: WebSocket):
        super().__init__()
        self.websocket = websocket

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        results = transcript_event.transcript.results
        if not results:
            await self.websocket.send_text("Processing...")  # Handle empty events
            return
        for result in results:
            for alt in result.alternatives:
                await self.websocket.send_text(alt.transcript)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    client = TranscribeStreamingClient(region="us-west-2")
    stream = await client.start_stream_transcription(
        language_code="en-US",
        media_sample_rate_hz=16000,
        media_encoding="pcm",
    )
    handler = MyEventHandler(websocket)

    async def write_chunks():
        try:
            async for data in websocket.iter_bytes():
                # Convert bytes to PCM format (using sounddevice)
                pcm_data = sd.bytes2buffer(data, dtype="int16")
                await stream.input_stream.send_audio_event(audio_chunk=pcm_data.tobytes())
        finally:
            await stream.input_stream.end_stream()

    await asyncio.gather(write_chunks(), handler.handle_events())
