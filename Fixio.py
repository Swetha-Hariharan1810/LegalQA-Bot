import asyncio
import logging
from fastapi import FastAPI, WebSocket
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
from botocore.exceptions import BotoCoreError, ClientError
import numpy as np
import subprocess
import soundfile as sf
import io

logging.basicConfig(level=logging.DEBUG, filename='app.log', filemode='a', format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

client = TranscribeStreamingClient(region="us-east-1")

stream = None
handler = None
audio_file_path = "received_audio.pcm"

@app.on_event("startup")
async def stream_start():
    global stream 
    global handler
    stream = await client.start_stream_transcription(
        language_code="en-US",
        media_sample_rate_hz=16000,
        media_encoding="pcm",
    )
    handler = MyEventHandler(stream.output_stream)

audio_queue = asyncio.Queue()

class MyEventHandler(TranscriptResultStreamHandler):
    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        logging.debug("Received a transcript event")
        results = transcript_event.transcript.results
        logging.info(f"results: {results}")
        for result in results:
            for alt in result.alternatives:
                transcript_text = alt.transcript
                logging.info(f"Transcription: {transcript_text}")
                print(f"Transcript: {transcript_text}")

async def write_chunks():
    with open(audio_file_path, 'wb') as audio_file:
        while True:
            chunk = await audio_queue.get()
            if chunk is None:
                break
            await stream.input_stream.send_audio_event(audio_chunk=chunk)
            audio_file.write(chunk)
            logging.info(f"Sent audio chunk to AWS Transcribe, size: {len(chunk)} bytes")
    await stream.input_stream.end_stream()

async def encode_pcm_to_buffer(blob):
    try:
        # Convert webm to wav using ffmpeg
        process = await asyncio.create_subprocess_exec(
            'ffmpeg', '-i', 'pipe:0', '-f', 'wav', 'pipe:1',
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        wav_data, stderr = await process.communicate(input=blob)

        if process.returncode != 0:
            logging.error(f"FFmpeg error: {stderr.decode()}")
            return None

        # Read the WAV data and convert to PCM int16
        wav_io = io.BytesIO(wav_data)
        with sf.SoundFile(wav_io) as wav_file:
            pcm_data = wav_file.read(dtype='int16')
            pcm_bytes = pcm_data.tobytes()

        return pcm_bytes
    except Exception as e:
        logging.error(f"Error in encode_pcm_to_buffer: {e}")
        return None

async def receive_audio_chunks(websocket):
    try:
        async for message in websocket.iter_bytes():
            # Validate the message
            if isinstance(message, bytes) and len(message) > 0:
                logging.info(f"Received audio chunk of size: {len(message)} bytes")
                encoded_buffer = await encode_pcm_to_buffer(message)
                if encoded_buffer:
                    await audio_queue.put(encoded_buffer)
                    logging.info(f"Queued encoded audio chunk of size: {len(encoded_buffer)} bytes")
                else:
                    logging.warning("Encoded buffer is None, skipping this chunk.")
            else:
                logging.warning(f"Invalid audio chunk received: {message}")
    except Exception as e:
        logging.error(f"Error receiving audio chunk: {e}")
    finally:
        await audio_queue.put(None)  # Signal end of stream

async def handle_transcription_events():
    try:
        await handler.handle_events()
    except Exception as e:
        logging.error(f"Error handling transcription events: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logging.info("WebSocket connection accepted")

    try:
        logging.info("Started AWS Transcribe stream")
        await asyncio.gather(
            receive_audio_chunks(websocket),
            write_chunks(),
            handle_transcription_events()
        )
    except (BotoCoreError, ClientError) as e:
        logging.error(f"AWS Transcribe error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        logging.info("WebSocket connection closed")
        await websocket.close()
        
