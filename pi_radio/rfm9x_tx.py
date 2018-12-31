# Simple transmitter for RFM9x
import time
import board
import busio
import digitalio
import adafruit_rfm9x

# Define pins connected to the chip, use these if wiring up the breakout according to the guide:
CS = digitalio.DigitalInOut(board.D6)
RESET = digitalio.DigitalInOut(board.D5)

# Define the onboard LED
LED = digitalio.DigitalInOut(board.D13)
LED.direction = digitalio.Direction.OUTPUT

# Initialize SPI bus.
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

# Initialze RFM radio
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, 915.0)

# You can however adjust the transmit power (in dB).  The default is 13 dB but
# high power radios like the RFM95 can go up to 23 dB:
rfm9x.tx_power = 23

# Packet counter, incremented per tx
packetNum = 0
while True:
    
    rfm9x.send(bytes("Hello Pi #","utf-8"))
    packetNum+=1
    print(packetNum)
    rfm9x.send(bytes(packetNum))
    
    # Listen for a new packet
    packet = rfm9x.receive()
    if packet is None:
        print('No reply, is there a transmitter around?')
        LED.value = False
    else:
        # Received a packet!
        LED.value = True
        # Print out the raw bytes of the packet:
        print('Received (raw bytes): {0}'.format(packet))
        # And decode to ASCII text and print it too.  Note that you always
        # receive raw bytes and need to convert to a text format like ASCII
        # if you intend to do string processing on your data.  Make sure the
        # sending side is sending ASCII data before you try to decode!
        packet_text = str(packet, 'ascii')
        print('Received (ASCII): {0}'.format(packet_text))
        # Also read the RSSI (signal strength) of the last received message and
        # print it.
        rssi = rfm9x.rssi
        print('Received signal strength: {0} dB'.format(rssi))
    # Wait one second between Tx/Rx
    time.sleep(1)
    