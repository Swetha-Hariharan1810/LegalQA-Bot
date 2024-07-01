import asyncio
import logging
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent

# Configure logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

class MyEventHandler(TranscriptResultStreamHandler):
    def __init__(self, websocket: WebSocket):
        super().__init__()
        self.websocket = websocket

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        results = transcript_event.transcript.results
        for result in results:
            for alt in result.alternatives:
                logging.info(f"Sending transcript: {alt.transcript}")
                await self.websocket.send_text(alt.transcript)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logging.info("WebSocket connection accepted")

    client = TranscribeStreamingClient(region="us-west-2")
    stream = await client.start_stream_transcription(
        language_code="en-US",
        media_sample_rate_hz=16000,
        media_encoding="pcm",
    )
    handler = MyEventHandler(websocket)

    async def write_chunks():
        try:
            async for message in websocket.iter_bytes():
                await stream.input_stream.send_audio_event(audio_chunk=message)
                logging.info("Sent audio chunk to AWS Transcribe")
        except Exception as e:
            logging.error(f"Error sending audio chunk: {e}")
        finally:
            await stream.input_stream.end_stream()
            logging.info("Stream ended")

    await asyncio.gather(write_chunks(), handler.handle_events())
    logging.info("WebSocket connection closed")
  
