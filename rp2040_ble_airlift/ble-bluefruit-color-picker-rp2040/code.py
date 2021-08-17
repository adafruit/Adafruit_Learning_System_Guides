import board
import neopixel

from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.color_packet import ColorPacket


from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

from adafruit_airlift.esp32 import ESP32


# If you are using an AirLift FeatherWing or AirLift Bitsy Add-On,
# use the pin settings below.
# If you are using an AirLift Breakout, check that these
# choices match the wiring to your microcontroller board,
# or change them as appropriate.
esp32 = ESP32(
    reset=board.D12,
    gpio0=board.D10,
    busy=board.D11,
    chip_select=board.D13,
    tx=board.TX,
    rx=board.RX,
)

adapter = esp32.start_bluetooth()

ble = BLERadio(adapter)
uart_service = UARTService()
advertisement = ProvideServicesAdvertisement(uart_service)

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=0.1)

while True:
    # Advertise when not connected.
    ble.start_advertising(advertisement)
    while not ble.connected:
        pass

    while ble.connected:
        if uart_service.in_waiting:
            packet = Packet.from_stream(uart_service)
            if isinstance(packet, ColorPacket):
                print(packet.color)
                pixels.fill(packet.color)
