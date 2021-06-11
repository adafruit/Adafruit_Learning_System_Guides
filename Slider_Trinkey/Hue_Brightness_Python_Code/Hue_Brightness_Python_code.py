"""
Slider Trinkey Hue Dimmer Python Example
(Requires Hue Dimmer CircuitPython example to be running on the Slider Trinkey)
"""
from phue import Bridge
import serial
from serial.tools import list_ports

# Update this to the room, zone or individual lamp you want to control.
LAMP_OR_GROUP_NAME = "Office Desk Stand Lamp"

# Update this to the IP address of your Hue Bridge.
b = Bridge("10.19.69.50")

slider_trinkey_port = None
ports = list_ports.comports(include_links=False)
for p in ports:
    if p.pid is not None:
        print("Port:", p.device, "-", hex(p.pid), end="\t")
        if p.pid == 0x8102:
            slider_trinkey_port = p
            print("Found Slider Trinkey!")
            break
        else:
            print()
else:
    print("Did not find Slider Trinkey port :(")
    exit(-1)

trinkey = serial.Serial(p.device)

# If the app is not registered and the button on the Hue Bridge is not pressed, press the button
# and call connect() (this only needs to be run a single time)
b.connect()
b.get_api()

is_group = False
light = None

# First, check if it's a group name.
for group_data in b.get_group().values():
    if group_data["name"] == LAMP_OR_GROUP_NAME:
        print("Found group with name", LAMP_OR_GROUP_NAME)
        is_group = True

# If it's not a group, find the lamp by name.
if not is_group:
    light_names = b.get_light_objects("name")
    light = light_names[LAMP_OR_GROUP_NAME]
    print("Found light with name", LAMP_OR_GROUP_NAME)

current_brightness = None
while True:
    x = trinkey.readline().decode("utf-8")
    if not x.startswith("Slider: "):
        continue

    # Convert the Slider Trinkey output value of 0-100 to 0-254.
    brightness_value = int((float(x.split(": ")[1]) / 100) * 254)

    if current_brightness is None or brightness_value != current_brightness:
        print("Setting brightness to:", brightness_value)
        if is_group:
            b.set_group(LAMP_OR_GROUP_NAME, {"bri": brightness_value})
        else:
            light.brightness = brightness_value
        current_brightness = brightness_value
