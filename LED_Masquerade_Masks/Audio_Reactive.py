import time

import analogio
import board
import pwmio

sampleWindow = 0.033  # Sample window width (0.033 sec = 33 mS = ~30 Hz)
ledPin = board.D0  # Pin where LEDs are connected (PWM not avail on D1)
micPin = board.A1  # Microphone 'OUT' is connected here

mic = analogio.AnalogIn(micPin)
pwm = pwmio.PWMOut(ledPin, frequency=1000, duty_cycle=0)

while True:
    # Listen to mic for short interval, recording min & max signal
    signalMin = 65535
    signalMax = 0
    startTime = time.monotonic()
    while (time.monotonic() - startTime) < sampleWindow:
        signal = mic.value
        if signal < signalMin:
            signalMin = signal
        if signal > signalMax:
            signalMax = signal

    peakToPeak = signalMax - signalMin  # Audio amplitude
    n = (peakToPeak - 250) * 4  # Remove low-level noise, boost
    if n > 65535:
        n = 65535  # Limit to valid PWM range
    elif n < 0:
        n = 0
    pwm.duty_cycle = n  # And send to LED as PWM level
