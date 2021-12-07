import json
import serial

# open serial port
ss = serial.Serial("/dev/ttyACM0")

# read string
_ = ss.readline() # first read may be incomplete, just toss it
raw_string = ss.readline().strip().decode()

# load JSON
json_data = json.loads(raw_string)

# print data
print(json_data['trng'])
