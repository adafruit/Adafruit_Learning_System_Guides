import time
import board
import pulseio
from adafruit_motor import servo
from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.button_packet import ButtonPacket
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

ble = BLERadio()
uart = UARTService()
advertisement = ProvideServicesAdvertisement(uart)

pwm = pulseio.PWMOut(board.A3, duty_cycle=2 ** 15, frequency=50)

my_servo = servo.Servo(pwm)

while True:
    print("WAITING...")
    # Advertise when not connected.
    ble.start_advertising(advertisement)
    while not ble.connected:
        pass

    # Connected
    ble.stop_advertising()
    print("CONNECTED")

    # Loop and read packets
    while ble.connected:
        if uart.in_waiting:
            packet = Packet.from_stream(uart)
            if isinstance(packet, ButtonPacket):
                #  if buttons in the app are pressed
                if packet.pressed:
                    if packet.button == ButtonPacket.DOWN:
                        print("pressed down")
                        for angle in range(90, 170, 90):  # 90 - 170 degrees, 90 degrees at a time.
                            my_servo.angle = angle
                            time.sleep(0.05)
                    if packet.button == ButtonPacket.UP:
                        print("pressed up")
                        for angle in range(170, 90, -90): # 170 - 90 degrees, 9 degrees at a time.
                            my_servo.angle = angle
                            time.sleep(0.05)
    # Disconnected
    print("DISCONNECTED")
