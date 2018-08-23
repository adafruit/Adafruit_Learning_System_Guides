import time
from adafruit_crickit import crickit

print("Heating Pad Demo")

# For signal control, we'll chat directly with seesaw
ss = crickit.seesaw
TMP36 = crickit.SIGNAL1  # TMP36 connected to signal port 1 & ground
POT = crickit.SIGNAL8    # potentiometer connected to signal port 8 & ground

heating_pad = crickit.dc_motor_2

while True:

    voltage = ss.analog_read(TMP36) * 3.3 / 1024.0
    tempC = (voltage - 0.5) * 100.0
    tempF = (tempC * 9.0 / 5.0) + 32.0

    heat_value = ss.analog_read(POT) / 1023.0

    print((tempF, heat_value))

    heating_pad.throttle = heat_value  # set heat value to Motor throttle value

    time.sleep(0.25)
