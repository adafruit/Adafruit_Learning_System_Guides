import time
import board
import simpleio
import pulseio

# PWM is not available on Trinket D1 
speaker_pin = board.D2  # PWM speaker using simpleio interface on D2 
pwm_leds = board.D4     # PWM (fading) LEDs are connected on D0 
pwm = pulseio.PWMOut(pwm_leds, frequency=256, duty_cycle=50)

# wait for vibration sensor detect

# LEDs start high and fade down
brightness = 2 ** 15 
fade_amount = 2 ** 13

# Super Mario Bros. Coin Sound with LED fade out
pwm.duty_cycle = brightness
time.sleep(.15)
simpleio.tone(speaker_pin, 988, 0.083) # tone1 - B5
brightness -= fade_amount
pwm.duty_cycle = brightness 
simpleio.tone(speaker_pin, 1319, 0.83) # tone2 - E6
time.sleep(.15)
brightness -= fade_amount
pwm.duty_cycle = brightness 
time.sleep(.15)
pwm.duty_cycle = 0
