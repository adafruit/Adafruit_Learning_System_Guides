# tts_kani.py
import json
import adafruit_connection_manager
import adafruit_requests

class WordFetcherTTS():
    def __init__(self, fj=None, launcher_config=None, output_path="/saves/tts_output.wav"):

        self.output_path = output_path
        self.launcher_config = launcher_config
        self.fj = fj

        # AWS auth requires us to have accurate date/time
        now = fj.sync_time()

        # setup adafruit_requests session
        pool = adafruit_connection_manager.get_radio_socketpool(fj.network._wifi.esp)
        self.requests = adafruit_requests.Session(pool)

    def fetch_word(self, word: str, voice: str = "katie") -> bool:

        if self.fj:
            self.fj.neopixels.fill(0xFFFF00)

        audio_data = self.text_to_speech_http(
            text=word,
            voice_id=voice,
        )

        success = False
        if audio_data:
            # Save to file
            try:
                with open(self.output_path, "wb") as f:
                    f.write(audio_data)
                print(f"Audio saved to: {self.output_path}")
                success = True
            except Exception as e: # pylint: disable=broad-except
                print(f"Failed to save file: {e}")
                success = False
        else:
            print("Failed to synthesize speech")
            success = False

        if self.fj:
            self.fj.neopixels.fill(0x00FF00)
        return success

    def text_to_speech_http(
        self,
        text,
        voice_id,
    ):
        """
        Simple function to convert text to speech using kani-tts AI local server.py HTTP API

        Args:
            text (str): Text to convert
            voice_id (str): voice ID

        Returns:
            bool: True if successful, False otherwise
        """

        # Prepare request
        print(self.launcher_config.data)
        endpoint = ""
        if self.launcher_config and "spell_jam" in self.launcher_config.data:
            endpoint = self.launcher_config.data["spell_jam"].get("tts_server_endpoint","")
        if endpoint == "":
            print("tts_server_endpoint not configured in launcher.conf.json.")
            return None

        method = "POST"
        uri = "/tts"

        # Create request body
        request_body = {
            "text": f'{voice_id}: {text}',
            "temperature": 0.4,
            "max_tokens": 400,
            "top_p": 0.95,
            "chunk_size": 25,
            "lookback_frames": 15
        }
        payload = json.dumps(request_body)
        url = f"{endpoint}{uri}"
        headers = {"Content-Type": "application/json"}
        print(f"Making request to: {url}, headers: {headers}, payload: {payload}")

        try:
            response = self.requests.post(url, headers=headers, data=payload)

            if response.status_code == 200:
                return response.content
            else:
                print(f"Error: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return None

        except Exception as e:  # pylint: disable=broad-except
            print(f"Request failed: {e}")
            return None

