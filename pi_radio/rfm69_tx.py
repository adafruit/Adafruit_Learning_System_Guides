# Simple transmitter for RFM69
import time
import board
import busio
import digitalio
import adafruit_rfm69

# Define pins connected to the chip, use these if wiring up the breakout according to the guide:
CS = digitalio.DigitalInOut(board.D5)
RESET = digitalio.DigitalInOut(board.D6)

# Define the onboard LED
LED = digitalio.DigitalInOut(board.D13)
LED.direction = digitalio.Direction.OUTPUT

# Initialize SPI bus.
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

# Initialze RFM radio
rfm69 = adafruit_rfm69.RFM69(spi, CS, RESET, 915.0)

# Optionally set an encryption key (16 byte AES key). MUST match both
# on the transmitter and receiver (or be set to None to disable/the default).
rfm69.encryption_key = b'\x01\x02\x03\x04\x05\x06\x07\x08\x01\x02\x03\x04\x05\x06\x07\x08'

# Packet counter, incremented per tx
packetNum = 0

rfm69.send(bytes('Hello world!\r\n',"utf-8"))
print('Sent hello world message!')

# Wait to receive packets.  Note that this library can't receive data at a fast
# rate, in fact it can only receive and process one 60 byte packet at a time.
# This means you should only use this for low bandwidth scenarios, like sending
# and receiving a single message at a time.
print('Waiting for packets...')
while True:
    rfm69.send(bytes("Hello Pi #","utf-8"))
    packetNum+=1
    print(packetNum)
    rfm69.send(bytes(packetNum))

    # Listen for a new packet
    packet = rfm69.receive()
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
    # Wait one second between Tx/Rx
    time.sleep(1)
