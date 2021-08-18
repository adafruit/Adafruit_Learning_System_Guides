import os
import time
import board
import busio
import adafruit_mcp9808

# This example shows how to get the temperature from a MCP9808 board
i2c_bus = busio.I2C(board.SCL, board.SDA)
mcp = adafruit_mcp9808.MCP9808(i2c_bus)

while True:
    # print precise temperature values to console
    tempC = mcp.temperature
    tempF = tempC * 9 / 5 + 32
    print('Temperature: {} C {} F '.format(tempC, tempF))

    # drop decimal points and convert to string for speech
    tempC = str(int(tempC))
    tempF = str(int(tempF))
    os.system("echo 'The temperature is " + tempF + " degrees' | festival --tts")

    time.sleep(60.0)
