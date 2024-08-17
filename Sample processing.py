import boto3
import botocore.exceptions
from contextlib import closing
import wave
import time
from botocore.exceptions import BotoCoreError, ClientError
from pydub import AudioSegment

class TranscribeStreamingSynchronousClient:
    MAX_TIMEOUT_MS = 15 * 60 * 1000  # 15 minutes

    def __init__(self, client):
        self.client = client
        self.final_transcript = ""

    def transcribe_file(self, audio_file_path):
        try:
            audio = AudioSegment.from_file(audio_file_path)
            sample_rate = int(audio.frame_rate)

            response = self.client.start_stream_transcription(
                LanguageCode='en-US',
                MediaEncoding='pcm',
                MediaSampleRateHertz=sample_rate,
                ShowSpeakerLabel=True
            )

            print("Launching request")
            for event in response['TranscriptResultStream']:
                if 'TranscriptEvent' in event:
                    results = event['TranscriptEvent']['Transcript']['Results']
                    if results:
                        self._process_results(results)

            return self.final_transcript

        except (BotoCoreError, ClientError) as e:
            print(f"Error streaming audio to AWS Transcribe service: {e}")
            raise RuntimeError(e)
        except Exception as e:
            print(f"Error reading audio file ({audio_file_path}) : {e}")
            raise RuntimeError(e)

    def _process_results(self, results):
        for result in results:
            if result['Alternatives']:
                transcript = result['Alternatives'][0]['Transcript']
                if transcript and not result['IsPartial']:
                    # Speaker label handling
                    speaker_label = result['Alternatives'][0]['Items'][0]['Speaker'] if 'Speaker' in result['Alternatives'][0]['Items'][0] else ""
                    speaker = f"Speaker {speaker_label}: " if speaker_label else ""

                    # Placeholder logic for pre and post transcript
                    pretranscript = transcript
                    posttranscript = f"{speaker}{pretranscript}\n"

                    # Append the post-transcript to the final transcript
                    self.final_transcript += posttranscript

if __name__ == "__main__":
    client = boto3.client('transcribe-streaming')
    transcriber = TranscribeStreamingSynchronousClient(client)
    transcript = transcriber.transcribe_file('path/to/your/audiofile.wav')
    print(transcript)
