import serial

# how many bytes to read?
TRNG_SIZE = 4

# open serial port
ss = serial.Serial("/dev/ttyACM0")

# read raw bytes
raw_bytes = ss.read(TRNG_SIZE)

# print them
print(raw_bytes)