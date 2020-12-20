import time
import terminalio
from adafruit_magtag.magtag import MagTag

magtag = MagTag()
magtag.peripherals.neopixel_disable = False

magtag.add_text(
    text_font=terminalio.FONT,
    text_position=(140, 55),
    text_scale=7,
    text_anchor_point=(0.5, 0.5),
)

magtag.set_text("00:00")

# Function that makes the neopixels display the seconds left
def update_neopixels(seconds):
    n = seconds // 15
    for j in range(n):
        magtag.peripherals.neopixels[3 - j] = (128, 0, 0)
    magtag.peripherals.neopixels[3 - n] = (int(((seconds / 15) % 1) * 128), 0, 0)


alarm_set = False
while True:
    if not alarm_set:
        # Set the timer to 1 minute
        if magtag.peripherals.button_a_pressed:
            alarm_time = 60
            alarm_set = True
            start = time.time()
            magtag.set_text("01:00")
            last_set = 60
            magtag.peripherals.neopixels.fill((128, 0, 0))

        # Set the timer to 5 minutes
        elif magtag.peripherals.button_b_pressed:
            alarm_time = 300
            alarm_set = True
            start = time.time()
            magtag.set_text("05:00")
            last_set = 300
            magtag.peripherals.neopixels.fill((128, 0, 0))

        # Set the timer to 20 minutes
        elif magtag.peripherals.button_c_pressed:
            alarm_time = 1200
            alarm_set = True
            start = time.time()
            magtag.set_text("20:00")
            last_set = 1200
            magtag.peripherals.neopixels.fill((128, 0, 0))

    else:
        remaining = alarm_time - (time.time() - start)
        print(remaining)
        if remaining == 0:
            magtag.peripherals.neopixels.fill((255, 0, 0))
            # Play alarm and flash neopixels to indicate the timer is done
            for i in range(2):
                magtag.peripherals.neopixels.fill((255, 0, 0))
                magtag.peripherals.play_tone(3000, 0.5)
                magtag.peripherals.neopixels.fill((0, 0, 0))
                time.sleep(0.1)
                magtag.peripherals.neopixels.fill((255, 0, 0))
                magtag.peripherals.play_tone(3000, 0.5)
                magtag.peripherals.neopixels.fill((0, 0, 0))
                time.sleep(0.5)
            alarm_set = False
            magtag.set_text("00:00")
            last_set = 0
            continue

        update_neopixels(remaining % 60)
        if remaining % 60 == 0 and remaining != last_set:
            magtag.set_text("{:02d}:00".format(remaining // 60))
            last_set = remaining

    # Reset the timer
    if magtag.peripherals.button_d_pressed:
        time.sleep(0.1)
        magtag.peripherals.neopixels.fill((0, 0, 0))
        time.sleep(0.1)
        magtag.peripherals.neopixels.fill((255, 0, 0))
        time.sleep(0.1)
        magtag.peripherals.neopixels.fill((0, 0, 0))
        time.sleep(0.1)

        alarm_set = False
        magtag.set_text("00:00")
