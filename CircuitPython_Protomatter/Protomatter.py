import framebufferio
import _protomatter

def protomatter_display(*, width, bit_depth, rgb_pins, addr_pins, clock_pin,
                        latch_pin, output_enable_pin, doublebuffer=True,
                        framebuffer=None, rotation=0, auto_refresh=True,
                        native_frames_per_second=60):
    height = len(rgb_pins) // 3 * 2 ** len(addr_pins)
    pm = _protomatter.Protomatter(
        width=width, height=height, bit_depth=bit_depth,
        rgb_pins=rgb_pins, addr_pins=addr_pins, clock_pin=clock_pin,
        latch_pin=latch_pin, output_enable_pin=output_enable_pin,
        doublebuffer=doublebuffer, framebuffer=framebuffer,
    )
    return framebufferio.FramebufferDisplay(
        pm, width=width, height=height,
        rotation=rotation, auto_refresh=auto_refresh,
        native_frames_per_second=native_frames_per_second,
    )
