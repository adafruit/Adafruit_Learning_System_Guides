# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
'''Raspberry Pi Halloween Costume Detector with OpenCV and Claude Vision API'''

#!/usr/bin/python3
import os
import subprocess
import time
import base64
import wave
import cv2
from picamera2 import Picamera2
import anthropic
from piper import PiperVoice, SynthesisConfig
import board
import digitalio

ANTHROPIC_API_KEY = "your-api-key-here"

try:
    username = os.getlogin()
    print(f"The current user is: {username}")
except OSError:
    print("Could not determine the login name.")
    print("Consider checking environment variables like USER or LOGNAME.")
    # Fallback to environment variables if os.getlogin() fails
    username = os.environ.get('USER') or os.environ.get('LOGNAME')
    if username:
        print(f"The user from environment variable is: {username}")
    else:
        print("User information not found in environment variables either.")

# Initialize LED
led = digitalio.DigitalInOut(board.D5)
led.direction = digitalio.Direction.OUTPUT
led.value = False  # Start with LED off

# Initialize detectors
upperbody_detector = cv2.CascadeClassifier(
                     "/usr/share/opencv4/haarcascades/haarcascade_upperbody.xml")
fgbg = cv2.createBackgroundSubtractorMOG2(detectShadows=False)

# Initialize camera
cv2.startWindowThread()
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(
                 main={"format": 'XRGB8888', "size": (640, 480)}))
picam2.start()

# Initialize Piper voice
voice = PiperVoice.load("/home/pi/en_US-joe-medium.onnx")
syn_config = SynthesisConfig(
    volume=1.0,
    length_scale=1.5,
    noise_scale=1.2,
    noise_w_scale=1.5,
    normalize_audio=False,
)

# Check for and create audio files if they don't exist
def create_audio_file_if_needed(filename, text):
    """Create audio file if it doesn't exist"""
    if not os.path.exists(filename):
        print(f"Creating {filename}...")
        with wave.open(filename, "wb") as wav:
            voice.synthesize_wav(text, wav, syn_config=syn_config)
        print(f"{filename} created!")
    else:
        print(f"{filename} already exists.")

# Create the hello and halloween audio files
create_audio_file_if_needed("hello.wav", "Hello? Who goes there?")
create_audio_file_if_needed("halloween.wav", "Happy Halloween!")

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
# set API key via the terminal as an environmental variable:
# export ANTHROPIC_API_KEY="your-api-key-here"

# Detection parameters
MOTION_THRESHOLD = 100000
COOLDOWN_SECONDS = 15
last_capture_time = 0
capture_delay = 5
motion_frame_count = 0
MOTION_FRAMES_REQUIRED = 5

def encode_image(image_path):
    """Encode image to base64 for Claude API"""
    with open(image_path, "rb") as image_file:
        return base64.standard_b64encode(image_file.read()).decode("utf-8")

def get_costume_joke(image_path):
    """Send image to Claude and get dad joke about costume"""
    print("Analyzing costume with Claude...")

    # Encode the image
    image_data = encode_image(image_path)

    # Send to Claude API
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=250,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": """Look at this image.
                        Your response must follow these rules exactly:

                        1. If you see a person in a Halloween costume, respond with ONLY a single-sentence cute,
                        family-friendly, encouraging, dad joke about the costume. Nothing else.

                        2. If you do NOT see a clear Halloween costume (empty room, unclear image, person in regular clothes, etc.),
                        respond with ONLY the character: 0

                        Examples of good responses:
                        - "Looks like that ghost costume is really boo-tiful!"
                        - "0"
                        - "I guess you could say that vampire costume really sucks... in a good way!"

                        Do not add any explanations, commentary, or descriptions. Just the joke or just 0.
                        """
                    }
                ],
            }
        ],
    )

    # Extract the joke from the response
    joke = message.content[0].text
    print(f"Claude's joke: {joke}")
    return joke
# pylint: disable=subprocess-run-check, broad-except
def play_audio_file(filename):
    """Play a pre-existing audio file"""
    print(f"Playing {filename}...")
    subprocess.run(["su", username, "-c", f"aplay {filename}"])

def speak_joke(joke_text):
    """Convert joke to speech and play it"""
    print("Generating speech...")

    wav_file = "joke.wav"

    # Generate audio with Piper
    with wave.open(wav_file, "wb") as wav:
        voice.synthesize_wav(joke_text, wav, syn_config=syn_config)

    print("Playing audio...")
    # Play the audio file (using aplay for Raspberry Pi)
    subprocess.run(["su", username, "-c", f"aplay {wav_file}"])

    # Optional: clean up the audio file after playing
    # os.remove(wav_file)

# Main loop
while True:
    im = picam2.capture_array()
    grey = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)

    # Check for motion
    fgmask = fgbg.apply(im)
    motion_amount = cv2.countNonZero(fgmask)
    motion_detected = motion_amount > MOTION_THRESHOLD

    if motion_detected:
        motion_frame_count += 1
    else:
        motion_frame_count = 0

    if motion_frame_count >= MOTION_FRAMES_REQUIRED:
        # Detect upperbody
        bodies = upperbody_detector.detectMultiScale(grey, 1.1, 3)
        person_detected = len(bodies) > 0

        # Draw rectangles
        for (x, y, w, h) in bodies:
            cv2.rectangle(im, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Process if person detected and cooldown passed
        current_time = time.time()
        if person_detected and (current_time - last_capture_time) > COOLDOWN_SECONDS:
            print("Person detected!")

            # Turn on LED and play hello message
            led.value = True
            play_audio_file("hello.wav")

            im = picam2.capture_array()
            # Capture image
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            file = f"costume_{timestamp}.jpg"
            cv2.imwrite(file, im)
            print(f"\nPicture saved: {file}")

            try:
                # Get joke from Claude
                the_joke = get_costume_joke(file)

                # If Claude returns 0, use the halloween fallback
                if the_joke.strip() == "0":
                    print("No costume detected, playing halloween.wav")
                    play_audio_file("halloween.wav")
                else:
                    # Speak the joke
                    speak_joke(the_joke)

            except Exception as e:
                print(f"Error: {e}")
                # Fallback to halloween.wav if something goes wrong
                play_audio_file("halloween.wav")

            # Turn off LED after processing
            led.value = False

            last_capture_time = current_time
            motion_frame_count = 0

    # Show motion amount
    cv2.putText(im, f"Motion: {motion_amount}", (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.imshow("Camera", im)
    cv2.waitKey(1)
