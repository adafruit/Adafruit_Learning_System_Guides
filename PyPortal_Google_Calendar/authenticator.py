# CircuitPython Google OAuth
# for PyPortal
import board
import busio
from digitalio import DigitalInOut
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from adafruit_esp32spi import adafruit_esp32spi
import adafruit_requests as requests
import displayio
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font
import adafruit_miniqr
from adafruit_oauth2 import OAuth2


# Add a secrets.py to your filesystem that has a dictionary called secrets with "ssid" and
# "password" keys with your WiFi credentials. DO NOT share that file or commit it into Git or other
# source control.
# pylint: disable=no-name-in-module,wrong-import-order
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

print("Connecting to AP...")
while not esp.is_connected:
    try:
        esp.connect_AP(secrets["ssid"], secrets["password"])
    except RuntimeError as e:
        print("could not connect to AP, retrying: ", e)
        continue
print("Connected to", str(esp.ssid, "utf-8"), "\tRSSI:", esp.rssi)

# Initialize a requests object with a socket and esp32spi interface
socket.set_interface(esp)
requests.set_socket(socket, esp)

# DisplayIO Setup
# Set up fonts
font_small = bitmap_font.load_font("/fonts/Arial-12.pcf")
font_large = bitmap_font.load_font("/fonts/Arial-14.pcf")
# preload fonts
glyphs = b"0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,.: "
font_small.load_glyphs(glyphs)
font_large.load_glyphs(glyphs)

group_verification = displayio.Group(max_size=25)
label_overview_text = Label(
    font_large, x=0, y=45, text="To authorize this device with Google:"
)
group_verification.append(label_overview_text)

label_verification_url = Label(font_small, x=0, y=100, line_spacing=1, max_glyphs=90)
group_verification.append(label_verification_url)

label_user_code = Label(font_small, x=0, y=150, max_glyphs=50)
group_verification.append(label_user_code)

label_qr_code = Label(font_small, x=0, y=190, text="Or scan the QR code:")
group_verification.append(label_qr_code)


### helper methods ###
def bitmap_QR(matrix):
    # monochome (2 color) palette
    BORDER_PIXELS = 2

    # bitmap the size of the screen, monochrome (2 colors)
    bitmap = displayio.Bitmap(
        matrix.width + 2 * BORDER_PIXELS, matrix.height + 2 * BORDER_PIXELS, 2
    )
    # raster the QR code
    for y in range(matrix.height):  # each scanline in the height
        for x in range(matrix.width):
            if matrix[x, y]:
                bitmap[x + BORDER_PIXELS, y + BORDER_PIXELS] = 1
            else:
                bitmap[x + BORDER_PIXELS, y + BORDER_PIXELS] = 0
    return bitmap


# Set scope(s) of access required by the API you're using
scopes = ["https://www.googleapis.com/auth/calendar.readonly"]

# Initialize an oauth2 object
google_auth = OAuth2(
    requests, secrets["google_client_id"], secrets["google_client_secret"], scopes
)


# Request device and user codes
# https://developers.google.com/identity/protocols/oauth2/limited-input-device#step-1:-request-device-and-user-codes
google_auth.request_codes()

# Display user code and verification url
# NOTE: If you are displaying this on a screen, ensure the text label fields are
# long enough to handle the user_code and verification_url.
# Details in link below:
# https://developers.google.com/identity/protocols/oauth2/limited-input-device#displayingthecode
print(
    "1) Navigate to the following URL in a web browser:", google_auth.verification_url
)
print("2) Enter the following code:", google_auth.user_code)

# modify display labels to show verification URL and user code
label_verification_url.text = (
    "1. On your computer or mobile device,\n    go to: %s"
    % google_auth.verification_url
)
label_user_code.text = "2. Enter code: %s" % google_auth.user_code

# Create a QR code
qr = adafruit_miniqr.QRCode(qr_type=3, error_correct=adafruit_miniqr.L)
qr.add_data(google_auth.verification_url.encode())
qr.make()

# generate the 1-pixel-per-bit bitmap
qr_bitmap = bitmap_QR(qr.matrix)
# we'll draw with a classic black/white palette
palette = displayio.Palette(2)
palette[0] = 0xFFFFFF
palette[1] = 0x000000
# we'll scale the QR code as big as the display can handle
scale = 15
# then center it!
qr_img = displayio.TileGrid(qr_bitmap, pixel_shader=palette, x=170, y=165)
group_verification.append(qr_img)
# show the group
board.DISPLAY.show(group_verification)


# Poll Google's authorization server
print("Waiting for browser authorization...")
if not google_auth.wait_for_authorization():
    raise RuntimeError("Timed out waiting for browser response!")

print("Successfully Authenticated with Google!")

# print formatted keys for adding to secrets.py
print("Add the following lines to your secrets.py file:")
print("\t'google_access_token' " + ":" + " '%s'," % google_auth.access_token)
print("\t'google_refresh_token' " + ":" + " '%s'" % google_auth.refresh_token)
# Remove QR code and code/verification labels
group_verification.pop()
group_verification.pop()
group_verification.pop()

label_overview_text.text = "Successfully Authenticated!"
label_verification_url.text = (
    "Check the REPL for tokens to add\n\tto your secrets.py file"
)

# prevent exit
while True:
    pass
