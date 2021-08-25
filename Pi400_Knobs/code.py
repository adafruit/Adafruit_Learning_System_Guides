# SPDX-FileCopyrightText: 2021 John Park for Adafruit Industries
# SPDX-License-Identifier: MIT

#!/usr/bin/env python

import time
import board
from adafruit_simplemath import map_range
import adafruit_pcf8591.pcf8591 as PCF
from adafruit_pcf8591.analog_in import AnalogIn
from pythonosc import udp_client


sender = udp_client.SimpleUDPClient("127.0.0.1", 4560)
sender.send_message("/trigger/prophet", [43, 110, 1, 0.7])

i2c = board.I2C()
pcf = PCF.PCF8591(i2c)

pcf_in_0 = AnalogIn(pcf, PCF.A0)
pcf_in_1 = AnalogIn(pcf, PCF.A1)
pcf_in_2 = AnalogIn(pcf, PCF.A2)
pcf_in_3 = AnalogIn(pcf, PCF.A3)

try:
    while True:
        osc_0_val = int(255 - (pcf_in_0.value / 256))  # convert values to useful ranges
        osc_1_val = int(255 - (pcf_in_1.value / 256))
        osc_2_val = int(255 - (pcf_in_2.value / 256))
        osc_3_val = int(255 - (pcf_in_3.value / 256))

        osc_note_val = int(
            map_range(osc_0_val, 0, 255, 43, 58)
        )  # map values to relevant ranges
        osc_cutoff_val = int(map_range(osc_1_val, 0, 255, 30, 110))
        osc_sustain_val = map_range(osc_2_val, 0, 255, 0.2, 2)
        osc_gain_val = map_range(osc_3_val, 0, 255, 0, 1.0)

        # print((osc_note_val, osc_cutoff_val, osc_sustain_val, osc_gain_val))  # for plotter
        sender.send_message(
            "/trigger/prophet",
            [osc_note_val, osc_cutoff_val, osc_sustain_val, osc_gain_val],
        )

        time.sleep(0.001)

except KeyboardInterrupt:
    print("done")
