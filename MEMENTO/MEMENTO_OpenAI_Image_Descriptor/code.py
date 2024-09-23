# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import time
import ssl
import binascii
import wifi
import vectorio
import socketpool
import adafruit_requests
import displayio
from jpegio import JpegDecoder
from adafruit_display_text import label, wrap_text_to_lines
import terminalio
import adafruit_pycamera

# scale for displaying returned text from OpenAI
text_scale = 2

# OpenAI key and prompts from settings.toml
openai_api_key = os.getenv("OPENAI_API_KEY")
alt_text_prompt = os.getenv("ALT_TEXT_PROMPT")
haiku_prompt = os.getenv("HAIKU_PROMPT")
cable_prompt = os.getenv("CABLE_PROMPT")
translate_prompt = os.getenv("TRANSLATE_PROMPT")
alien_prompt = os.getenv("ALIEN_PROMPT")
weird_prompt = os.getenv("WEIRD_PROMPT")

prompts = [alt_text_prompt,
           haiku_prompt,
           cable_prompt,
           translate_prompt,
           alien_prompt,
           weird_prompt]
num_prompts = len(prompts)
prompt_index = 0
prompt_labels = ["ALT_TEXT", "HAIKU", "CABLE_IDENTIFIER", "TRANSLATE", "ALIEN", "WEIRD?"]

# encode jpeg to base64 for OpenAI
def encode_image(image_path):
    with open(image_path, 'rb') as image_file:
        image_data = image_file.read()
        base64_encoded_data = binascii.b2a_base64(image_data).decode('utf-8').rstrip()
        return base64_encoded_data

# view returned text on MEMENTO screen
def view_text(the_text):
    rectangle = vectorio.Rectangle(pixel_shader=palette, width=240, height=240, x=0, y=0)
    pycam.splash.append(rectangle)
    the_text = "\n".join(wrap_text_to_lines(the_text, 20))
    if prompt_index == 1:
        the_text = the_text.replace("*", "\n")
    text_area = label.Label(terminalio.FONT, text=the_text,
                            color=0xFFFFFF, x=2, y=10, scale=text_scale)
    pycam.splash.append(text_area)
    pycam.display.refresh()

# send image to OpenAI, print the returned text and save it as a text file
def send_img(img, prompt):
    base64_image = encode_image(img)
    headers = {
      "Content-Type": "application/json",
      "Authorization": f"Bearer {openai_api_key}"
    }
    payload = {
      "model": "gpt-4-turbo",
      "messages": [
        {
          "role": "user",
          "content": [
            {
              "type": "text",
              "text": f"{prompt}"
            },
            {
              "type": "image_url",
              "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
              }
            }
          ]
        }
      ],
      "max_tokens": 300
    }
    response = requests.post("https://api.openai.com/v1/chat/completions",
                             headers=headers, json=payload)
    json_openai = response.json()
    print(json_openai['choices'][0]['message']['content'])
    alt_text_file = img.replace('jpg', 'txt')
    alt_text_file = alt_text_file[:11] + f"_{prompt_labels[prompt_index]}" + alt_text_file[11:]
    if prompt_index == 5:
        alt_text_file = alt_text_file.replace("?", "")
    with open(alt_text_file, "a") as fp:
        fp.write(json_openai['choices'][0]['message']['content'])
        fp.flush()
        time.sleep(1)
        fp.close()
    view_text(json_openai['choices'][0]['message']['content'])
# view images on sd card to re-send to OpenAI
def load_image(bit, file):
    bit.fill(0b00000_000000_00000)  # fill with a middle grey
    decoder.open(file)
    decoder.decode(bit, scale=0, x=0, y=0)
    pycam.blit(bit, y_offset=32)
    pycam.display.refresh()

print()
print("Connecting to WiFi")
wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
print("Connected to WiFi")
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

palette = displayio.Palette(1)
palette[0] = 0x000000
decoder = JpegDecoder()
# used for showing images from sd card
bitmap = displayio.Bitmap(240, 176, 65535)

pycam = adafruit_pycamera.PyCamera()
pycam.mode = 0  # only mode 0 (JPEG) will work in this example

# Resolution of 320x240 is plenty for OpenAI
pycam.resolution = 1  # 0-12 preset resolutions:
#                      0: 240x240, 1: 320x240, 2: 640x480, 3: 800x600, 4: 1024x768,
#                      5: 1280x720, 6: 1280x1024, 7: 1600x1200, 8: 1920x1080, 9: 2048x1536,
#                      10: 2560x1440, 11: 2560x1600, 12: 2560x1920
# pycam.led_level = 1  # 0-4 preset brightness levels
# pycam.led_color = 0  # 0-7  preset colors: 0: white, 1: green, 2: yellow, 3: red,
#                                          4: pink, 5: blue, 6: teal, 7: rainbow
pycam.effect = 0  # 0-7 preset FX: 0: normal, 1: invert, 2: b&w, 3: red,
#                                  4: green, 5: blue, 6: sepia, 7: solarize
# sort image files by numeric order
all_images = [
    f"/sd/{filename}"
    for filename in os.listdir("/sd")
    if filename.lower().endswith(".jpg")
    ]
all_images.sort(key=lambda f: int(''.join(filter(str.isdigit, f))))
# add label for selected prompt
rect = vectorio.Rectangle(pixel_shader=palette, width=240, height=20, x=0, y=0)
prompt_txt = label.Label(
            terminalio.FONT, text=prompt_labels[prompt_index], color=0xFF0055, x=10, y=15, scale=2
        )
# pylint: disable=protected-access
pycam._botbar.append(rect)
pycam._botbar.append(prompt_txt)
# pylint: enable=protected-access
pycam.display.refresh()

view = False
new_prompt = False
file_index = -1

while True:
    if new_prompt:
        pycam.display_message("SEND?")
    if not view:
        if not new_prompt:
            pycam.blit(pycam.continuous_capture())
    pycam.keys_debounce()
    if pycam.shutter.long_press:
        pycam.autofocus()
    if pycam.shutter.short_count:
        try:
            pycam.display_message("snap", color=0x00DD00)
            pycam.capture_jpeg()
            pycam.live_preview_mode()
        except TypeError as exception:
            pycam.display_message("Failed", color=0xFF0000)
            time.sleep(0.5)
            pycam.live_preview_mode()
        except RuntimeError as exception:
            pycam.display_message("Error\nNo SD Card", color=0xFF0000)
            time.sleep(0.5)
        all_images = [
        f"/sd/{filename}"
        for filename in os.listdir("/sd")
        if filename.lower().endswith(".jpg")
        ]
        all_images.sort(key=lambda f: int(''.join(filter(str.isdigit, f))))
        the_image = all_images[-1]
        pycam.display_message("OpenAI..", color=0x00DD00)
        send_img(the_image, prompts[prompt_index])
        view = True

    if pycam.up.fell:
        prompt_index = (prompt_index - 1) % num_prompts
        prompt_txt.text = prompt_labels[prompt_index]
        pycam.display.refresh()

    if pycam.down.fell:
        prompt_index = (prompt_index + 1) % num_prompts
        prompt_txt.text = prompt_labels[prompt_index]
        pycam.display.refresh()

    if pycam.right.fell:
        if new_prompt:
            file_index = (file_index - -1) % -len(all_images)
            filename = all_images[file_index]
            load_image(bitmap, filename)
        else:
            prompt_index = (prompt_index + 1) % num_prompts
            prompt_txt.text = prompt_labels[prompt_index]
            pycam.display.refresh()

    if pycam.left.fell:
        if new_prompt:
            file_index = (file_index + -1) % -len(all_images)
            filename = all_images[file_index]
            load_image(bitmap, filename)
        else:
            prompt_index = (prompt_index - 1) % num_prompts
            prompt_txt.text = prompt_labels[prompt_index]
            pycam.display.refresh()

    if pycam.select.fell:
        if not new_prompt:
            file_index = -1
            new_prompt = True
            filename = all_images[file_index]
            load_image(bitmap, filename)
        else:
            new_prompt = False
            pycam.display.refresh()

    if pycam.ok.fell:
        if view:
            pycam.splash.pop()
            pycam.splash.pop()
            pycam.display.refresh()
            view = False
        if new_prompt:
            pycam.display_message("OpenAI..", color=0x00DD00)
            send_img(filename, prompts[prompt_index])
            new_prompt = False
            view = True
