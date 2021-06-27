import time
import board
import analogio
import usb_midi
import adafruit_midi
import neopixel
from adafruit_midi.control_change import ControlChange

pixels = neopixel.NeoPixel(board.NEOPIXEL, 2, brightness=1)

slider = analogio.AnalogIn(board.POTENTIOMETER)
position = slider.value  # ranges from 0-65535


midi = adafruit_midi.MIDI(
    midi_in=usb_midi.ports[0], in_channel=0, midi_out=usb_midi.ports[1], out_channel=0
)

last_cc_val = 0


# ------- Hue/Sat/Val function to convert to RGB  ------ #
def hsv2rgb(h, s, v):
    """
    Convert H,S,V in 0-255,0-255,0-255 format
    to R,G,B in 0-255,0-255,0-255 format
    Converts an integer HSV (value range from 0 to 255) to an RGB tuple
    """
    if s == 0:
        return v, v, v
    h = h/255
    s = s/255
    v = v/255
    i = int(h * 6.0)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i = i % 6
    if i == 0:
        r, g, b = v, t, p
    if i == 1:
        r, g, b = q, v, p
    if i == 2:
        r, g, b = p, v, t
    if i == 3:
        r, g, b = p, q, v
    if i == 4:
        r, g, b = t, p, v
    if i == 5:
        r, g, b = v, p, q
    return int(r * 255), int(g * 255), int(b * 255)


hue_a = 0
sat_a = 255
val_a = 255
color_a = hsv2rgb(hue_a, sat_a, val_a)

hue_b = 127
sat_b = 255
val_b = 255
color_b = hsv2rgb(hue_a, sat_a, val_a)

pixels[0] = color_a
pixels[1] = color_b
pixels.show()

while True:
    cc_val = slider.value // 512  # make 0-127 range for MIDI CC

    if abs(cc_val - last_cc_val) > 2:
        print(cc_val)
        last_cc_val = cc_val
        mod_wheel = ControlChange(1, cc_val)
        midi.send(mod_wheel)
        color_a = hsv2rgb(cc_val, sat_a, val_a)
        pixels[0] = color_a
        color_b = hsv2rgb(cc_val, sat_b, val_b)
        pixels[1] = color_b
        time.sleep(0.001)
