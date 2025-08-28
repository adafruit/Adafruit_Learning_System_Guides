# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
import hmac
import json

from adafruit_datetime import datetime
import adafruit_hashlib as hashlib


def url_encode(string, safe=""):
    """
    Minimal URL encoding function to replace urllib.parse.quote

    Args:
        string (str): String to encode
        safe (str): Characters that should not be encoded

    Returns:
        str: URL encoded string
    """
    # Characters that need to be encoded (RFC 3986)
    unreserved = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~"

    # Add safe characters to unreserved set
    allowed = unreserved + safe

    encoded = ""
    for char in string:
        if char in allowed:
            encoded += char
        else:
            # Convert to percent-encoded format
            encoded += f"%{ord(char):02X}"

    return encoded


def _zero_pad(num, count=2):
    padded = str(num)
    while len(padded) < count:
        padded = "0" + padded
    return padded


class PollyHTTPClient:
    def __init__(self, requests_instance, access_key, secret_key, region="us-east-1"):
        self._requests = requests_instance
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.service = "polly"
        self.host = f"polly.{region}.amazonaws.com"
        self.endpoint = f"https://{self.host}"

    def _sign(self, key, msg):
        """Helper function for AWS signature"""
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    def _get_signature_key(self, date_stamp):
        """Generate AWS signature key"""
        k_date = self._sign(("AWS4" + self.secret_key).encode("utf-8"), date_stamp)
        k_region = self._sign(k_date, self.region)
        k_service = self._sign(k_region, self.service)
        k_signing = self._sign(k_service, "aws4_request")
        return k_signing

    def _create_canonical_request(self, method, uri, query_string, headers, payload):
        """Create canonical request for AWS Signature V4"""
        canonical_uri = url_encode(uri, safe="/")
        canonical_querystring = query_string

        # Create canonical headers
        canonical_headers = ""
        signed_headers = ""
        header_names = sorted(headers.keys())
        for name in header_names:
            canonical_headers += f"{name.lower()}:{headers[name].strip()}\n"
            signed_headers += f"{name.lower()};"
        signed_headers = signed_headers[:-1]  # Remove trailing semicolon

        # Create payload hash
        payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        # Create canonical request
        canonical_request = (f"{method}\n{canonical_uri}\n{canonical_querystring}\n"
                             f"{canonical_headers}\n{signed_headers}\n{payload_hash}")

        return canonical_request, signed_headers

    def _create_string_to_sign(self, timestamp, credential_scope, canonical_request):
        """Create string to sign for AWS Signature V4"""
        algorithm = "AWS4-HMAC-SHA256"
        canonical_request_hash = hashlib.sha256(
            canonical_request.encode("utf-8")
        ).hexdigest()
        string_to_sign = (
            f"{algorithm}\n{timestamp}\n{credential_scope}\n{canonical_request_hash}"
        )
        return string_to_sign

    def synthesize_speech( # pylint: disable=too-many-locals
        self,
        text,
        voice_id="Joanna",
        output_format="mp3",
        engine="standard",
        text_type="text",
    ):
        """
        Synthesize speech using Amazon Polly via direct HTTP request

        Args:
            text (str): Text to convert to speech
            voice_id (str): Voice to use (e.g., 'Joanna', 'Matthew', 'Amy')
            output_format (str): Audio format ('mp3', 'ogg_vorbis', 'pcm')
            engine (str): Engine type ('standard' or 'neural')
            text_type (str): 'text' or 'ssml'

        Returns:
            bytes: Audio data if successful, None if failed
        """

        # Prepare request
        method = "POST"
        uri = "/v1/speech"

        # Create request body
        request_body = {
            "Text": text,
            "OutputFormat": output_format,
            "VoiceId": voice_id,
            "Engine": engine,
            "TextType": text_type,
        }
        payload = json.dumps(request_body)

        # Get current time
        now = datetime.now()
        # amzdate = now.strftime('%Y%m%dT%H%M%SZ')
        amzdate = (f"{now.year}{_zero_pad(now.month)}{_zero_pad(now.day)}"
                   f"T{_zero_pad(now.hour)}{_zero_pad(now.minute)}{_zero_pad(now.second)}Z")
        # datestamp = now.strftime('%Y%m%d')
        datestamp = f"{now.year}{_zero_pad(now.month)}{_zero_pad(now.day)}"

        # Create headers
        headers = {
            "Content-Type": "application/x-amz-json-1.0",
            "Host": self.host,
            "X-Amz-Date": amzdate,
            "X-Amz-Target": "AWSPollyService.SynthesizeSpeech",
        }

        # Create canonical request
        canonical_request, signed_headers = self._create_canonical_request(
            method, uri, "", headers, payload
        )

        # Create string to sign
        credential_scope = f"{datestamp}/{self.region}/{self.service}/aws4_request"
        string_to_sign = self._create_string_to_sign(
            amzdate, credential_scope, canonical_request
        )

        # Create signature
        signing_key = self._get_signature_key(datestamp)
        signature = hmac.new(
            signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # Add authorization header
        authorization_header = (
            f"AWS4-HMAC-SHA256 "
            f"Credential={self.access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )
        headers["Authorization"] = authorization_header

        # Make request
        try:
            url = f"{self.endpoint}{uri}"
            response = self._requests.post(url, headers=headers, data=payload)

            if response.status_code == 200:
                return response.content
            else:
                print(f"Error: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return None

        except Exception as e:
            print(f"Request failed: {e}")
            return None


def text_to_speech_polly_http(
    requests_instance,
    text,
    access_key,
    secret_key,
    output_file="/saves/awspollyoutput.mp3",
    voice_id="Joanna",
    region="us-east-1",
    output_format="mp3",
):
    """
    Simple function to convert text to speech using Polly HTTP API

    Args:
        text (str): Text to convert
        access_key (str): AWS Access Key ID
        secret_key (str): AWS Secret Access Key
        output_file (str): Output file path
        voice_id (str): Polly voice ID
        region (str): AWS region
        output_format (str): Audio format

    Returns:
        bool: True if successful, False otherwise
    """

    # Create Polly client
    client = PollyHTTPClient(requests_instance, access_key, secret_key, region)

    # Synthesize speech
    audio_data = client.synthesize_speech(
        text=text, voice_id=voice_id, output_format=output_format
    )

    if audio_data:
        # Save to file
        try:
            with open(output_file, "wb") as f:
                f.write(audio_data)
            print(f"Audio saved to: {output_file}")
            return True
        except Exception as e:
            print(f"Failed to save file: {e}")
            return False
    else:
        print("Failed to synthesize speech")
        return False


def text_to_speech_with_ssml(
    requests_instance,
    text,
    access_key,
    secret_key,
    speech_rate="medium",
    output_file="output.mp3",
):
    """
    Example with SSML for speech rate control
    """
    # Wrap text in SSML
    ssml_text = f'<speak><prosody rate="{speech_rate}">{text}</prosody></speak>'

    client = PollyHTTPClient(requests_instance, access_key, secret_key)
    audio_data = client.synthesize_speech(
        text=ssml_text, voice_id="Joanna", text_type="ssml"
    )

    if audio_data:
        with open(output_file, "wb") as f:
            f.write(audio_data)
        print(f"SSML audio saved to: {output_file}")
        return True
    return False


# Example usage
# if __name__ == "__main__":
#     # Replace with your actual AWS credentials
#     AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
#     AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
#
#     # Basic usage
#     success = text_to_speech_polly_http(
#         text="Hello from CircuitPython! This is Amazon Polly speaking.",
#         access_key=AWS_ACCESS_KEY,
#         secret_key=AWS_SECRET_KEY,
#         voice_id="Joanna"
#     )

# SSML example
# if success:
#     text_to_speech_with_ssml(
#         text="This speech has a custom rate using SSML markup.",
#         access_key=AWS_ACCESS_KEY,
#         secret_key=AWS_SECRET_KEY,
#         speech_rate="slow",
#         output_file="ssml_example.mp3"
#     )
