# Adafruit-Crickit-Mini-Smart-Home-MQTT
Arduino based Mini Smart Home

https://learn.adafruit.com/mini-smart-home-with-huzzah/overview

MQTT Feeds:

1. Door Lock
   - house/lock
     - State: LOCK or UNLOCK

2. Window Fan
   - house/fan
     - State: ON or OFF
   - house/fan/speed
     - State: 0 to 255
3. RGB LED 1
   - house/led/one
     - State: ON or OFF
   - house/led/one/brightness
     - State: 0 to 255
   - house/led/one/color
     - State: three sets of 0 - 255 numbers separated by commas.
     - Template: “red,green,blue”
     - Example: 20,150,255
4. RGB LED 2
   - house/led/two
     - State: ON or OFF
   - house/led/two/brightness
     - State: 0 to 255
   - house/led/two/color
     - State: three sets of 0 - 255 numbers separated by commas.
     - Template: “red,green,blue”
     - Example: 20,150,255
5. RGB LED 3
   - house/led/three
     - State: ON or OFF
   - house/led/three/brightness
     - State: 0 to 255
   - house/led/three/color
     - State: three sets of 0 - 255 numbers separated by commas.
     - Template: “red,green,blue”
     - Example: 20,150,255
6. RGB LED 4
   - house/led/four
     - State: ON or OFF
   - house/led/four/brightness
     - State: 0 to 255
   - house/led/four/color
     - State: three sets of 0 - 255 numbers separated by commas.
     - Template: “red,green,blue”
     - Example: 20,150,255
7. RGB LED 5
   - house/led/five
     - State: ON or OFF
   - house/led/five/brightness
     - State: 0 to 255
   - house/led/five/color
     - State: three sets of 0 - 255 numbers separated by commas.
     - Template: “red,green,blue”
     - Example: 20,150,255
8. Light Level Sensor 
   - house/lux
     - State: 0 to 6000
9. Motion Sensor 
   - house/motion
     - State: MOVE or STILL
10. Door Sensor 
   - house/door
     - State: OPEN or CLOSED
