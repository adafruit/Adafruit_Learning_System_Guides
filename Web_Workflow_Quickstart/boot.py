import storage
import microcontroller

if microcontroller.nvm[0] != 1:
    storage.disable_usb_drive()
