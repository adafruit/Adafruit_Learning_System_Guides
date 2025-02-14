# SPDX-FileCopyrightText: 2024 Tyeth Gundry for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# pylint: disable=import-outside-toplevel, line-too-long
def setup_display():
    # Code taken from Adafruit Qualia ESP32-S3 for RGB-666 Displays Learn Guide - Rectangle Bar 3.2" display
    # https://learn.adafruit.com/adafruit-qualia-esp32-s3-for-rgb666-displays/qualia-rgb666-with-tl032fwv01-3-2-320x820-bar-display
    from displayio import release_displays
    release_displays()

    import busio
    import board
    import dotclockframebuffer
    from framebufferio import FramebufferDisplay

    init_sequence_tl032 = bytes((
        b'\x11\x80d'
        b'\xff\x05w\x01\x00\x00\x13'
        b'\xef\x01\x08'
        b'\xff\x05w\x01\x00\x00\x10'
        b'\xc0\x02\xe5\x02'
        b'\xc1\x02\x0c\n'
        b'\xc2\x02\x07\x0f'
        b'\xc3\x01\x02'
        b'\xcc\x01\x10'
        b'\xcd\x01\x08'
        b'\xb0\x10\x00\x08Q\r\xce\x06\x00\x08\x08\x1d\x02\xd0\x0fo6?'
        b'\xb1\x10\x00\x10O\x0c\x11\x05\x00\x07\x07\x1f\x05\xd3\x11n4?'
        b'\xff\x05w\x01\x00\x00\x11'
        b'\xb0\x01M'
        b'\xb1\x01\x1c'
        b'\xb2\x01\x87'
        b'\xb3\x01\x80'
        b'\xb5\x01G'
        b'\xb7\x01\x85'
        b'\xb8\x01!'
        b'\xb9\x01\x10'
        b'\xc1\x01x'
        b'\xc2\x01x'
        b'\xd0\x81\x88d'
        b'\xe0\x03\x80\x00\x02'
        b'\xe1\x0b\x04\xa0\x00\x00\x05\xa0\x00\x00\x00``'
        b'\xe2\r00``<\xa0\x00\x00=\xa0\x00\x00\x00'
        b'\xe3\x04\x00\x0033'
        b'\xe4\x02DD'
        b'\xe5\x10\x06>\xa0\xa0\x08@\xa0\xa0\nB\xa0\xa0\x0cD\xa0\xa0'
        b'\xe6\x04\x00\x0033'
        b'\xe7\x02DD'
        b'\xe8\x10\x07?\xa0\xa0\tA\xa0\xa0\x0bC\xa0\xa0\rE\xa0\xa0'
        b'\xeb\x07\x00\x01NN\xeeD\x00'
        b"\xed\x10\xff\xff\x04Vr\xff\xff\xff\xff\xff\xff'e@\xff\xff"
        b'\xef\x06\x10\r\x04\x08?\x1f'
        b'\xff\x05w\x01\x00\x00\x13'
        b'\xe8\x02\x00\x0e'
        b'\xff\x05w\x01\x00\x00\x00'
        b'\x11\x80x'
        b'\xff\x05w\x01\x00\x00\x13'
        b'\xe8\x82\x00\x0c\n'
        b'\xe8\x02\x00\x00'
        b'\xff\x05w\x01\x00\x00\x00'
        b'6\x01\x00'
        b':\x01f'
        b'\x11\x80x'
        b')\x80x'
    ))

    board.I2C().deinit()
    i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
    tft_io_expander = dict(board.TFT_IO_EXPANDER)
    #tft_io_expander['i2c_address'] = 0x38 # uncomment for rev B
    dotclockframebuffer.ioexpander_send_init_sequence(i2c, init_sequence_tl032, **tft_io_expander)
    i2c.deinit()

    tft_pins = dict(board.TFT_PINS)

    tft_timings = {
        "frequency": 16000000,
        "width": 320,
        "height": 820,

        "hsync_pulse_width": 3,
        "hsync_back_porch": 251,
        "hsync_front_porch": 150,
        "hsync_idle_low": False,

        "vsync_pulse_width": 6,
        "vsync_back_porch": 90,
        "vsync_front_porch": 100,
        "vsync_idle_low": False,

        "pclk_active_high": False,
        "pclk_idle_high": False,
        "de_idle_high": False,
    }

    #bitmap = displayio.OnDiskBitmap("/display-ruler-720p.bmp")

    fb = dotclockframebuffer.DotClockFramebuffer(**tft_pins, **tft_timings)
    display = FramebufferDisplay(fb, auto_refresh=False)
    return display
