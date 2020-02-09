# Display stuff
import displayio
import adafruit_imageload
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
from adafruit_gizmo import tft_gizmo
# BLE stuff
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService
from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.color_packet import ColorPacket

#---| User Config |--------------------------------------------------
BLE_NAME = "Candy Heart"
MESSAGE_DELIMITER = ","
MESSAGE_COLOR = 0xFF0000
#---| User Config |--------------------------------------------------

# Setup BLE radio and service
ble = BLERadio()
uart = UARTService()
advertisement = ProvideServicesAdvertisement(uart)
ble._adapter.name = BLE_NAME #pylint: disable=protected-access

# Create the TFT Gizmo display
display = tft_gizmo.TFT_Gizmo()

# Load the candy heart BMP
bitmap, palette = adafruit_imageload.load("/heart_bw.bmp",
                                          bitmap=displayio.Bitmap,
                                          palette=displayio.Palette)

heart = displayio.TileGrid(bitmap, pixel_shader=palette)

# Set up message text
LINE1_MAX = 9
LINE2_MAX = 5
font = bitmap_font.load_font("/Multicolore_36.bdf")
line1 = label.Label(font, text="?"*LINE1_MAX)
line2 = label.Label(font, text="?"*LINE2_MAX)
line1.anchor_point = (0.5, 0)    # middle top
line2.anchor_point = (0.5, 1.0)  # middle bottom
line1.anchored_position = (120, 85)
line2.anchored_position = (120, 175)
line1.color = line2.color = MESSAGE_COLOR

# Set up group and add to display
group = displayio.Group()
group.append(heart)
group.append(line1)
group.append(line2)
display.show(group)

def update_heart(message, heart_color):
    # turn off auto refresh while we change some things
    display.auto_refresh = False
    # set message text
    text1, _, text2 = message.partition(MESSAGE_DELIMITER)
    line1.text = text1[:LINE1_MAX] if len(text1) > LINE1_MAX else text1
    line2.text = text1[:LINE2_MAX] if len(text2) > LINE2_MAX else text2
    # update location for new text bounds
    line1.anchored_position = (120, 85)
    line2.anchored_position = (120, 175)
    # set heart color
    palette[1] = heart_color
    # OK, now turn auto refresh back on to display
    display.auto_refresh = True

# Initial update
text = "TEXT,ME"
color = 0x00FFFF
update_heart(text, color)

# Loop forever
while True:
    # advertise and wait for connection
    print("WAITING...")
    ble.start_advertising(advertisement)
    while not ble.connected:
        pass

    # connected
    print("CONNECTED")
    ble.stop_advertising()

    # receive and handle BLE traffic
    while ble.connected:
        if uart.in_waiting:
            raw_bytes = uart.read(uart.in_waiting)
            if raw_bytes[0] == ord('!'):
            # BLE Connect Control Packet
                packet = Packet.from_bytes(raw_bytes)
                if isinstance(packet, ColorPacket):
                    print("color = ", color)
                    color = packet.color
            else:
            # Just plain text
                text = raw_bytes.decode("utf-8").strip()
                print("text = ", text)
            update_heart(text, color)

    # disconnected
    print("DISCONNECTED")
