import time

import adafruit_apds9960.apds9960
import board
import digitalio
import ulab
import ulab.filter

# Blank the screen.  Scrolling text causes unwanted delays.
import displayio
d = displayio.Group()
board.DISPLAY.show(d)

# Filter computed at https://fiiir.com/
# Sampling rate: 8Hz
# Cutoff freqency: 0.5Hz
# Transition bandwidth 0.25Hz
# Window type: Regular
# Number of coefficients: 31
# Manually trimmed to 16 coefficients
taps = ulab.array([
    +0.861745279666917052/2,
    -0.134728583242092248,
    -0.124472980501612152,
    -0.108421190967457198,
    -0.088015688587190874,
    -0.065052714580474319,
    -0.041490993500537393,
    -0.019246940463156042,
    -0.000000000000000005,
    +0.014969842582454691,
    +0.024894596100322432,
    +0.029569415718397409,
    +0.029338562862396955,
    +0.025020274838643962,
    +0.017781854357373172,
    +0.008981905549472832,
])

# How much reflected light is required before pulse sensor activates
# These values are triggered when I bring my finger within a half inch.
# The sensor works when the finger is pressed lightly against the sensor.
PROXIMITY_THRESHOLD_HI = 225
PROXIMITY_THRESHOLD_LO = 215

# These constants control how much the sensor amplifies received light
APDS9660_AGAIN_1X = 0
APDS9660_AGAIN_4X = 1
APDS9660_AGAIN_16X = 2
APDS9660_AGAIN_64X = 3

# How often we are going to poll the sensor (If you change this, you need
# to change the filter above and the integration time below)
dt = 125000000 # 8Hz, 125ms

# Wait until after deadline_ns has passed
def sleep_deadline(deadline_ns):
    while time.monotonic_ns() < deadline_ns:
        pass

# Compute a high resolution crossing-time estimate for the sample, using a
# linear model
def estimated_cross_time(y0, y1, t0):
    m = (y1 - y0) / dt
    return t0 + round(-y1 / m)

i2c = board.I2C()
sensor = adafruit_apds9960.apds9960.APDS9960(i2c)
white_leds = digitalio.DigitalInOut(board.WHITE_LEDS)
white_leds.switch_to_output(False)

def main():
    sensor.enable_proximity = True
    while True:
        # Wait for user to put finger over sensor
        while sensor.proximity < PROXIMITY_THRESHOLD_HI:
            time.sleep(.01)

        # After the finger is sensed, set up the color sensor
        sensor.enable_color = True
        # This sensor integration time is just a little bit shorter than 125ms,
        # so we should always have a fresh value when we ask for it, without
        # checking if a value is available.
        sensor.integration_time = 220
        # In my testing, 64X gain saturated the sensor, so this is the biggest
        # gain value that works properly.
        sensor.color_gain = APDS9660_AGAIN_4X
        white_leds.value = True

        # And our data structures
        # The most recent data samples, equal in number to the filter taps
        data = ulab.zeros(len(taps))
        # The filtered value on the previous iteration
        old_value = 1
        # The times of the most recent pulses registered.  Increasing this number
        # makes the estimation more accurate, but at the expense of taking longer
        # before a pulse number can be computed
        pulse_times = []
        # The estimated heart rate based on the recent pulse times
        rate = None
        # the number of samples taken
        n = 0

        # Rather than sleeping for a fixed duration, we compute a deadline
        # in nanoseconds and wait for the new deadline time to arrive.  This
        # helps the long term frequency of measurements better match the desired
        # frequency.
        t0 = deadline = time.monotonic_ns()
        # As long as their finger is over the sensor, capture data
        while sensor.proximity >= PROXIMITY_THRESHOLD_LO:
            deadline += dt
            sleep_deadline(deadline)
            value = sum(sensor.color_data) # Combination of all channels
            ulab.numerical.roll(data, 1)
            data[-1] = value
            # Compute the new filtered variable by applying the filter to the
            # recent data samples
            filtered = ulab.numerical.sum(data * taps)

            # We gathered enough data to fill the filters, and
            # the light value crossed the zero line in the positive direction
            # Therefore we need to record a pulse
            if n > len(taps) and old_value < 0 and filtered >= 0:
                # This crossing time is estimated, but it increases the pulse
                # estimate resolution quite a bit.  If only the nearest 1/8s
                # was used for pulse estimation, the smallest pulse increment
                # that can be measured is 7.5bpm.
                cross = estimated_cross_time(old_value, filtered, deadline)
                # store this pulse time (in seconds since sensor-touch)
                pulse_times.append((cross - t0) * 1e-9)
                # and maybe delete an old pulse time
                del pulse_times[:-10]
                # And compute a rate based on the last recorded pulse times
                if len(pulse_times) > 1:
                    rate = 60/(pulse_times[-1]-pulse_times[0])*(len(pulse_times)-1)
            old_value = filtered

            # We gathered enough data to fill the filters, so report the light
            # value and possibly the estimated pulse rate
            if n > len(taps):
                print((filtered, rate))
            n += 1

        # Turn off the sensor and the LED and go back to the top for another run
        sensor.enable_color = False
        white_leds.value = False
        print()
main()
