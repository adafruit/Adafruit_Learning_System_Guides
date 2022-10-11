# SPDX-FileCopyrightText: 2022 Matt Desmarais for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import ssl
import microcontroller
import socketpool
import wifi
import board
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT
import digitalio
from adafruit_debouncer import Debouncer

#setup buzzer1
buzzer1 = digitalio.DigitalInOut(board.D13)
buzzer1.direction = digitalio.Direction.OUTPUT

#setup buzzer2
buzzer2 = digitalio.DigitalInOut(board.D11)
buzzer2.direction = digitalio.Direction.OUTPUT

#setup left door switch
leftdoor = digitalio.DigitalInOut(board.D5)
leftdoor.direction = digitalio.Direction.INPUT
leftdoor.pull = digitalio.Pull.UP
leftswitch = Debouncer(leftdoor)

#setup right door switch
rightdoor = digitalio.DigitalInOut(board.D9)
rightdoor.direction = digitalio.Direction.INPUT
rightdoor.pull = digitalio.Pull.UP
rightswitch = Debouncer(rightdoor)

#setup motion sensor
pir = digitalio.DigitalInOut(board.D6)
pir.direction = digitalio.Direction.INPUT
motion = Debouncer(pir)

try:
    from secrets import secrets
except ImportError:
    print("WiFi and Adafruit IO credentials are kept in secrets.py - please add them there!")
    raise

# Add your Adafruit IO Username and Key to secrets.py
# (visit io.adafruit.com if you need to create an account,
# or if you need to obtain your Adafruit IO key.)
aio_username = secrets["aio_username"]
aio_key = secrets["aio_key"]

# WiFi
try:
    print("Connecting to %s" % secrets["ssid"])
    wifi.radio.connect(secrets["ssid"], secrets["password"])
    print("Connected to %s!" % secrets["ssid"])
# Wi-Fi connectivity fails with error messages, not specific errors, so this except is broad.
except Exception as e:  # pylint: disable=broad-except
    print("Failed to connect to WiFi. Error:", e, "\nBoard will restart in 5 seconds.")
    time.sleep(5)
    microcontroller.reset()

# Create a socket pool
pool = socketpool.SocketPool(wifi.radio)

# Initialize a new MQTT Client object
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    username=secrets["aio_username"],
    password=secrets["aio_key"],
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)

# Define callback functions which will be called when certain events happen.
def connected():
    print("Connected to Adafruit IO!  Listening for Freezer changes...")

# Initialize Adafruit IO MQTT "helper"
io = IO_MQTT(mqtt_client)

# Set up the callback methods above
io.on_connect = connected

#start time for timed uploads
start = int(time.time()/300)
#door timers set start times to now
start1 = time.monotonic()
start2 = time.monotonic()
#door alarms set to False
prealarm = False
alarm1 = False
alarm2 = False

door1feed = "unit-6.door1"
door2feed = "unit-6.door2"
motionfeed = "unit-6.motion"
alarmfeed = "unit-6.alarm"
resolvedfeed = "unit-6.resolved"
#reconnectedfeed = "unit-6.reconnected"

#initial publishes all zeros
try:
    io.connect()
# Adafruit IO fails with internal error types and WiFi fails with specific messages.
# This except is broad to handle any possible failure.
except Exception as e:  # pylint: disable=broad-except
    print("Failed to get or send data, or connect. Error:", e,
          "\nBoard will restart in 20 seconds.")
    time.sleep(20)
    microcontroller.reset()
io.publish(alarmfeed, 0)
io.publish(resolvedfeed, 0)
#io.publish(reconnectedfeed, 1)
#time.sleep(.25)
#io.publish(reconnectedfeed, 0)

while True:
    try:
        # If Adafruit IO is not connected...
        if not io.is_connected:
            # Connect the client to the MQTT broker.
            print("Connecting to Adafruit IO...")
            io.connect()

        time.sleep(1)
        #update leftswitch
        leftswitch.update()
        #if door closed upload to IO
        if leftswitch.fell:
            print('left closed')
            io.publish(door1feed, 1)
            time.sleep(.25)
            io.publish(door1feed, 0)
        #if door opened upload to IO, set start1 to now
        if leftswitch.rose:
            print('left opened')
            io.publish(door1feed, 1)
            start1 = time.monotonic()
        #if door remains open
        if leftswitch.value:
            print('still left open')
        #if door remains closed, reset start1
        else:
            #door still closed reset timer
            print('still left closed')
            start1 = time.monotonic()

        #update rightswitch
        rightswitch.update()
        #if door closed upload to IO
        if rightswitch.fell:
            print('right closed')
            io.publish(door2feed, 1)
            time.sleep(.25)
            io.publish(door2feed, 0)
        #if door opened upload to IO, set start2 to now
        if rightswitch.rose:
            print('right opened')
            io.publish(door2feed, 1)
            start2 = time.monotonic()
        if rightswitch.value:
            print('still right open')
        #door still closed reset timer
        else:
            print('still right closed')
            start2 = time.monotonic()

        #if a door closes update both switches
        if rightswitch.fell or leftswitch.fell:
            rightswitch.update()
            leftswitch.update()
            #if both doors are closed
            if not rightswitch.value and not leftswitch.value:
                print('doors just closed')
                #if prelarm is true then set it to False
                if prealarm is True:
                    buzzer1.value = False
                #if an alarm is true then upload to IO alarm resolved
                if alarm1 or alarm2:
                    #publish 0 to alarm feed
                    io.publish(alarmfeed, 0)
                    #buzzers off/Alarms to False
                    buzzer1.value = False
                    buzzer2.value = False
                    alarm1 = False
                    alarm2 = False
                    #toggle alarm resolved feed to send email notification
                    io.publish(resolvedfeed, 1)
                    time.sleep(5)
                    io.publish(resolvedfeed, 0)

        #check motion sensor if there is no alarm
        if(alarm1 is False and alarm2 is False and prealarm is False):
            #update pir sensor
            motion.update()
            #if motion stopped
            if motion.fell:
                print('motion stopped')
                #publish 0 to motion feed
                io.publish(motionfeed, 1)
                time.sleep(.25)
                io.publish(motionfeed, 0)
            #if motion started
            if motion.rose:
                print('motion detected')
                #reset start times
                start1 = time.monotonic()
                start2 = time.monotonic()
            #if continued motion
            elif motion.value:
                print('still motion')
                io.publish(motionfeed, 1)
                time.sleep(5)
            #if continued no motion
            else:
                print('no motion')

        print("\n")

        # Explicitly pump the message loop.
        io.loop()

        #check difference between time now and start times if more than N seconds start beeping
        if (((time.monotonic() - start1) >= 300) or ((time.monotonic() - start2) >= 300)):
            prealarm = True
            #beeping
            buzzer1.value = True
            time.sleep(.5)
            buzzer1.value = False

        #check if difference between time now and start1 if more than X seconds turn on buzzer2
        if (alarm1 is False and ((time.monotonic() - start1) >= 600)):
            alarm1 = True
            buzzer2.value = True
            #publish 1 to alarm feed
            io.publish(alarmfeed, 1)

        #check if difference between time now and start2 if more than X seconds turn on buzzer2
        if (alarm2 is False and ((time.monotonic() - start2) >= 600)):
            alarm2 = True
            buzzer2.value = True
            #publish 1 to alarm feed
            io.publish(alarmfeed, 1)

        print(str(time.time()))
        print(str(int(time.time()/300)))
        #check if 300 seconds have passed compared to start time, if so publish values
        if int(time.time()/300) > start:
            print("PUBLISH EVERY FIVE MINUTES")
            start = int(time.time()/300)
            io.publish(door1feed, int(leftswitch.value))
            io.publish(door2feed, int(rightswitch.value))
            io.publish(motionfeed, int(motion.value))

    # Adafruit IO fails with internal error types and WiFi fails with specific messages.
    # This except is broad to handle any possible failure.
    except Exception as e:  # pylint: disable=broad-except
        print("Failed to get or send data, or connect. Error:", e,
              "\nBoard will restart in 20 seconds.")
        time.sleep(20)
        microcontroller.reset()
