# Circuit Playground Express Simple Simon
#
# Game play based on information provided here:
# http://www.waitingforfriday.com/?p=586
#
# Author: Carter Nelson
# MIT License (https://opensource.org/licenses/MIT)
import time
import random
import math
import board
from analogio import AnalogIn
from adafruit_circuitplayground.express import cpx

FAILURE_TONE        = 100
SEQUENCE_DELAY      = 0.8
GUESS_TIMEOUT       = 3.0
DEBOUNCE            = 0.250
SEQUENCE_LENGTH = {
  1 : 8,
  2 : 14,
  3 : 20,
  4 : 31
}
SIMON_BUTTONS = {
  1 : { 'pads':(4,5), 'pixels':(0,1,2), 'color':0x00FF00, 'freq':415 },
  2 : { 'pads':(6,7), 'pixels':(2,3,4), 'color':0xFFFF00, 'freq':252 },
  3 : { 'pads':(1, ), 'pixels':(5,6,7), 'color':0x0000FF, 'freq':209 },
  4 : { 'pads':(2,3), 'pixels':(7,8,9), 'color':0xFF0000, 'freq':310 },  
}

def choose_skill_level():
    # Default
    skill_level = 1
    # Loop until button B is pressed
    while not cpx.button_b:
        # Button A increases skill level setting
        if cpx.button_a:
            skill_level += 1
            skill_level = skill_level if skill_level < 5 else 1
            # Indicate current skill level
            cpx.pixels.fill(0)
            for p in range(skill_level):
                cpx.pixels[p] = 0xFFFFFF
            time.sleep(DEBOUNCE)
    return skill_level

def new_game(skill_level):
    # Seed the random function with noise
    a4 = AnalogIn(board.A4)
    a5 = AnalogIn(board.A5)
    a6 = AnalogIn(board.A6)
    a7 = AnalogIn(board.A7)

    seed  = a4.value
    seed += a5.value
    seed += a6.value
    seed += a7.value

    random.seed(seed)    

    # Populate the game sequence
    return [random.randint(1,4) for i in range(SEQUENCE_LENGTH[skill_level])]

def indicate_button(button, duration):
    # Turn them all off
    cpx.pixels.fill(0)
    # Turn on the ones for the given button
    for p in button['pixels']:
        cpx.pixels[p] = button['color']
    # Play button tone
    if button['freq'] == None:
        time.sleep(duration)
    else:
        cpx.play_tone(button['freq'], duration)
    # Turn them all off again
    cpx.pixels.fill(0)
    
def show_sequence(sequence, step):
    # Set tone playback duration based on current location
    if step <= 5:
        duration = 0.420
    elif step <= 13:
        duration = 0.320
    else:
        duration = 0.220
    
    # Play back sequence up to current step
    for b in range(step):
        time.sleep(0.05)
        indicate_button(SIMON_BUTTONS[sequence[b]], duration)    

def cap_map(b):
    if b == 1: return cpx.touch_A1
    if b == 2: return cpx.touch_A2
    if b == 3: return cpx.touch_A3
    if b == 4: return cpx.touch_A4
    if b == 5: return cpx.touch_A5
    if b == 6: return cpx.touch_A6
    if b == 7: return cpx.touch_A7    
    
def get_button_press():
    # Loop over all the buttons
    for button in SIMON_BUTTONS.values():
        # Loop over each pad
        for pad in button['pads']:
            if cap_map(pad):
                indicate_button(button, DEBOUNCE)
                return button
    return None

def game_lost(step):
    # Show button that should have been pressed
    cpx.pixels.fill(0)
    for p in SIMON_BUTTONS[sequence[step]]['pixels']:
        cpx.pixels[p] = SIMON_BUTTONS[sequence[step]]['color']
   
    # Play sad sound :(
    cpx.play_tone(FAILURE_TONE, 1.5)
    
    # And just sit here until reset
    while True:
        pass
    
def game_won():
    # Play 'razz' special victory signal
    for i in range(3):
        indicate_button(SIMON_BUTTONS[4], 0.1)        
        indicate_button(SIMON_BUTTONS[2], 0.1)        
        indicate_button(SIMON_BUTTONS[3], 0.1)        
        indicate_button(SIMON_BUTTONS[1], 0.1)        
    indicate_button(SIMON_BUTTONS[4], 0.1)            
    indicate_button(SIMON_BUTTONS[2], 0.1)

    # Change tones to failure tone
    for button in SIMON_BUTTONS.values():
        button['freq'] = FAILURE_TONE
        
    # Continue for another 0.8 seconds
    for i in range(2):
        indicate_button(SIMON_BUTTONS[3], 0.1)        
        indicate_button(SIMON_BUTTONS[1], 0.1)        
        indicate_button(SIMON_BUTTONS[4], 0.1)        
        indicate_button(SIMON_BUTTONS[2], 0.1)        
    
    # Change tones to silence
    for button in SIMON_BUTTONS.values():
        button['freq'] = None
    
    # Loop lights forever
    while True:
        indicate_button(SIMON_BUTTONS[3], 0.1)        
        indicate_button(SIMON_BUTTONS[1], 0.1)        
        indicate_button(SIMON_BUTTONS[4], 0.1)        
        indicate_button(SIMON_BUTTONS[2], 0.1)                

# Initialize setup    
cpx.pixels.fill(0)
cpx.pixels[0] = 0xFFFFFF
skill_level = choose_skill_level()
sequence = new_game(skill_level)
current_step = 1

#Loop forever
while True:
    # Show sequence up to current step
    show_sequence(sequence, current_step)
    
    # Read player button presses
    for step in range(current_step):
        start_guess_time = time.monotonic()
        guess = None
        while (time.monotonic() - start_guess_time < GUESS_TIMEOUT) and (guess == None):
            guess = get_button_press()
        if not guess == SIMON_BUTTONS[sequence[step]]:
            game_lost(sequence[step])

    # Advance the game forward
    current_step += 1
    if current_step > len(sequence):
        game_won()
    
    # Small delay before continuing    
    time.sleep(SEQUENCE_DELAY)
