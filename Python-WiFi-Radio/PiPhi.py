#! /usr/bin/python

# UI wrapper for 'pianobar' client for Pandora, using Adafruit 16x2 LCD
# Pi Plate for Raspberry Pi.
# Written by Adafruit Industries.  MIT license.
#
# Required hardware includes any internet-connected Raspberry Pi
# system, any of the Adafruit 16x2 LCD w/Keypad Pi Plate varieties
# and either headphones or amplified speakers.
# Required software includes the Adafruit Raspberry Pi Python Code
# repository, pexpect library and pianobar.  A Pandora account is
# also necessary.
#
# Resources:
# http://www.adafruit.com/products/1109 RGB Positive 16x2 LCD + Keypad
# http://www.adafruit.com/products/1110 RGB Negative 16x2 LCD + Keypad
# http://www.adafruit.com/products/1115 Blue & White 16x2 LCD + Keypad

import atexit, pexpect, pickle, socket, time, subprocess
from Adafruit_I2C import Adafruit_I2C
from Adafruit_MCP230xx import Adafruit_MCP230XX
from Adafruit_CharLCDPlate import Adafruit_CharLCDPlate


# Constants:
RGB_LCD      = False # Set to 'True' if using color backlit LCD
HALT_ON_EXIT = False # Set to 'True' to shut down system when exiting
MAX_FPS      = 6 if RGB_LCD else 4 # Limit screen refresh rate for legibility
VOL_MIN      = -20
VOL_MAX      =  15
VOL_DEFAULT  =   0
HOLD_TIME    = 3.0 # Time (seconds) to hold select button for shut down
PICKLEFILE   = '/home/pi/.config/pianobar/state.p'

# Global state:
volCur       = VOL_MIN     # Current volume
volNew       = VOL_DEFAULT # 'Next' volume after interactions
volSpeed     = 1.0         # Speed of volume change (accelerates w/hold)
volSet       = False       # True if currently setting volume
paused       = False       # True if music is paused
staSel       = False       # True if selecting station
volTime      = 0           # Time of last volume button interaction
playMsgTime  = 0           # Time of last 'Playing' message display
staBtnTime   = 0           # Time of last button press on station menu
xTitle       = 16          # X position of song title (scrolling)
xInfo        = 16          # X position of artist/album (scrolling)
xStation     = 0           # X position of station (scrolling)
xTitleWrap   = 0
xInfoWrap    = 0
xStationWrap = 0
songTitle   = ''
songInfo    = ''
stationNum  = 0            # Station currently playing
stationNew  = 0            # Station currently highlighted in menu
stationList = ['']
stationIDs  = ['']

# Char 7 gets reloaded for different modes.  These are the bitmaps:
charSevenBitmaps = [
  [0b10000, # Play (also selected station)
   0b11000,
   0b11100,
   0b11110,
   0b11100,
   0b11000,
   0b10000,
   0b00000],
  [0b11011, # Pause
   0b11011,
   0b11011,
   0b11011,
   0b11011,
   0b11011,
   0b11011,
   0b00000],
  [0b00000, # Next Track
   0b10100,
   0b11010,
   0b11101,
   0b11010,
   0b10100,
   0b00000,
   0b00000]]


# --------------------------------------------------------------------------


# Exit handler tries to leave LCD in a nice state.
def cleanExit():
    if lcd is not None:
        time.sleep(0.5)
        lcd.backlight(lcd.OFF)
        lcd.clear()
        lcd.stop()
    if pianobar is not None:
        pianobar.kill(0)


def shutdown():
    lcd.clear()
    if HALT_ON_EXIT:
        if RGB_LCD: lcd.backlight(lcd.YELLOW)
        lcd.message('Wait 30 seconds\nto unplug...')
        # Ramp down volume over 5 seconds while 'wait' message shows
        steps = int((volCur - VOL_MIN) + 0.5) + 1
        pause = 5.0 / steps
        for i in range(steps):
            pianobar.send('(')
            time.sleep(pause)
        subprocess.call("sync")
        cleanExit()
        subprocess.call(["shutdown", "-h", "now"])
    else:
        exit(0)


# Draws song title or artist/album marquee at given position.
# Returns new position to avoid global uglies.
def marquee(s, x, y, xWrap):
    lcd.setCursor(0, y)
    if x > 0: # Initially scrolls in from right edge
        lcd.message(' ' * x + s[0:16-x])
    else:     # Then scrolls w/wrap indefinitely
        lcd.message(s[-x:16-x])
        if x < xWrap: return 0
    return x - 1


def drawPlaying():
    lcd.createChar(7, charSevenBitmaps[0])
    lcd.setCursor(0, 1)
    lcd.message('\x07 Playing       ')
    return time.time()


def drawPaused():
    lcd.createChar(7, charSevenBitmaps[1])
    lcd.setCursor(0, 1)
    lcd.message('\x07 Paused        ')


def drawNextTrack():
    lcd.createChar(7, charSevenBitmaps[2])
    lcd.setCursor(0, 1)
    lcd.message('\x07 Next track... ')


# Draw station menu (overwrites fulls screen to facilitate scrolling)
def drawStations(stationNew, listTop, xStation, staBtnTime):
    last = len(stationList)
    if last > 2: last = 2  # Limit stations displayed
    ret  = 0  # Default return value (for station scrolling)
    line = 0  # Line counter
    msg  = '' # Clear output string to start
    for s in stationList[listTop:listTop+2]: # For each station...
        sLen = len(s) # Length of station name
        if (listTop + line) == stationNew: # Selected station?
            msg += chr(7) # Show selection cursor
            if sLen > 15: # Is station name longer than line?
                if (time.time() - staBtnTime) < 0.5:
                    # Just show start of line for half a sec
                    s2 = s[0:15]
                else:
                    # After that, scrollinate
                    s2 = s + '   ' + s[0:15]
                    xStationWrap = -(sLen + 2)
                    s2 = s2[-xStation:15-xStation]
                    if xStation > xStationWrap:
                        ret = xStation - 1
            else: # Short station name - pad w/spaces if needed
                s2 = s[0:15]
                if sLen < 15: s2 += ' ' * (15 - sLen)
        else: # Not currently-selected station
            msg += ' '   # No cursor
            s2 = s[0:15] # Clip or pad name to 15 chars
            if sLen < 15: s2 += ' ' * (15 - sLen)
        msg  += s2 # Add station name to output message
        line += 1
        if line == last: break
        msg  += '\n' # Not last line - add newline
    lcd.setCursor(0, 0)
    lcd.message(msg)
    return ret


def getStations():
    lcd.clear()
    lcd.message('Retrieving\nstation list...')
    pianobar.expect('Select station: ', timeout=20)
    # 'before' is now string of stations I believe
    # break up into separate lines
    a     = pianobar.before.splitlines()
    names = []
    ids   = []
    # Parse each line
    for b in a[:-1]: # Skip last line (station select prompt)
        # Occasionally a queued up 'TIME: -XX:XX/XX:XX' string or
        # 'new playlist...' appears in the output.  Station list
        # entries have a known format, so it's straightforward to
        # skip these bogus lines.
#        print '\"{}\"'.format(b)
        if (b.find('playlist...') >= 0) or (b.find('Autostart') >= 0):
            continue
#        if b[0:5].find(':') >= 0: continue
#        if (b.find(':') >= 0) or (len(b) < 13): continue
        # Alternate strategy: must contain either 'QuickMix' or 'Radio':
        # Somehow the 'playlist' case would get through this check.  Buh?
        if b.find('Radio') or b.find('QuickMix'):
            id   = b[5:7].strip()
            name = b[13:].strip()
            # If 'QuickMix' found, always put at head of list
            if name == 'QuickMix':
                ids.insert(0, id)
                names.insert(0, name)
            else:
                ids.append(id)
                names.append(name)
    return names, ids


# --------------------------------------------------------------------------
# Initialization

atexit.register(cleanExit)

lcd = Adafruit_CharLCDPlate()
lcd.begin(16, 2)
lcd.clear()

# Create volume bargraph custom characters (chars 0-5):
for i in range(6):
    bitmap = []
    bits   = (255 << (5 - i)) & 0x1f
    for j in range(8): bitmap.append(bits)
    lcd.createChar(i, bitmap)

# Create up/down icon (char 6)
lcd.createChar(6,
  [0b00100,
   0b01110,
   0b11111,
   0b00000,
   0b00000,
   0b11111,
   0b01110,
   0b00100])

# By default, char 7 is loaded in 'pause' state
lcd.createChar(7, charSevenBitmaps[1])

# Get last-used volume and station name from pickle file
try:
    f = open(PICKLEFILE, 'rb')
    v = pickle.load(f)
    f.close()
    volNew         = v[0]
    defaultStation = v[1]
except:
    defaultStation = None

# Show IP address (if network is available).  System might be freshly
# booted and not have an address yet, so keep trying for a couple minutes
# before reporting failure.
t = time.time()
while True:
    if (time.time() - t) > 120:
        # No connection reached after 2 minutes
        if RGB_LCD: lcd.backlight(lcd.RED)
        lcd.message('Network is\nunreachable')
        time.sleep(30)
        exit(0)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 0))
        if RGB_LCD: lcd.backlight(lcd.GREEN)
        else:       lcd.backlight(lcd.ON)
        lcd.message('My IP address is\n' + s.getsockname()[0])
        time.sleep(5)
        break         # Success -- let's hear some music!
    except:
        time.sleep(1) # Pause a moment, keep trying

# Launch pianobar as pi user (to use same config data, etc.) in background:
print('Spawning pianobar...')
pianobar = pexpect.spawn('sudo -u pi pianobar')
print('Receiving station list...')
pianobar.expect('Get stations... Ok.\r\n', timeout=60)
stationList, stationIDs = getStations()
try:    # Use station name from last session
    stationNum = stationList.index(defaultStation)
except: # Use first station in list
    stationNum = 0
print 'Selecting station ' + stationIDs[stationNum]
pianobar.sendline(stationIDs[stationNum])


# --------------------------------------------------------------------------
# Main loop.  This is not quite a straight-up state machine; there's some
# persnickety 'nesting' and canceling among mode states, so instead a few
# global booleans take care of it rather than a mode variable.

if RGB_LCD: lcd.backlight(lcd.ON)
lastTime = 0

pattern_list = pianobar.compile_pattern_list(['SONG: ', 'STATION: ', 'TIME: '])

while pianobar.isalive():

    # Process all pending pianobar output
    while True:
        try:
            x = pianobar.expect(pattern_list, timeout=0)
            if x == 0:
                songTitle  = ''
                songInfo   = ''
		xTitle     = 16
		xInfo      = 16
		xTitleWrap = 0
		xInfoWrap  = 0
                x = pianobar.expect(' \| ')
                if x == 0: # Title | Artist | Album
                    print 'Song: "{}"'.format(pianobar.before)
                    s = pianobar.before + '    '
                    n = len(s)
                    xTitleWrap = -n + 2
                    # 1+ copies + up to 15 chars for repeating scroll
                    songTitle = s * (1 + (16 / n)) + s[0:16]
                    x = pianobar.expect(' \| ')
                    if x == 0:
                        print 'Artist: "{}"'.format(pianobar.before)
                        artist = pianobar.before
                        x = pianobar.expect('\r\n')
                        if x == 0:
                            print 'Album: "{}"'.format(pianobar.before)
                            s = artist + ' < ' + pianobar.before + ' > '
                            n = len(s)
                            xInfoWrap = -n + 2
                            # 1+ copies + up to 15 chars for repeating scroll
                            songInfo  = s * (2 + (16 / n)) + s[0:16]
            elif x == 1:
                x = pianobar.expect(' \| ')
                if x == 0:
                    print 'Station: "{}"'.format(pianobar.before)
            elif x == 2:
                # Time doesn't include newline - prints over itself.
                x = pianobar.expect('\r', timeout=1)
                if x == 0:
                    print 'Time: {}'.format(pianobar.before)
                # Periodically dump state (volume and station name)
                # to pickle file so it's remembered between each run.
                try:
                    f = open(PICKLEFILE, 'wb')
                    pickle.dump([volCur, stationList[stationNum]], f)
                    f.close()
                except:
                    pass
        except pexpect.EOF:
            break
        except pexpect.TIMEOUT:
            break


    # Poll all buttons once, avoids repeated I2C traffic for different cases
    b        = lcd.buttons()
    btnUp    = b & (1 << lcd.UP)
    btnDown  = b & (1 <<lcd.DOWN)
    btnLeft  = b & (1 <<lcd.LEFT)
    btnRight = b & (1 <<lcd.RIGHT)
    btnSel   = b & (1 <<lcd.SELECT)

    # Certain button actions occur regardless of current mode.
    # Holding the select button (for shutdown) is a big one.
    if btnSel:

        t = time.time()                        # Start time of button press
        while lcd.buttonPressed(lcd.SELECT):   # Wait for button release
            if (time.time() - t) >= HOLD_TIME: # Extended hold?
                shutdown()                     # We're outta here
        # If tapped, different things in different modes...
        if staSel:                  # In station select menu...
            pianobar.send('\n')     #  Cancel station select
            staSel = False          #  Cancel menu and return to
            if paused: drawPaused() #  play or paused state
        else:                       # In play/pause state...
            volSet = False          #  Exit volume-setting mode (if there)
            paused = not paused     #  Toggle play/pause
            pianobar.send('p')      #  Toggle pianobar play/pause
            if paused: drawPaused() #  Display play/pause change
            else:      playMsgTime = drawPlaying()

    # Right button advances to next track in all modes, even paused,
    # when setting volume, in station menu, etc.
    elif btnRight:

        drawNextTrack()
        if staSel:      # Cancel station select, if there
            pianobar.send('\n')
            staSel = False
        paused = False  # Un-pause, if there
        volSet = False
        pianobar.send('n')

    # Left button enters station menu (if currently in play/pause state),
    # or selects the new station and returns.
    elif btnLeft:

        staSel = not staSel # Toggle station menu state
        if staSel:
            # Entering station selection menu.  Don't return to volume
            # select, regardless of outcome, just return to normal play.
            pianobar.send('s')
            lcd.createChar(7, charSevenBitmaps[0])
            volSet     = False
            cursorY    = 0 # Cursor position on screen
            stationNew = 0 # Cursor position in list
            listTop    = 0 # Top of list on screen
            xStation   = 0 # X scrolling for long station names
# Just keep the list we made at start-up
#            stationList, stationIDs = getStations()
            staBtnTime = time.time()
            drawStations(stationNew, listTop, 0, staBtnTime)
        else:
            # Just exited station menu with selection - go play.
            stationNum = stationNew # Make menu selection permanent
            print 'Selecting station: "{}"'.format(stationIDs[stationNum])
            pianobar.sendline(stationIDs[stationNum])
            paused = False

    # Up/down buttons either set volume (in play/pause) or select station
    elif btnUp or btnDown:

        if staSel:
            # Move up or down station menu
            if btnDown:
                if stationNew < (len(stationList) - 1):
                    stationNew += 1              # Next station
                    if cursorY < 1: cursorY += 1 # Move cursor
                    else:           listTop += 1 # Y-scroll
                    xStation = 0                 # Reset X-scroll
            elif stationNew > 0:                 # btnUp implied
                    stationNew -= 1              # Prev station
                    if cursorY > 0: cursorY -= 1 # Move cursor
                    else:           listTop -= 1 # Y-scroll
                    xStation = 0                 # Reset X-scroll
            staBtnTime = time.time()             # Reset button time
            xStation = drawStations(stationNew, listTop, 0, staBtnTime)
        else:
            # Not in station menu
            if volSet is False:
                # Just entering volume-setting mode; init display
                lcd.setCursor(0, 1)
                volCurI = int((volCur - VOL_MIN) + 0.5)
                n = int(volCurI / 5)
                s = (chr(6) + ' Volume ' +
                     chr(5) * n +       # Solid brick(s)
                     chr(volCurI % 5) + # Fractional brick 
                     chr(0) * (6 - n))  # Spaces
                lcd.message(s)
                volSet   = True
                volSpeed = 1.0
            # Volume-setting mode now active (or was already there);
            # act on button press.
            if btnUp:
                volNew = volCur + volSpeed
                if volNew > VOL_MAX: volNew = VOL_MAX
            else:
                volNew = volCur - volSpeed
                if volNew < VOL_MIN: volNew = VOL_MIN
            volTime   = time.time() # Time of last volume button press
            volSpeed *= 1.15        # Accelerate volume change

    # Other logic specific to unpressed buttons:
    else:
        if staSel:
            # In station menu, X-scroll active station name if long
            if len(stationList[stationNew]) > 15:
                xStation = drawStations(stationNew, listTop, xStation,
                  staBtnTime)
        elif volSet:
            volSpeed = 1.0 # Buttons released = reset volume speed
            # If no interaction in 4 seconds, return to prior state.
            # Volume bar will be erased by subsequent operations.
            if (time.time() - volTime) >= 4:
                volSet = False
                if paused: drawPaused()

    # Various 'always on' logic independent of buttons
    if not staSel:
        # Play/pause/volume: draw upper line (song title)
        if songTitle is not None:
            xTitle = marquee(songTitle, xTitle, 0, xTitleWrap)

        # Integerize current and new volume values
        volCurI = int((volCur - VOL_MIN) + 0.5)
        volNewI = int((volNew - VOL_MIN) + 0.5)
        volCur  = volNew
        # Issue change to pianobar
        if volCurI != volNewI:
            d = volNewI - volCurI
            if d > 0: s = ')' *  d
            else:     s = '(' * -d
            pianobar.send(s)

        # Draw lower line (volume or artist/album info):
        if volSet:
            if volNewI != volCurI: # Draw only changes
                if(volNewI > volCurI):
                    x = int(volCurI / 5)
                    n = int(volNewI / 5) - x
                    s = chr(5) * n + chr(volNewI % 5)
                else:
                    x = int(volNewI / 5)
                    n = int(volCurI / 5) - x
                    s = chr(volNewI % 5) + chr(0) * n
                lcd.setCursor(x + 9, 1)
                lcd.message(s)
        elif paused == False:
            if (time.time() - playMsgTime) >= 3:
                # Display artist/album (rather than 'Playing')
                xInfo = marquee(songInfo, xInfo, 1, xInfoWrap)

    # Throttle frame rate, keeps screen legible
    while True:
        t = time.time()
        if (t - lastTime) > (1.0 / MAX_FPS): break
    lastTime = t
