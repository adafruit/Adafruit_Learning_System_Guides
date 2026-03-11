# 📸 Memento Flex

**The Student "Flexible" Camera** — Memento Flex is a versatile, AI-powered smart camera built on [Adafruit MEMENTO](https://www.adafruit.com/product/5420).
 Designed for students, creators etc, it "flexes" between a standard digital camera, a scientific observation tool, and an AI-vision assistant.

## Features

* **AI-Powered Insights:** Connects to OpenRouter to provide real-time image descriptions.
* **Smart Time-Lapse:** Includes a "Low Power" mode that dims the screen to save battery during long observations.
* **Animation Suite:** Support for both looping GIFs and Onion-skinning Stop Motion.
* **Automated Sync:** Fetches local time automatically via NTP over Wi-Fi.
* **Custom Text UI:** Result text is intelligently wrapped and scaled to be readable on the 240x240 display.

---

## Setup Instructions

### 1. Requirements
* **Hardware:** Adafruit MEMENTO Camera board & a microSD card.
* **Firmware:** [CircuitPython 10.x](https://circuitpython.org/board/adafruit_memento_camera/)
* **API Key:** A free or paid key from [OpenRouter.ai](https://openrouter.ai/).

### 2. Configuration
Create a `settings.toml` file on your `CIRCUITPY` drive. **Do not share this file publicly!**

```toml
# Wi-Fi Settings
CIRCUITPY_WIFI_SSID = "Your_Network_Name"
CIRCUITPY_WIFI_PASSWORD = "Your_Password"

# AI & Time Settings
OPENROUTER_API_KEY = "your_key_here"
TZ = "Your_timezone"
UTC_OFFSET = Your_Offset
AI_PROMPT = "Describe this image in 5-10 simple words."
```
## Installation

1. **Upload Code:** Copy the `code.py` file from this repository onto your MEMENTO's `CIRCUITPY` drive.
2. **Install Libraries:** Ensure your `lib` folder on the MEMENTO contains the necessary Adafruit libraries. 
   > **Note:** You can find these in the [Adafruit CircuitPython Library Bundle](https://circuitpython.org/libraries).
3. **Configure:** Make sure your `settings.toml` is set up with your Wi-Fi and API credentials.
4. **Restart:** Press the **Reset** button on the top of your MEMENTO to start the **Flex** software.

## Controls

| Button | Action |
| :--- | :--- |
| **Shutter (Click)** | Snap Photo / Record GIF / Capture Frame |
| **Shutter (Long)** | Trigger Autofocus |
| **OK Button** | **JPEG Mode:** Analyze with AI <br> **LAPS Mode:** Start/Stop Time-lapse |
| **D-Pad** | Navigate Settings (Resolution, Effects, Mode, etc.) |
| **Select Button** | Change Sub-modes (e.g., High/Low Power in LAPS) |

---

## Example Images
   ![WhatsApp Image 2026-02-13 at 12 00 34 PM (2)](https://github.com/user-attachments/assets/ef1e0bcc-88d9-4629-a746-1fd2d40b58cd)
![WhatsApp Image 2026-02-13 at 12 00 34 PM (1)](https://github.com/user-attachments/assets/24b47181-d589-489e-b888-24d7f6838c1d)
![WhatsApp Image 2026-02-13 at 12 00 34 PM](https://github.com/user-attachments/assets/b5d39002-fbf5-4e58-b798-71cf98e048fe)

**Image captured for AI powered mode(compressed)**

<img width="240" height="240" alt="image" src="https://github.com/user-attachments/assets/61a8794c-1cbc-4270-b97e-0c92974cf8a3" />


## 📜 Credits

 ([Adafruit Industries](https://www.adafruit.com/)).
* **Modifications & "Flex" Features:** [Gautham Chenoth Praveen](https://github.com/Gautham-8066).

* **References:** [OpenAI Image Descriptors with MEMENTO By Liz Clark](https://learn.adafruit.com/openai-image-descriptors-with-memento) , [Remote Shutter Button for MEMENTO By Ruiz Brothers](https://learn.adafruit.com/memento-shutter) , https://learn.adafruit.com/adafruit-memento-camera-board/fancy-camera.

---

