"""
Use PWM to fade an LED up and down using the potentiometer value as the duty cycle.

REQUIRED HARDWARE:
* potentiometer on pin GP26.
* LED on pin GP14.
"""
import board
import analogio
import pwmio

potentiometer = analogio.AnalogIn(board.GP26)
led = pwmio.PWMOut(board.GP14, frequency=1000)

while True:
    led.duty_cycle = potentiometer.value
