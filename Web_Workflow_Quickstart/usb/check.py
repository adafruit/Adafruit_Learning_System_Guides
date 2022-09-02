import microcontroller
print(f"USB Mass Storage is {'enabled' if microcontroller.nvm[0] == 1 else 'disabled'} on this device")