# Inspired by https://pimylifeup.com/raspberry-pi-kiosk/
# Start with a raspberry pi "full" installation that boots to desktop and
# can run chromium browser.
#
# Follow braincraft setup instructions sections:
#  - raspberry pi setup
#  - blinka setup
#  - audio setup
#  - fan service setup (optional)
#
# Now run this script, restart, and satisfy yourself that the player works
# properly using a HDMI monitor.  Troubleshooting is easier at this point!
#
# Now run the braincraft setup setps:
#  - display module install
#  - enable "overlay mode" in raspi-config so that it's safe to just power off
#    the pi anytime
#
# Before working with the system, remember to
#  - disable "overlay mode"
#  - optionally disable the display module to get a regular desktop back

cd $HOME

sudo apt-get install -y xdotool unclutter sed
cat > kiosk.sh <<EOF
#!/bin/bash
set -x
DISPLAY=:0; export DISPLAY
xset s noblank
xset s off
xset -dpms
unclutter -idle 0.5 -root &
sudo python3 /home/pi/braincraftKeys.py &
while true; do
    # Set speaker volume down -7dB (~40% volume)
    amixer -c 2 -- sset Speaker -7dB
    amixer -c 2 -- sset Headphone -7dB

    # Wait for network to come up
    while ! ping -c 1 youtube.com; do sleep 1; done

    sed -i 's/"exited_cleanly":false/"exited_cleanly":true/' /home/pi/.config/chromium/Default/Preferences
    sed -i 's/"exit_type":"Crashed"/"exit_type":"Normal"/' /home/pi/.config/chromium/Default/Preferences

    /usr/bin/chromium-browser --autoplay-policy=no-user-gesture-required --noerrdialogs --disable-infobars --kiosk --remote-debugging-port=9992 file:///home/pi/kioskvideo.html &
    sleep 15
    xdotool keydown f; xdotool keyup f
    wait %%
done
EOF
chmod +x kiosk.sh

cat > braincraftKeys.py <<"EOF"
#!/usr/bin/env python3
# Credit to Pimoroni for Picade HAT scripts as starting point.

import time
import signal
import os
import sys
from datetime import datetime

try:
    from evdev import uinput, UInput, ecodes as e
except ImportError:
    exit("This library requires the evdev module\nInstall with: sudo pip install evdev")

import digitalio
import board

DEBUG = False
BOUNCE_TIME = 0.01 # Debounce time in seconds
POWEROFF_TIMEOUT = 5

KEYS= [ # EDIT KEYCODES IN THIS TABLE TO YOUR PREFERENCES:
	# See /usr/include/linux/input.h for keycode names
	# Keyboard  Action (tuple = press together, no repeat)
        (board.D17, (e.KEY_K,)), # button - play/pause
        (board.D16, (e.KEY_LEFTCTRL, e.KEY_R)), # push stick - reload
	(board.D22, (e.KEY_LEFTSHIFT, e.KEY_P)), # left - previous in playlist
	(board.D24, (e.KEY_LEFTSHIFT, e.KEY_N)),  # right - next in playlist
	(board.D23, e.KEY_EQUAL),        # up - volume up
	(board.D27, e.KEY_MINUS),        # down - volume down
]

key_values = set()
for pin, action in KEYS:
    if isinstance(action, int):
        key_values.add(action)
    else:
        key_values.update(action)

class KeyManager:
    def __init__(self, pin, action):
        self.pin = digitalio.DigitalInOut(pin)
        self.pin.switch_to_output(digitalio.Pull.UP)
        self.action = action
        self.old_value = False

    @property
    def value(self):
        return not self.pin.value  # buttons are active-low

    def tick(self):
        value = self.value
        if value != self.old_value:
            if isinstance(self.action, int):
                ui.write(e.EV_KEY, self.action, value)
                ui.syn()
            elif value:
                for key in self.action:
                    ui.write(e.EV_KEY, key, 1)
                    ui.syn()
                for key in self.action[::-1]:
                    ui.write(e.EV_KEY, key, 0)
                    ui.syn()
        self.old_value = value

class ShutdownManager:
    def __init__(self, manager):
        self.manager = manager
        self.old_value = False
        self.press_start = 0

    @property
    def value(self):
        return self.manager.value

    def tick(self):
        now = time.time()
        value = self.value
        if value:
            if self.old_value:
                if now > self.press_start + POWEROFF_TIMEOUT:
                    os.system("env DISPLAY=:0 XAUTHORITY=/home/pi/.Xauthority xset dpms force off")
                    os.system("sudo poweroff")
            else:
                self.press_start = now
        self.old_value = value

managers = [KeyManager(k, v) for k, v in KEYS]
managers.append(ShutdownManager(managers[0]))

os.system("sudo modprobe uinput")

try:
    ui = UInput({e.EV_KEY: key_values}, name="braincraft-hat", bustype=e.BUS_USB)
except uinput.UInputError as e:
    sys.stdout.write(repr(e))
    sys.stdout.write("Have you tried running as root? sudo {}".format(sys.argv[0]))
    sys.exit(0)

def log(msg):
    sys.stdout.write(str(datetime.now()))
    sys.stdout.write(": ")
    sys.stdout.write(msg)
    sys.stdout.write("\n")
    sys.stdout.flush()

while True:
    for manager in managers:
        manager.tick()
    time.sleep(BOUNCE_TIME)
EOF
chmod +x braincraftKeys.py

cat > kiosk.service <<EOF
[Unit]
Description=Chromium Kiosk
Wants=graphical.target
After=graphical.target

[Service]
Environment=DISPLAY=:0.0
Environment=XAUTHORITY=/home/pi/.Xauthority
Type=simple
ExecStart=/bin/bash /home/pi/kiosk.sh
Restart=on-abort
User=pi
Group=pi

[Install]
WantedBy=graphical.target
EOF

sudo mv kiosk.service /etc/systemd/system/
sudo systemctl enable kiosk.service
sudo systemctl start kiosk.service

cat > kioskvideo.html <<"EOF"
<html>
<head>
<title>Braincraft Hat - lofi hip hop radio - betas to relax/study to</title>
<!--
Embed the youtube video for best viewing on the square (virtual 480x480)
Adafruit Braincraft Hat and react to (virtual) keystrokes to control playback

https://developers.google.com/youtube/iframe_api_reference
-->
</head>
<body>
<div style="position:absolute; top:0px; left:0px; width:480px; height:480px; overflow:hidden">
<iframe id="player" type="text/html" width="854" height="480" style="margin-left: -68px" src="http://www.youtube.com/embed/5qap5aO4i9A?enablejsapi=1&autoplay=1" frameborder="0" allow="autoplay"></iframe></div>
<div style="height:480px"></div>
NOTE: Chromium must be launched with --autoplay-policy=no-user-gesture-required or the video will not autoplay and the play/pause keystrokes will not work properly.  Clicking in the video will also affect keystroke functionality!
<script type="text/javascript">
  // playlist[0] needs to match the initial iframe src to work right
  var playlist = [
    '5qap5aO4i9A', // study
    'DWcJFNfaw9c', // sleep
    '5yx6BWlEVcY', // jazzy
  ]
  // in unboxed mode, pan to a different horizontal position depending on video
  var pan = [
    -68, -208, -187
  ]
  var playlist_idx = 0;
  var tag = document.createElement('script');
  tag.id = 'iframe-demo';
  tag.src = 'https://www.youtube.com/iframe_api';
  var firstScriptTag = document.getElementsByTagName('script')[0];
  firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

  var player;
  var unboxed=true;
  function onYouTubeIframeAPIReady() {
    player = new YT.Player('player', {
        events: {
          'onReady': onPlayerReady,
        }
    });
  }
  function onPlayerReady(event) {
    event.target.setVolume(40);
  }

  function fixPan() {
    if(unboxed) {
        document.getElementById('player').width=854
        document.getElementById('player').style="margin-left:"+pan[playlist_idx]+"px"
    } else {
        document.getElementById('player').width=480
        document.getElementById('player').style=""
    }
  }
  document.addEventListener('keydown', (event) => {
    if (event.ctrlKey || event.metaKey || event.altKey) {
        return
    }

    switch(event.key) {
    case 'k': // toggle play-pause
        if(player.getPlayerState() == 1) {
            console.log("pause")
            player.pauseVideo()
        } else {
            player.playVideo()
            console.log("play")
        }
        break;

    case 'p': // unconditional pause
        player.pauseVideo()
        break;

    case '[': // previous video in playlist
    case 'P': // previous video in playlist
        playlist_idx = (playlist_idx + playlist.length - 1) % playlist.length
        player.loadVideoById({'videoId' : playlist[playlist_idx]});
        fixPan()
        break;

    case ']': // previous video in playlist
    case 'N': // next video in playlist
        playlist_idx = (playlist_idx + 1) % playlist.length
        player.loadVideoById({'videoId' : playlist[playlist_idx]});
        fixPan()
        break;

    case '+': // volume up
    case '=': // volume up
        player.setVolume(Math.min(100, player.getVolume() + 10));
        break;

    case '-': // volume down
        player.setVolume(Math.max(0, player.getVolume() - 10));
        break;

    case 'm': // toggle mute
        if(player.isMuted()) {
            player.unMute()
        } else {
            player.mute()
        }
        break;

    case 'l':
        unboxed = !unboxed;
        fixPan()
    }

    
  }, false)
</script>
</body>
EOF
