"""
'mib_button_press_pwm.py'.

=================================================
fade a led in and out using two buttons
"""
import time
import digitalio
import board
import pulseio


led = pulseio.PWMOut(board.D13)
btn1 = digitalio.DigitalInOut(board.D3)
btn2 = digitalio.DigitalInOut(board.D2)
btn1.switch_to_input()
btn2.switch_to_input()


while True:
    BRIGHTNESS = led.duty_cycle
    # If button
    if not btn1.value:
        BRIGHTNESS += 100
    if not btn2.value:
        BRIGHTNESS -= 100
    BRIGHTNESS = max(0, BRIGHTNESS)
    BRIGHTNESS = min(44000, BRIGHTNESS)
    led.duty_cycle = BRIGHTNESS
    time.sleep(0.001)
