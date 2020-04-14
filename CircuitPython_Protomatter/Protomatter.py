import framebufferio
import _protomatter

# //| .. class:: Display(framebuffer, *, width, height, colstart=0, rowstart=0, rotation=0, color_depth=16, grayscale=False, pixels_in_byte_share_row=True, bytes_per_cell=1, reverse_pixels_in_byte=False, backlight_pin=None, brightness=1.0, auto_brightness=False, auto_refresh=True, native_frames_per_second=60)


def protomatter_display(*,
    width,
    bit_depth,
    rgb_pins,
    addr_pins,
    clock_pin,
    latch_pin,
    output_enable_pin,
    doublebuffer=True,
    framebuffer=None,
    rotation=0,
    auto_refresh=True,
    native_frames_per_second=60
):
    height = len(rgb_pins) // 3 * 2 ** len(addr_pins)
    pm = _protomatter.Protomatter(
        width=width,
        height=height,
        bit_depth=bit_depth,
        rgb_pins=rgb_pins,
        addr_pins=addr_pins,
        clock_pin=clock_pin,
        latch_pin=latch_pin,
        output_enable_pin=output_enable_pin,
        doublebuffer=doublebuffer,
        framebuffer=framebuffer,
    )
    return framebufferio.FramebufferDisplay(
        pm,
        width=width,
        height=height,
        rotation=rotation,
        auto_refresh=auto_refresh,
        native_frames_per_second=native_frames_per_second,
    )

def default_display(release=True):
    if release:
        displayio.release_displays()
    import microcontroller.pin
    return protomatter_display(64, 4,
        [microcontroller.pin.PA18, microcontroller.pin.PA16, microcontroller.pin.PA19, microcontroller.pin.PA21, microcontroller.pin.PA20, microcontroller.pin.PA22],
        [microcontroller.pin.PA06, microcontroller.pin.PA04, microcontroller.pin.PB09, microcontroller.pin.PB08],
        microcontroller.pin.PA23, microcontroller.pin.PB17, microcontroller.pin.PB16, auto_refresh=True)

