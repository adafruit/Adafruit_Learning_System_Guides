# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark Adafruit Industries
# SPDX-License-Identifier: MIT
"""Live camera preview on a MIPI DSI display.

Metro ESP32-P4 + Raspberry Pi Camera v1.3 (OV5647) + 7-inch Touch Display 2.

The display runs at its native portrait orientation in 16-bit color, so each
camera frame is copied straight to the screen.
"""

import board
import displayio
import mipicsi
import videocore
import adafruit_ov5647
import raspberry_pi_touch_display_2 as display_init

i2c = board.I2C()
display = display_init.make_display(i2c, color_depth=16, rotation=0)

sensor = adafruit_ov5647.OV5647(i2c, reset_pin=board.CAMERA_RESET)
sensor.mode = adafruit_ov5647.Mode.R640X480
camera = mipicsi.Camera(sensor, output_format=mipicsi.PixelFormat.RGB565)

frame = bytearray(sensor.width * sensor.height * 2)
video = videocore.VideoBuffer(frame)
video.play(camera)

video.x = (display.width - sensor.width) // 2
video.y = (display.height - sensor.height) // 2
root = displayio.Group()
root.append(video)
display.root_group = root

while True:
    pass
