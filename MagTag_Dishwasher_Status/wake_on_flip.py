import time
import board
import alarm
import displayio
import adafruit_lis3dh

# get the display
epd = board.DISPLAY

# set up accelerometer
lis = adafruit_lis3dh.LIS3DH_I2C(board.I2C(), address=0x19)

# See: ST Design Tip DT0008 - Simple screen rotation using
#      the accelerometer built-in 4D detection interrupt
# pylint: disable=protected-access
lis._write_register_byte(0x20, 0x3F)  # low power mode with ODR = 25Hz
lis._write_register_byte(0x22, 0x40)  # AOI1 interrupt generation is routed to INT1 pin
lis._write_register_byte(0x23, 0x80)  # FS = ±2g low power mode with BDU bit enabled
lis._write_register_byte(
    0x24, 0x0C
)  # Interrupt signal on INT1 pin is latched with D4D_INT1 bit enabled
lis._write_register_byte(
    0x32, 0x20
)  # Threshold = 32LSBs * 15.625mg/LSB = 500mg. (~30 deg of tilt)
lis._write_register_byte(0x33, 0x01)  # Duration = 1LSBs * (1/25Hz) = 0.04s

# read to clear
_ = lis._read_register_byte(0x31)

# get current accel values
_, y, _ = lis.acceleration

# update based on orientation
if y > 0:
    # upside up
    bmp_file = "clean.bmp"
    rotation = 270
    irq_config = 0b01000100
else:
    # upside down
    bmp_file = "dirty.bmp"
    rotation = 90
    irq_config = 0b01001000

# show bitmap
epd.rotation = rotation
with open(bmp_file, "rb") as fp:
    bitmap = displayio.OnDiskBitmap(fp)
    tile_grid = displayio.TileGrid(bitmap, pixel_shader=displayio.ColorConverter())
    group = displayio.Group(max_size=1)
    group.append(tile_grid)
    epd.show(group)
    time.sleep(epd.time_to_refresh + 0.01)
    epd.refresh()
    while epd.busy:
        pass

# config accelo irq
lis._write_register_byte(0x30, irq_config)

# go to sleep
pin_alarm = alarm.pin.PinAlarm(pin=board.ACCELEROMETER_INTERRUPT, value=True)
alarm.exit_and_deep_sleep_until_alarms(pin_alarm)
