# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Init sequences and timings for the Qualia bar displays."""

PANELS = {
    "bar320x820": {
        "i2c_frequency": 400_000,
        "init_sequence": (
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
        ),
        "timings": {
            "frequency": 16000000,
            "width": 320,
            "height": 820,
            "hsync_pulse_width": 2,
            "hsync_back_porch": 44,
            "hsync_front_porch": 50,
            "hsync_idle_low": False,
            "vsync_pulse_width": 2,
            "vsync_back_porch": 18,
            "vsync_front_porch": 16,
            "vsync_idle_low": False,
            "pclk_active_high": False,
            "pclk_idle_high": False,
            "de_idle_high": False,
        },
    },
    "bar240x960": {
        "i2c_frequency": 100_000,
        "init_sequence": (
            b'\xff\x05w\x01\x00\x00\x13'
            b'\xef\x01\x08'
            b'\xff\x05w\x01\x00\x00\x10'
            b'\xc0\x02w\x00'
            b'\xc1\x02\x11\x0c'
            b'\xc2\x02\x07\x02'
            b'\xcc\x010'
            b'\xb0\x10\x06\xcf\x14\x0c\x0f\x03\x00\n\x07\x1b\x03\x12\x10%6\x1e'
            b'\xb1\x10\x0c\xd4\x18\x0c\x0e\x06\x03\x06\x08#\x06\x12\x100/\x1f'
            b'\xff\x05w\x01\x00\x00\x11'
            b'\xb0\x01s'
            b'\xb1\x01|'
            b'\xb2\x01\x83'
            b'\xb3\x01\x80'
            b'\xb5\x01I'
            b'\xb7\x01\x87'
            b'\xb8\x013'
            b'\xb9\x02\x10\x1f'
            b'\xbb\x01\x03'
            b'\xc1\x01\x08'
            b'\xc2\x01\x08'
            b'\xd0\x01\x88'
            b'\xe0\x06\x00\x00\x02\x00\x00\x0c'
            b'\xe1\x0b\x05\x96\x07\x96\x06\x96\x08\x96\x00DD'
            b'\xe2\x0c\x00\x00\x03\x03\x00\x00\x02\x00\x00\x00\x02\x00'
            b'\xe3\x04\x00\x0033'
            b'\xe4\x02DD'
            b'\xe5\x10\r\xd4(\x8c\x0f\xd6(\x8c\t\xd0(\x8c\x0b\xd2(\x8c'
            b'\xe6\x04\x00\x0033'
            b'\xe7\x02DD'
            b'\xe8\x10\x0e\xd5(\x8c\x10\xd7(\x8c\n\xd1(\x8c\x0c\xd3(\x8c'
            b'\xeb\x06\x00\x01\xe4\xe4D\x00'
            b'\xed\x10\xf3\xc1\xba\x0ffwDUUDwf\xf0\xab\x1c?'
            b'\xef\x06\x10\r\x04\x08?\x1f'
            b'\xff\x05w\x01\x00\x00\x13'
            b'\xe8\x02\x00\x0e'
            b'\x11\x80x'
            b'\xe8\x82\x00\x0c\n'
            b'\xe8\x02@\x00'
            b'\xff\x05w\x01\x00\x00\x00'
            b'6\x01\x00'
            b':\x01f'
            b')\x80\x14'
            b'\xff\x05w\x01\x00\x00\x10'
            b'\xe5\x02\x00\x00'
        ),
        "timings": {
            "frequency": 16000000,
            "width": 240,
            "height": 960,
            "overscan_left": 120,
            "hsync_pulse_width": 8,
            "hsync_back_porch": 20,
            "hsync_front_porch": 20,
            "hsync_idle_low": False,
            "vsync_pulse_width": 8,
            "vsync_back_porch": 20,
            "vsync_front_porch": 20,
            "vsync_idle_low": False,
            "pclk_active_high": True,
            "pclk_idle_high": False,
            "de_idle_high": False,
        },
    },
}
