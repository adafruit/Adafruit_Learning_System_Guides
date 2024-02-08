import usb_cdc
import board
import digitalio
import storage

usb_cdc.enable(console=True, data=True)    # Enable console and data

write_mode_btn = digitalio.DigitalInOut(board.D9)
write_mode_btn.direction = digitalio.Direction.INPUT
write_mode_btn.pull = digitalio.Pull.UP

storage.remount("/", readonly=write_mode_btn.value)
