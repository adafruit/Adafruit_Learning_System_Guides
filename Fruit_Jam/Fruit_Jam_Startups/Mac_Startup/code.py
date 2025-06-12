import time
from audiocore import WaveFile
import audiobusio
import board
import supervisor
from displayio import Group, TileGrid, OnDiskBitmap
import adafruit_tlv320
from adafruit_fruitjam.peripherals import request_display_config
from adafruit_progressbar.horizontalprogressbar import (
    HorizontalFillDirection,
    HorizontalProgressBar,
)

# DAC setup
i2c = board.I2C()
dac = adafruit_tlv320.TLV320DAC3100(i2c)
dac.configure_clocks(sample_rate=44100, bit_depth=16)

# for headphone jack ouput
dac.headphone_output = True
dac.headphone_volume = -15  # dB
# for speaker JST output
# dac.speaker_output = True
# dac.speaker_volume = -15  # dB

# Chime audio setup
wave_file = open(  # pylint: disable=consider-using-with
    "mac_startup/mac_chime.wav", "rb"
)
wave = WaveFile(wave_file)
audio = audiobusio.I2SOut(board.I2S_BCLK, board.I2S_WS, board.I2S_DIN)

# Display setup
request_display_config(640, 480)
display = supervisor.runtime.display
display.auto_refresh = False

# group to hold visual all elements
main_group = Group()
display.root_group = main_group
display.refresh()

# background image
bg_bmp = OnDiskBitmap("mac_startup/mac_startup_bg.bmp")
bg_tg = TileGrid(bg_bmp, pixel_shader=bg_bmp.pixel_shader)
main_group.append(bg_tg)

# Icons for bottom left
icons = []
for i in range(6):
    odb = OnDiskBitmap("mac_startup/mac_startup_icon{0}.bmp".format(i))
    tg = TileGrid(odb, pixel_shader=odb.pixel_shader)
    icons.append(
        {
            "bmp": odb,
            "tg": tg,
        }
    )
    tg.x = 10 + ((33 + 8) * i)
    tg.y = display.height - tg.tile_height - 10
    tg.hidden = True
    if i < 5:
        odb.pixel_shader.make_transparent(0)
    main_group.append(tg)

# progress bar in the welcome box
progress_bar = HorizontalProgressBar(
    (147, 138),
    (346, 7),
    direction=HorizontalFillDirection.LEFT_TO_RIGHT,
    min_value=0,
    max_value=800,
    fill_color=0xC7BEFD,
    outline_color=0x000000,
    bar_color=0x3F3F3F,
    margin_size=0,
)
main_group.append(progress_bar)

# play the chime sound
audio.play(wave)
while audio.playing:
    pass

# start drawing the visual elements
display.auto_refresh = True
time.sleep(1)
start_time = time.monotonic()

while True:
    elapsed = time.monotonic() - start_time

    # if we haven't reached the end yet
    if elapsed * 100 <= 800:
        # update the progress bar
        progress_bar.value = elapsed * 100

    else:  # reached the end animation
        # set progress bar to max value
        progress_bar.value = 800

    # loop over all icons
    for index, icon in enumerate(icons):
        # if it's time for the current icon to show, and it's still hidden
        if (elapsed - 1) > index and icon["tg"].hidden:
            # make the current icon visible
            icon["tg"].hidden = False
