# SPDX-FileCopyrightText: 2021 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import random
import board
import pwmio
import displayio
import adafruit_imageload
from audiocore import WaveFile
from adafruit_motor import servo
from digitalio import DigitalInOut, Direction, Pull
from adafruit_matrixportal.matrix import Matrix

I2S_VERSION = False #  set to True if using I2S audio out

#  import the appropriate audio module
if I2S_VERSION:
    from audiobusio import I2SOut
else:
    from audioio import AudioOut

#  setup for down button on matrixportal
switch = DigitalInOut(board.BUTTON_DOWN)
switch.direction = Direction.INPUT
switch.pull = Pull.UP

#  setup for break beam sensor
break_beam = DigitalInOut(board.A1)
break_beam.direction = Direction.INPUT
break_beam.pull = Pull.UP

#  pwm for servo
servo_pwm = pwmio.PWMOut(board.A4, duty_cycle=2 ** 15, frequency=50)

#  servo setup
servo = servo.Servo(servo_pwm)
servo.angle = 90

#  import dreidel song audio file
wave_file = open("dreidel_song.wav", "rb")
wave = WaveFile(wave_file)

#  setup for audio out
if I2S_VERSION:
    audio = I2SOut(board.A2, board.A3, board.TX)
else:
    audio = AudioOut(board.A0)

#  setup for matrix display
matrix = Matrix(width=32, height=32)
display = matrix.display

group = displayio.Group()

#  import dreidel bitmap
dreidel_bit, dreidel_pal = adafruit_imageload.load("/dreidel.bmp",
                                                 bitmap=displayio.Bitmap,
                                                 palette=displayio.Palette)

dreidel_grid = displayio.TileGrid(dreidel_bit, pixel_shader=dreidel_pal,
                                 width=1, height=1,
                                 tile_height=32, tile_width=32,
                                 default_tile=0,
                                 x=0, y=0)

group.append(dreidel_grid)

#  show dreidel bitmap
display.root_group = group

timer = 0 #  time.monotonic() holder
spin = 0 #  index for tilegrid
speed = 0.1 #  rate that bitmap updates
clock = 0 #  initial time.monotonic() holder to act as time keeper
gimel = 3 #  bitmap index for gimel, the winning character
countdown = 5 #  countdown for length of game. default is 5 seconds
beam_state = False #  state machine for break beam
reset = False #  state for reset of game
dreidel = False #  state to track if dreidel game is running

clock = time.monotonic() #  initial time.monotonic()

while True:
    #  debouncing for break beam sensor
    if not break_beam.value and not beam_state:
        beam_state = True

    #  if the break beam sensor is triggered or the down button is pressed...
    if (not break_beam.value and beam_state) or not switch.value:
        #  update break beam state
        beam_state = False
        #  begin reset for game states
        reset = True
        print("pressed")
        #  quick delay
        time.sleep(0.1)

	#  if reset state...
    if reset:
        #  hold time.monotonic() value
        clock = time.monotonic()
        #  reset countdown
        countdown = 5
        #  choose random side of dreidel to begin spinning on
        spin = random.randint(0, 3)
        #  choose random speed spin the dreidel
        speed = random.uniform(0.05, 0.1)
        #  set game state to True
        dreidel = True
        #  turn off reset state
        reset = False

	#  if the game is running...
    if dreidel:
        #  play the dreidel song
        audio.play(wave)

        #  while the dreidel song is playing...
        while audio.playing:
            #  if more time has passed than the random delay setup in reset...
            if (timer + speed) < time.monotonic():
                #  dreidel grid index is set to spin value
                dreidel_grid[0] = spin
                #  spin is increased by 1
                spin += 1
                #  timer is updated to current time
                timer = time.monotonic()

                #  if a second has passed...
                if time.monotonic() > (clock + 1):
                    print(clock)
                    print(spin)
                    #  the delay is increased to slow down the dreidel
                    speed += 0.05
                    #  clock is set to current time
                    clock = time.monotonic()
                    #  countdown value is decreased by 1
                    countdown -= 1

                #  if countdown is 0 aka 5 seconds has passed since the start of game...
                if countdown == 0:
                    #  if the bitmap is showing gimel...
                    #  you win!
                    if spin is gimel:
                        #  the servo turns 90 degrees to dump out chocolate coins
                        servo.angle = 0
                        #  2 second delay
                        time.sleep(2)
                        #  servo turns back to default position
                        for i in range(0, 90, 2):
                            servo.angle = i
                            time.sleep(0.1)
                        #  ensures servo is in default position
                        servo.angle = 90
                        #  stop playing the dreidel song
                        audio.stop()
                        #  game state is turned off
                        dreidel = False

                    #  if you didn't win...
                    else:
                        #  the dreidel song stops
                        audio.stop()
                        #  game state is turned off
                        dreidel = False

                #  if you are at the end of the sprite sheet...
                if spin > 3:
                    #  index is reset to 0
                    spin = 0
