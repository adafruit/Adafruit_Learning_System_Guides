import time
import board
import busio
from adafruit_circuitplayground.express import cpx

uart = busio.UART(board.TX, board.RX, baudrate=115200)

while True:

    data = uart.read(1)  # read a byte

    if data is not None:  # Data was received

        output = "%0.1f\t%d\t%0.1f\r\n" % (time.monotonic(),
                                           cpx.light, cpx.temperature)
        uart.write(output)         # Print to serial

        time.sleep(1.0)
