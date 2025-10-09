# tts_aws.py
import os
import adafruit_connection_manager
import adafruit_requests
from aws_polly import text_to_speech_polly_http

class WordFetcherTTS():
    def __init__(self, fj=None, launcher_config=None, output_path="/saves/tts_output.mp3"):

        self.output_path = output_path
        self.fj = fj
        self.launcher_config = launcher_config

        # AWS auth requires us to have accurate date/time
        now = fj.sync_time()

        # setup adafruit_requests session
        pool = adafruit_connection_manager.get_radio_socketpool(fj.network._wifi.esp)
        ssl_context = adafruit_connection_manager.get_radio_ssl_context(fj.network._wifi.esp)
        self.requests = adafruit_requests.Session(pool, ssl_context)
        self.AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
        self.AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")

    def fetch_word(self, word: str, voice: str = "Joanna") -> bool:
        if not self.AWS_ACCESS_KEY or not self.AWS_SECRET_KEY:
            print("Missing AWS credentials.")
            return False

        if self.fj:
            self.fj.neopixels.fill(0xFFFF00)

        success = text_to_speech_polly_http(
            self.requests,
            text=word,
            access_key=self.AWS_ACCESS_KEY,
            secret_key=self.AWS_SECRET_KEY,
            output_file=self.output_path,
            voice_id=voice,
            region="us-east-1",
            output_format="mp3",
        )

        if self.fj:
            self.fj.neopixels.fill(0x00FF00)
        return success
