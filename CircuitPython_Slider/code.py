import time
import displayio
import terminalio
import adafruit_imageload
from adafruit_display_text.label import Label
from adafruit_featherwing import minitft_featherwing
from adafruit_motorkit import MotorKit
from adafruit_motor import stepper

# setup stepper motor
kit = MotorKit()

# setup minitft featherwing
minitft = minitft_featherwing.MiniTFTFeatherWing()

# setup bitmap file locations
five_minBMP = "/5min_bmp.bmp"
ten_minBMP = "/10min_bmp.bmp"
twenty_minBMP = "/20min_bmp.bmp"
hourBMP = "/60min_bmp.bmp"
runningBMP = "/camSlide_bmp.bmp"
reverseqBMP = "/reverseQ_bmp.bmp"
backingUpBMP = "/backingup_bmp.bmp"
stopBMP = "/stopping_bmp.bmp"

# variables for state machines in loop
mode = 0
onOff = 0
pause = 0
stop = 0
z = 0

# image groups
five_minGroup = displayio.Group()
ten_minGroup = displayio.Group()
twenty_minGroup = displayio.Group()
hourGroup = displayio.Group()
reverseqGroup = displayio.Group()
backingUpGroup = displayio.Group()
stopGroup = displayio.Group()
progBarGroup = displayio.Group()

# bitmap setup for all of the menu screens
five_minBG, five_minPal = adafruit_imageload.load(
    five_minBMP, bitmap=displayio.Bitmap, palette=displayio.Palette
)
five_minDis = displayio.TileGrid(five_minBG, pixel_shader=five_minPal)
ten_minBG, ten_minPal = adafruit_imageload.load(
    ten_minBMP, bitmap=displayio.Bitmap, palette=displayio.Palette
)
ten_minDis = displayio.TileGrid(ten_minBG, pixel_shader=ten_minPal)
twenty_minBG, twenty_minPal = adafruit_imageload.load(
    twenty_minBMP, bitmap=displayio.Bitmap, palette=displayio.Palette
)
twenty_minDis = displayio.TileGrid(twenty_minBG, pixel_shader=twenty_minPal)
hourBG, hourPal = adafruit_imageload.load(
    hourBMP, bitmap=displayio.Bitmap, palette=displayio.Palette
)
hourDis = displayio.TileGrid(hourBG, pixel_shader=hourPal)
runningBG, runningPal = adafruit_imageload.load(
    runningBMP, bitmap=displayio.Bitmap, palette=displayio.Palette
)
runningDis = displayio.TileGrid(runningBG, pixel_shader=runningPal)
reverseqBG, reverseqPal = adafruit_imageload.load(
    reverseqBMP, bitmap=displayio.Bitmap, palette=displayio.Palette
)
reverseqDis = displayio.TileGrid(reverseqBG, pixel_shader=reverseqPal)
backingUpBG, backingUpPal = adafruit_imageload.load(
    backingUpBMP, bitmap=displayio.Bitmap, palette=displayio.Palette
)
backingUpDis = displayio.TileGrid(backingUpBG, pixel_shader=backingUpPal)
stopBG, stopPal = adafruit_imageload.load(
    stopBMP, bitmap=displayio.Bitmap, palette=displayio.Palette
)
stopDis = displayio.TileGrid(stopBG, pixel_shader=stopPal)

# setup for timer display when camera is sliding
text_area = Label(terminalio.FONT, text="      ")
text_area.x = 55
text_area.y = 65

# adding the bitmaps to the image groups so they can be displayed
five_minGroup.append(five_minDis)
ten_minGroup.append(ten_minDis)
twenty_minGroup.append(twenty_minDis)
hourGroup.append(hourDis)
progBarGroup.append(runningDis)
progBarGroup.append(text_area)
reverseqGroup.append(reverseqDis)
backingUpGroup.append(backingUpDis)
stopGroup.append(stopDis)

# setting button states on minitft featherwing to None
down_state = None
up_state = None
a_state = None
b_state = None
select_state = None

# arrays to match up with the different slide speeds
# graphics menu array
graphics = [five_minGroup, ten_minGroup, twenty_minGroup, hourGroup]
# delay for the stepper motor
speed = [0.0154, 0.034, 0.0688, 0.2062]
# time duration for the camera slide
slide_duration = [300, 600, 1200, 3600]
# beginning timer display
slide_begin = ["5:00", "10:00", "20:00", "60:00"]
# stepper motor steps that corresponds with the timer display
# fmt: off
slide_checkin = [  860,  1720,  2580,  3440,  4300,  5160,
                  6020,  6880,  7740,  8600,  9460, 10320,
                 11180, 12040, 12900, 13760, 14620, 15480,
                 16340, 17195]
# fmt: on
# variable that counts up through the slide_checkin array
check = 0

# start time
begin = time.monotonic()
print(begin)
# when feather is powered up it shows the initial graphic splash
minitft.display.show(graphics[mode])

while True:
    # setup minitft featherwing buttons
    buttons = minitft.buttons
    # define the buttons' state changes
    if not buttons.down and down_state is None:
        down_state = "pressed"
    if not buttons.up and up_state is None:
        up_state = "pressed"
    if not buttons.select and select_state is None:
        select_state = "pressed"
    if not buttons.a and a_state is None:
        a_state = "pressed"
    if not buttons.b and b_state is None:
        b_state = "pressed"
    # scroll down to change slide duration and graphic
    if buttons.down and down_state == "pressed":
        # blocks the button if the slider is sliding or
        # in an in-between state
        if pause == 1 or onOff == 1:
            mode = mode
            down_state = None
        else:
            mode += 1
            down_state = None
            if mode > 3:
                mode = 0
            print("Mode:,", mode)
            minitft.display.show(graphics[mode])
    # scroll up to change slide duration and graphic
    if buttons.up and up_state == "pressed":
        # blocks the button if the slider is sliding or
        # in an in-between state
        if pause == 1 or onOff == 1:
            mode = mode
            up_state = None
        else:
            mode -= 1
            up_state = None
            if mode < 0:
                mode = 3
            print("Mode: ", mode)
            minitft.display.show(graphics[mode])
    # workaround so that the menu graphics show after a slide is finished
    if mode == mode and pause == 0 and onOff == 0:
        minitft.display.show(graphics[mode])
    # starts slide
    if buttons.select and select_state == "pressed" or z == 2:
        # blocks the button if the slider is sliding or
        # in an in-between state
        if pause == 1 or onOff == 1:
            # print("null")
            select_state = None
        else:
            # shows the slider is sliding graphic
            minitft.display.show(progBarGroup)
            # gets time of button press
            press = time.monotonic()
            print(press)
            # displays initial timer
            text_area.text = slide_begin[mode]
            # resets button
            select_state = None
            # changes onOff state
            onOff += 1
            # changes z state
            z = 0
            if onOff > 1:
                onOff = 0
            # number of steps for the length of the aluminum extrusions
            for i in range(17200):
                # for loop start time
                start = time.monotonic()
                # gets actual duration time
                real_time = start - press
                # creates a countdown from the slide's length
                end = slide_duration[mode] - real_time
                # /60 since time is in seconds
                mins_remaining = end / 60
                if mins_remaining < 0:
                    mins_remaining += 60
                # gets second(s) count
                total_sec_remaining = mins_remaining * 60
                # formats to clock time
                mins_remaining, total_sec_remaining = divmod(end, 60)
                # microstep for the stepper
                kit.stepper1.onestep(style=stepper.MICROSTEP)
                # delay determines speed of the slide
                time.sleep(speed[mode])
                if i == slide_checkin[check]:
                    # check-in for time remaining based on motor steps
                    print("0%d:%d" % (mins_remaining, total_sec_remaining))
                    print(check)
                    if total_sec_remaining < 10:
                        text_area.text = "%d:0%d" % (
                            mins_remaining,
                            total_sec_remaining,
                        )
                    else:
                        text_area.text = "%d:%d" % (mins_remaining, total_sec_remaining)
                    check = check + 1
                if check > 19:
                    check = 0
                if end < 10:
                    # displays the stopping graphic for the last 10 secs.
                    minitft.display.show(stopGroup)
            # changes states after slide has completed
            kit.stepper1.release()
            pause = 1
            onOff = 0
            stop = 1
            check = 0
            # delay for safety
            time.sleep(2)
            # shows choice menu
            minitft.display.show(reverseqGroup)
    # b is defined to stop the slider
    # only active if the slider is in the 'stopped' state
    if buttons.b and b_state == "pressed" and stop == 1:
        # z defines location of the camera on the slider
        # 0 means that it is opposite the motor
        if z == 0:
            b_state = None
            time.sleep(1)
            minitft.display.show(backingUpGroup)
            # delay for safety
            time.sleep(2)
            # brings camera back to 'home' at double speed
            for i in range(1145):
                kit.stepper1.onestep(direction=stepper.BACKWARD, style=stepper.DOUBLE)
            time.sleep(1)
            kit.stepper1.release()
            # changes states
            pause = 0
            stop = 0
        # 1 means that the camera is next to the motor
        if z == 1:
            b_state = None
            time.sleep(2)
            # changes states
            pause = 0
            stop = 0
            z = 0
    # a is defined to slide in reverse of the prev. slide
    # only active if the slider is in the 'stopped' state
    if buttons.a and a_state == "pressed" and stop == 1:
        # z defines location of the camera on the slider
        # 1 means that the camera is next to the motor
        if z == 1:
            a_state = None
            time.sleep(2)
            stop = 0
            pause = 0
            # 2 allows the 'regular' slide loop to run
            # as if the 'select' button has been pressed
            z = 2
        # 0 means that the camera is opposite the motor
        if z == 0:
            a_state = None
            # same script as the 'regular' slide loop
            time.sleep(2)
            minitft.display.show(progBarGroup)
            press = time.monotonic()
            print(press)
            text_area.text = slide_begin[mode]
            onOff += 1
            pause = 0
            stop = 0
            if onOff > 1:
                onOff = 0
            for i in range(17200):
                start = time.monotonic()
                real_time = start - press
                end = slide_duration[mode] - real_time
                mins_remaining = end / 60
                if mins_remaining < 0:
                    mins_remaining += 60
                total_sec_remaining = mins_remaining * 60
                mins_remaining, total_sec_remaining = divmod(end, 60)
                # only difference is that the motor is stepping backwards
                kit.stepper1.onestep(
                    direction=stepper.BACKWARD, style=stepper.MICROSTEP
                )
                time.sleep(speed[mode])
                if i == slide_checkin[check]:
                    print("0%d:%d" % (mins_remaining, total_sec_remaining))
                    if total_sec_remaining < 10:
                        text_area.text = "%d:0%d" % (
                            mins_remaining,
                            total_sec_remaining,
                        )
                    else:
                        text_area.text = "%d:%d" % (mins_remaining, total_sec_remaining)
                    check = check + 1
                if check > 19:
                    check = 0
                if end < 10:
                    minitft.display.show(stopGroup)
            # state changes
            kit.stepper1.release()
            pause = 1
            onOff = 0
            stop = 1
            z = 1
            check = 0
            time.sleep(2)
            minitft.display.show(reverseqGroup)
