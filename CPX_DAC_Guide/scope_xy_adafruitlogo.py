### scope-xy-adafruitlogo v1.0

"""Output a logo to an oscilloscope in X-Y mode on an Adafruit M4
board like Feather M4 or PyGamer (best to disconnect headphones).
"""

### copy this file to PyGamer (or other M4 board) as code.py

### MIT License

### Copyright (c) 2019 Kevin J. Walters

### Permission is hereby granted, free of charge, to any person obtaining a copy
### of this software and associated documentation files (the "Software"), to deal
### in the Software without restriction, including without limitation the rights
### to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
### copies of the Software, and to permit persons to whom the Software is
### furnished to do so, subject to the following conditions:

### The above copyright notice and this permission notice shall be included in all
### copies or substantial portions of the Software.

### THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
### IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
### FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
### AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
### LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
### OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
### SOFTWARE.

import time
import math
import array

import board
import audioio
import analogio

### Vector data for logo
import adafruit_logo_vector

VECTOR_POINT_SPACING = 3

def addpoints(points, min_dist):
    """Add extra points to any lines if length is greater than min_dist"""

    newpoints = []
    original_len = len(points)
    for pidx in range(original_len):
        px1, py1 = points[pidx]
        px2, py2 = points[(pidx + 1) % original_len]

        ### Always keep the original point
        newpoints.append((px1, py1))

        diff_x = px2 - px1
        diff_y = py2 - py1
        dist = math.sqrt(diff_x ** 2 + diff_y ** 2)
        if dist > min_dist:
            ### Calculate extra intermediate points plus one
            extrasp1 = int(dist // min_dist) + 1
            for extra_idx in range(1, extrasp1):
                ratio = extra_idx / extrasp1
                newpoints.append((px1 + diff_x * ratio,
                                  py1 + diff_y * ratio))
        ### Two points define a straight line
        ### so no need to connect final point back to first
        if original_len == 2:
            break

    return newpoints

### pylint: disable=invalid-name
### If logo is off centre then correct it here
if adafruit_logo_vector.offset_x != 0 or adafruit_logo_vector.offset_y != 0:
    data = []
    for part in adafruit_logo_vector.data:
        newpart = []
        for point in part:
            newpart.append((point[0] - adafruit_logo_vector.offset_x,
                            point[1] - adafruit_logo_vector.offset_y))
        data.append(newpart)
else:
    data = adafruit_logo_vector.data


### Add intermediate points to make line segments for each part
### look like continuous lines on x-y oscilloscope output
display_data = []
for part in data:
    display_data.extend(addpoints(part, VECTOR_POINT_SPACING))

### PyPortal DACs seem to stop around 53000 and there's 2 100 ohm resistors
### on output so maybe large values aren't good idea?
### 32768 and 32000 exhibit this bug but 25000 so far appears to be a
### workaround, albeit a mysterious one
### https://github.com/adafruit/circuitpython/issues/1992
### Using "h" for audioio.RawSample() DAC range will be 20268 to 45268
dac_x_min = 0
dac_y_min = 0
dac_x_max = 25000
dac_y_max = 25000
dac_x_mid = dac_x_max // 2
dac_y_mid = dac_y_max // 2

### Convert the points into format suitable for audio library
### and scale to the DAC range used by the library
### Intentionally using "h" data representation here as this happens to
### cause the CircuitPython audio libraries to make a copy of
### rawdata which is useful to allow animating code to modify rawdata
### without affecting current DAC output
rawdata = array.array("h", (2 * len(display_data)) * [0])

range_x = 512.0
range_y = 512.0
halfrange_x = range_x / 2
halfrange_y = range_y / 2
mid_x = 256.0
mid_y = 256.0
mult_x = dac_x_max / range_x
mult_y = dac_y_max / range_y

### https://github.com/adafruit/circuitpython/issues/1992
print("length of rawdata", len(rawdata))

use_wav = True
poor_wav_bug_workaround = False
leave_wav_looping = True

### A0 will be x, A1 will be y
if use_wav:
    print("Using audioio.RawSample for DACs")
    dacs = audioio.AudioOut(board.A0, right_channel=board.A1)
else:
    print("Using analogio.AnalogOut for DACs")
    a0 = analogio.AnalogOut(board.A0)
    a1 = analogio.AnalogOut(board.A1)

### 10Hz is about ok for AudioOut, optimistic for AnalogOut
frame_t = 1/10
prev_t = time.monotonic()
angle = 0  ### in radians
frame = 1
while True:
    ##print("Transforming data for frame:", frame, "at", prev_t)

    ### Rotate the points of the vector graphic around its centre
    idx = 0
    sine = math.sin(angle)
    cosine = math.cos(angle)
    for px, py in display_data:
        pcx = px - mid_x
        pcy = py - mid_y
        dac_a0_x = round((-sine * pcx + cosine * pcy + halfrange_x) * mult_x)
        ### Keep x position within legal values (if needed)
        ##dac_a0_x = min(dac_a0_x, dac_x_max)
        ##dac_a0_x = max(dac_a0_x, 0)
        dac_a1_y = round((sine * pcy + cosine * pcx + halfrange_y) * mult_y)
        ### Keep y position within legal values (if needed)
        ##dac_a1_y = min(dac_a1_y, dac_y_max)
        ##dac_a1_y = max(dac_a1_y, 0)
        rawdata[idx] = dac_a0_x - dac_x_mid      ### adjust for "h" array
        rawdata[idx + 1] = dac_a1_y - dac_y_mid  ### adjust for "h" array
        idx += 2

    if use_wav:
        ### 200k (maybe 166.667k) seems to be practical limit
        ### 1M permissible but seems same as around 200k
        output_wave = audioio.RawSample(rawdata,
                                        channel_count=2,
                                        sample_rate=200 * 1000)

        ### The image may "warp" sometimes with loop=True due to a strange bug
        ### https://github.com/adafruit/circuitpython/issues/1992
        if poor_wav_bug_workaround:
            while True:
                dacs.play(output_wave)
                if time.monotonic() - prev_t >= frame_t:
                    break
        else:
            dacs.play(output_wave, loop=True)
            while time.monotonic() - prev_t < frame_t:
                pass
            if not leave_wav_looping:
                dacs.stop()
    else:
        while True:
            ### This gives a very flickery image with 4932 points
            ### slight flicker at 2552
            ### might be ok for 1000
            for idx in range(0, len(rawdata), 2):
                a0.value = rawdata[idx]
                a1.value = rawdata[idx + 1]
            if time.monotonic() - prev_t >= frame_t:
                break
    prev_t = time.monotonic()
    angle += math.pi / 180 * 3 ### 72 degrees per frame
    frame += 1
