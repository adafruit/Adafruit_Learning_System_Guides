from adafruit_circuitplayground.express import cpx

touchpad_to_color = {
    "touch_A1": (255, 0, 0),  # red
    "touch_A2": (255, 40, 0),  # orange
    "touch_A3": (255, 150, 0),  # yellow
    "touch_A4": (0, 255, 0),  # green
    "touch_A5": (0, 0, 255),  # blue
    "touch_A6": (180, 0, 255),  # purple
    "touch_A7": (0, 0, 0),  # off
}

while True:
    for touchpad in touchpad_to_color:
        if getattr(cpx, touchpad):
            cpx.pixels.fill(touchpad_to_color[touchpad])
