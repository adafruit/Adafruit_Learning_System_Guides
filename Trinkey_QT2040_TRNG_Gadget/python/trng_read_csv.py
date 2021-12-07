import serial

# open serial port
ss = serial.Serial("/dev/ttyACM0")

# read string
raw_string = ss.readline().strip().decode()

# read again if not complete
if '' in raw_string.split(','):
    raw_string = ss.readline().strip().decode()

# create list of integers
rnd_ints = [int(x) for x in raw_string.split(',')]

# print them
print(rnd_ints)
