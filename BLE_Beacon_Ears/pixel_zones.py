# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT
'''Pixel zone abstraction for the BLE Beacon Ears project.

A "zone" represents one ear. In prototype mode (ONBOARD) both zones composite
into the single onboard NeoPixel, with the left zone painting first and the
right zone painting second so the right side "wins" - still useful for a
quick visual of current state. In production mode (STEREO_JEWELS) each zone
drives its own 7-pixel Jewel on an independent data pin.

The API is intentionally minimal:
    zone.fill(rgb)              - solid color across all pixels
    zone.set_led(idx, rgb)      - write a specific pixel
    zone.count                  - number of pixels in the zone
    zone.show()                 - flush to hardware (no-op if auto_write)

The renderer writes to both zones each frame and calls show() once at frame
end. Double-buffering is not needed at 15fps - a torn frame would be
invisible to the eye.
'''
# Target: Adafruit QT Py ESP32-S3 - the BLE Beacon Ears
import board
import digitalio
import neopixel


class OnboardSingle:
    '''Prototype mode: both zones share the single onboard NeoPixel.

    The left zone paints first; the right zone overwrites. This gives a
    "right-biased" preview of stereo effects. Pair with the serial
    stereo_log helper in the renderer to see what the other side is doing.
    '''

    def __init__(self, brightness=0.15):
        self._power = None
        try:
            self._power = digitalio.DigitalInOut(board.NEOPIXEL_POWER)
            self._power.switch_to_output(value=True)
        except (AttributeError, ValueError):
            pass
        self._pixel = neopixel.NeoPixel(
            board.NEOPIXEL, 1, brightness=brightness, auto_write=False)
        self._pixel.fill((0, 0, 0))
        self._pixel.show()

    def make_zones(self):
        '''Return (left_zone, right_zone) both pointing at the same pixel.'''
        # Both zones share the underlying neopixel object. The renderer
        # writes left first, then right. A single show() call at frame end
        # flushes the right zone's final state to hardware.
        return _SingleZone(self._pixel), _SingleZone(self._pixel)

    def show(self):
        '''Flush the onboard pixel state to hardware.'''
        self._pixel.show()

    def set_brightness(self, brightness):
        '''Change pixel brightness at runtime.'''
        self._pixel.brightness = brightness


class StereoJewels:
    '''Production mode: two 7-pixel Jewels on independent data pins.

    Supports an idle-skip optimization: once both jewels have been shown
    as all-black, subsequent show() calls are no-ops until pixel data
    actually changes. This avoids unnecessary data-stream activity and
    lets the WS2812 chips stay in their lowest-current latched state.
    '''

    def __init__(self, left_pin, right_pin, brightness=0.1):
        self._left = neopixel.NeoPixel(
            left_pin, 7, brightness=brightness, auto_write=False)
        self._right = neopixel.NeoPixel(
            right_pin, 7, brightness=brightness, auto_write=False)
        self._left.fill((0, 0, 0))
        self._right.fill((0, 0, 0))
        self._left.show()
        self._right.show()
        self._last_shown_black = True

    def make_zones(self):
        '''Return (left_zone, right_zone) wrapping each Jewel separately.'''
        return _JewelZone(self._left), _JewelZone(self._right)

    def set_brightness(self, brightness):
        '''Change the brightness of both jewels at runtime.'''
        self._left.brightness = brightness
        self._right.brightness = brightness
        self._last_shown_black = False  # force next show() to push new values

    def _all_black(self):
        '''Return True if every pixel on both jewels is currently (0,0,0).'''
        for i in range(7):
            if self._left[i] != (0, 0, 0):
                return False
            if self._right[i] != (0, 0, 0):
                return False
        return True

    def show(self):
        '''Flush both Jewel buffers to hardware, with idle-skip optimization.

        If we've already shown all-black once and nothing has changed to
        non-black since, skip the data stream to save power. The WS2812
        chips latch their last color state and stay in quiescent mode
        until new data arrives.
        '''
        if self._all_black():
            if self._last_shown_black:
                return
            self._left.show()
            self._right.show()
            self._last_shown_black = True
        else:
            self._left.show()
            self._right.show()
            self._last_shown_black = False


class _SingleZone:
    '''Zone backed by a shared 1-pixel NeoPixel (OnboardSingle mode).'''

    count = 1

    def __init__(self, pixel):
        self._pixel = pixel

    def fill(self, rgb):
        '''Set the shared onboard pixel to the given color.'''
        self._pixel[0] = rgb

    def set_led(self, idx, rgb):
        '''Write a specific pixel index. Only idx 0 has effect here.

        All LED writes collapse to the single onboard pixel. The last
        write of the frame wins, which matches the "right overwrites
        left" compositing intent.
        '''
        if idx == 0:
            self._pixel[0] = rgb


class _JewelZone:
    '''Zone backed by a dedicated 7-pixel Jewel (StereoJewels mode).'''

    count = 7

    def __init__(self, pixel_obj):
        self._pixel = pixel_obj

    def fill(self, rgb):
        '''Set every pixel on this Jewel to the given color.'''
        self._pixel.fill(rgb)

    def set_led(self, idx, rgb):
        '''Write a specific pixel index (0-6) on this Jewel.'''
        if 0 <= idx < 7:
            self._pixel[idx] = rgb
