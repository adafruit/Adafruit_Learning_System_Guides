# SPDX-FileCopyrightText: 2026 Gautham Chenoth Praveen 
# SPDX-License-Identifier: MIT license

import os
import ssl
import time
import board
import rtc
import wifi
import socketpool
import adafruit_ntp
import adafruit_requests
import bitmaptools
import displayio
import gifio
import binascii
import gc
import adafruit_pycamera
from adafruit_debouncer import Button
from digitalio import DigitalInOut, Direction, Pull

# --- Wi-Fi and AI Setup ---
UTC_OFFSET = os.getenv("UTC_OFFSET")
TZ = os.getenv("TZ")
SSID = os.getenv("CIRCUITPY_WIFI_SSID")
PASSWORD = os.getenv("CIRCUITPY_WIFI_PASSWORD")
API_KEY = os.getenv("OPENROUTER_API_KEY")
AI_PROMPT = os.getenv("AI_PROMPT") or "Describe this image in 5 words."
AI_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_ID = "openrouter/free"

pool = None
requests = None

# Custom wrapping function to replace the 'textwrap' module
def wrap_text(text, width):
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    for word in words:
        if current_length + len(word) + 1 <= width:
            current_line.append(word)
            current_length += len(word) + 1
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
            current_length = len(word)
    if current_line:
        lines.append(" ".join(current_line))
    return "\n".join(lines)

if SSID and PASSWORD:
    print(f"Connecting to {SSID}...")
    try:
        wifi.radio.connect(SSID, PASSWORD)
        pool = socketpool.SocketPool(wifi.radio)
        requests = adafruit_requests.Session(pool, ssl.create_default_context())
        
        if UTC_OFFSET is None and TZ:
            resp = requests.get("http://worldtimeapi.org/api/timezone/" + TZ).json()
            UTC_OFFSET = resp["raw_offset"] + resp["dst_offset"]

        ntp = adafruit_ntp.NTP(pool, server="pool.ntp.org", tz_offset=(UTC_OFFSET or 0) // 3600)
        rtc.RTC().datetime = ntp.datetime
        print("Time Synced:", ntp.datetime)
    except Exception as e:
        print("Wifi/NTP failed:", e)

# --- Hardware Setup ---
pycam = adafruit_pycamera.PyCamera()

# External Button Setup (Pin A0)
ext_pin = DigitalInOut(board.A0)
ext_pin.direction = Direction.INPUT
ext_pin.pull = Pull.UP
ext_button = Button(ext_pin, long_duration_ms=1000)

settings = (None, "resolution", "effect", "mode", "led_level", "led_color", "timelapse_rate")
curr_setting = 0

last_frame = displayio.Bitmap(pycam.camera.width, pycam.camera.height, 65535)
onionskin = displayio.Bitmap(pycam.camera.width, pycam.camera.height, 65535)
timelapse_remaining = None
timelapse_timestamp = None

def send_to_ai():
    if not requests:
        pycam.display_message("No WiFi", color=0xFF0000)
        return

    gc.collect()
    old_res = pycam.resolution
    pycam.resolution = 0 # Lowest res for RAM safety
    
    try:
        pycam.display_message("AI Snap...", color=0xFFFF00)
        
        prefix = "ai_v" 
        pycam.capture_jpeg(prefix)
        
        # Find latest file
        all_files = [f for f in os.listdir("/sd") if f.startswith(prefix) and f.endswith(".jpg")]
        if not all_files:
            raise Exception("File not found")
        all_files.sort()
        latest_file = "/sd/" + all_files[-1]
        
        with open(latest_file, "rb") as f:
            image_binary = f.read()
            
        encoded = binascii.b2a_base64(image_binary).decode("utf-8").replace("\n", "")
        image_binary = None 
        gc.collect()
        
        pycam.display_message("Thinking...", color=0x00FFFF)
        
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": MODEL_ID,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": AI_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encoded}"
                            }
                        }
                    ]
                }
            ]
        }
        
        print(f"Sending to {MODEL_ID}...")
        response = requests.post(AI_API_URL, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            answer = result["choices"][0]["message"]["content"]
            print("AI Result:", answer)
            
            # --- Text Wrapping and Scaling ---
            # Using our custom function to wrap text to ~22 chars wide
            wrapped_result = wrap_text(answer, 22)
            pycam.display_message(wrapped_result, color=0x00FF00, scale=1)
            
            # Clean up SD card
            try:
                os.remove(latest_file)
            except:
                pass
        else:
            pycam.display_message(f"Err {response.status_code}", color=0xFF0000)
                
        time.sleep(6) # Extra time to read the result
        
    except Exception as e:
        print("AI Error:", e)
        pycam.display_message("AI Fail", color=0xFF0000)
        time.sleep(2)
    
    encoded = None
    gc.collect()
    pycam.resolution = old_res
    pycam.live_preview_mode()

print("Starting Loop!")

while True:
    # --- Mode Handling & Preview ---
    if pycam.mode_text == "STOP" and pycam.stop_motion_frame != 0:
        new_frame = pycam.continuous_capture()
        bitmaptools.alphablend(onionskin, last_frame, new_frame, displayio.Colorspace.RGB565_SWAPPED)
        pycam.blit(onionskin)
        
    elif pycam.mode_text == "GBOY":
        bitmaptools.dither(last_frame, pycam.continuous_capture(), displayio.Colorspace.RGB565_SWAPPED)
        pycam.blit(last_frame)
        
    elif pycam.mode_text == "LAPS":
        if timelapse_remaining is None:
            pycam.timelapsestatus_label.text = "STOP"
        else:
            timelapse_remaining = int(timelapse_timestamp - time.time())
            pycam.timelapsestatus_label.text = f"{timelapse_remaining}s /    "
        
        pycam.timelapse_rate_label.text = pycam.timelapse_rate_label.text
        pycam.timelapse_submode_label.text = pycam.timelapse_submode_label.text

        if (timelapse_remaining is None) or (pycam.timelapse_submode_label.text == "HiPwr"):
            pycam.blit(pycam.continuous_capture())
        
        pycam.display.brightness = 0.05 if (pycam.timelapse_submode_label.text == "LowPwr" and timelapse_remaining is not None) else 1.0
        pycam.display.refresh()

        if timelapse_remaining is not None and timelapse_remaining <= 0:
            pycam.blit(pycam.continuous_capture())
            try:
                pycam.display_message("Snap!", color=0x0000FF)
                pycam.capture_jpeg()
            except Exception:
                pycam.display_message("Error", color=0xFF0000)
            
            pycam.live_preview_mode()
            pycam.display.refresh()
            timelapse_timestamp = time.time() + pycam.timelapse_rates[pycam.timelapse_rate] + 1
    else:
        pycam.blit(pycam.continuous_capture())

    # --- Button Inputs ---
    pycam.keys_debounce()
    ext_button.update()

    if pycam.shutter.long_press or ext_button.long_press:
        pycam.autofocus()

    if pycam.shutter.short_count or ext_button.short_count:
        if pycam.mode_text == "STOP":
            pycam.capture_into_bitmap(last_frame)
            pycam.stop_motion_frame += 1
            pycam.capture_jpeg()
            pycam.live_preview_mode()
        elif pycam.mode_text == "JPEG":
            pycam.tone(200, 0.1)
            pycam.display_message("Snap!", color=0x0000FF)
            pycam.capture_jpeg()
            pycam.live_preview_mode()
        elif pycam.mode_text == "GIF":
            try:
                with pycam.open_next_image("gif") as f:
                    pycam._mode_label.text = "RECORDING"
                    with gifio.GifWriter(f, pycam.camera.width, pycam.camera.height, 
                                         displayio.Colorspace.RGB565_SWAPPED, dither=True) as g:
                        i = 0
                        while (i < 15) or not pycam.shutter_button.value:
                            i += 1
                            _f = pycam.continuous_capture()
                            g.add_frame(_f, 0.12)
                            pycam.blit(_f)
                    pycam._mode_label.text = "GIF"
            except:
                pycam.display_message("SD Error", color=0xFF0000)

    # --- OK Button (Trigger AI in JPEG mode) ---
    if pycam.ok.fell:
        if pycam.mode_text == "LAPS":
            if timelapse_remaining is None: # Start
                timelapse_remaining = pycam.timelapse_rates[pycam.timelapse_rate]
                timelapse_timestamp = time.time() + timelapse_remaining + 1
                s = pycam.get_camera_autosettings()
                pycam.set_camera_exposure(s["exposure"])
                pycam.set_camera_gain(s["gain"])
                pycam.set_camera_wb(s["wb"])
            else: # Stop
                timelapse_remaining = None
                pycam.camera.exposure_ctrl = True
                pycam.set_camera_gain(None)
                pycam.set_camera_wb(None)
                pycam.set_camera_exposure(None)
        elif pycam.mode_text == "JPEG":
            send_to_ai()

    # D-Pad Navigation
    if pycam.right.fell:
        curr_setting = (curr_setting + 1) % len(settings)
        if pycam.mode_text != "LAPS" and settings[curr_setting] == "timelapse_rate":
            curr_setting = (curr_setting + 1) % len(settings)
        pycam.select_setting(settings[curr_setting])
        
    if pycam.left.fell:
        curr_setting = (curr_setting - 1 + len(settings)) % len(settings)
        if pycam.mode_text != "LAPS" and settings[curr_setting] == "timelapse_rate":
            curr_setting = (curr_setting - 1 + len(settings)) % len(settings)
        pycam.select_setting(settings[curr_setting])

    if pycam.up.fell and settings[curr_setting]:
        setattr(pycam, settings[curr_setting], getattr(pycam, settings[curr_setting]) + 1)
    if pycam.down.fell and settings[curr_setting]:
        setattr(pycam, settings[curr_setting], getattr(pycam, settings[curr_setting]) - 1)

    if pycam.select.fell and pycam.mode_text == "LAPS":
        pycam.timelapse_submode += 1

    # SD Card hot-swap
    if pycam.card_detect.fell:
        pycam.unmount_sd_card()
    if pycam.card_detect.rose:
        try: pycam.mount_sd_card()
        except: pass
