# SPDX-FileCopyrightText: 2024 Bill Binko
# SPDX-License-Identifier: MIT

#Customizable per Analog Joystick - these are good for Adafruit Thumbsticks to start
#How big the "dead zone" is in the center of the joystick
deadPct = .10

#Vertical limits
#Reading at "down"
lowVert = 0
#"up"
highVert = 65000
#set to -1 to invert the vertical axis
invertVert = -1

#Horizontal limits
lowHor= 0
highHor = 65000
#set to -1 to invert the horizontal axis
invertHor = 1

#How much to move a mouse a full-throw
#(10 works well on a PC, and 2 is good for iOS AssitiveTouch)
maxMouseMove=8
