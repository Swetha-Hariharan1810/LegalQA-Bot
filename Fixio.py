import asyncio
import websockets
import soundfile as sf
import numpy as np
import io

async def audio_handler(websocket, path):
    async for message in websocket:
        audio_blob = message

        # Convert the audio blob (assuming it's in webm format) to PCM int16
        pcm_data = await convert_webm_to_pcm(audio_blob)

        # Do something with pcm_data, e.g., save to a file, process, etc.
        with open('output.pcm', 'ab') as f:
            f.write(pcm_data)

async def convert_webm_to_pcm(blob):
    import subprocess

    # Convert webm to wav using ffmpeg
    process = await asyncio.create_subprocess_exec(
        'ffmpeg', '-i', 'pipe:0', '-f', 'wav', 'pipe:1',
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    wav_data, _ = await process.communicate(input=blob)

    # Read the WAV data and convert to PCM int16
    wav_io = io.BytesIO(wav_data)
    with sf.SoundFile(wav_io) as wav_file:
        pcm_data = wav_file.read(dtype='int16')
        pcm_bytes = pcm_data.tobytes()

    return pcm_bytes

start_server = websockets.serve(audio_handler, "localhost", 5000)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
