import os
import asyncio
import websockets
import logging, sys
import string
import random
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from presigned_url import AWSTranscribePresignedURL
from eventstream import create_audio_event, decode_event

# Configure logging
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

# Configure access
access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")
session_token = os.getenv("AWS_SESSION_TOKEN", "")
region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
transcribe_url_generator = AWSTranscribePresignedURL(access_key, secret_key, session_token, region)

# Sound settings
language_code = "en-US"
media_encoding = "pcm"
sample_rate = 16000  # Updated sample rate to 16000 to match previous code
number_of_channels = 1  # Mono
channel_identification = False  # Mono, so no channel identification

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logging.info("WebSocket connection accepted")

    # Generate signed URL for AWS Transcribe
    request_url = transcribe_url_generator.get_request_url(sample_rate, 
                                                           language_code, 
                                                           media_encoding, 
                                                           number_of_channels=number_of_channels,
                                                           enable_channel_identification=channel_identification)
    
    async with websockets.connect(request_url, ping_timeout=None) as transcribe_ws:
        logging.info("Connected to AWS Transcribe WebSocket")

        async def send_audio():
            try:
                async for message in websocket.iter_bytes():
                    audio_event = create_audio_event(message)
                    await transcribe_ws.send(audio_event)
                    logging.info("Sent audio chunk to AWS Transcribe")
            except websockets.exceptions.ConnectionClosedError as e:
                logging.error("Connection closed error while sending audio", exc_info=e)
            except Exception as e:
                logging.exception("Exception while sending audio", exc_info=e)
            finally:
                await transcribe_ws.close()
                logging.info("Closed AWS Transcribe WebSocket")

        async def receive_transcript():
            try:
                while True:
                    response = await transcribe_ws.recv()
                    header, payload = decode_event(response)
                    if header[':message-type'] == 'event' and len(payload['Transcript']['Results']) > 0:
                        transcript = payload['Transcript']['Results'][0]['Alternatives'][0]['Transcript']
                        logging.info(f"Received transcript: {transcript}")
                        await websocket.send_text(transcript)
                    elif header[":message-type"] == 'exception':
                        logging.error(payload['Message'])
                    await asyncio.sleep(0)  # Yield to main loop
            except websockets.exceptions.ConnectionClosedError as e:
                logging.error("Connection closed error while receiving transcript", exc_info=e)
            except Exception as e:
                logging.exception("Exception while receiving transcript", exc_info=e)

        await asyncio.gather(send_audio(), receive_transcript())
        logging.info("WebSocket connection closed")
