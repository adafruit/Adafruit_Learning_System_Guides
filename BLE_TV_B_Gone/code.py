# SPDX-FileCopyrightText: 2018 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# Circuit Playground Bluefruit version 2022 John Park

import array
import time
import board
import pulseio
from digitalio import DigitalInOut, Direction, Pull
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService
from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.button_packet import ButtonPacket

# pylint: disable=eval-used
# Switch to select 'stealth-mode'
switch = DigitalInOut(board.SLIDE_SWITCH)
switch.direction = Direction.INPUT
switch.pull = Pull.UP
# Button to see output debug
led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT
# which pin for IR LED/blaster
ir_pin = board.A2  # JST IR Blaster board
# Speaker as haptic feedback
spkr_en = DigitalInOut(board.SPEAKER_ENABLE)
spkr_en.direction = Direction.OUTPUT
spkr_en.value = True
spkr = DigitalInOut(board.SPEAKER)
spkr.direction = Direction.OUTPUT

# Allow any button to trigger activity!
button_a = DigitalInOut(board.BUTTON_A)
button_a.direction = Direction.INPUT
button_a.pull = Pull.DOWN
button_b = DigitalInOut(board.BUTTON_B)
button_b.direction = Direction.INPUT
button_b.pull = Pull.DOWN

# BLE setup
ble = BLERadio()
uart_service = UARTService()
advertisement = ProvideServicesAdvertisement(uart_service)

def ir_code_send(code):
    f = open(code, "r")
    for line in f:
        code = eval(line)
        print(code)
        if switch.value:
            led.value = True
        else:
            spkr.value = True
        # If this is a repeating code, extract details
        try:
            repeat = code["repeat"]
            delay = code["repeat_delay"]
        except KeyError:  # by default, repeat once only!
            repeat = 1
            delay = 0
        # The table holds the on/off pairs
        table = code["table"]
        pulses = []  # store the pulses here
        # Read through each indexed element
        for i in code["index"]:
            pulses += table[i]  # and add to the list of pulses
        pulses.pop()  # remove one final 'low' pulse

        with pulseio.PulseOut(
            ir_pin, frequency=code["freq"], duty_cycle=2**15
        ) as pulse:
            for i in range(repeat):
                pulse.send(array.array("H", pulses))
                time.sleep(delay)

        led.value = False
        spkr.value = False
        time.sleep(code["delay"])

    f.close()


while True:
    ble.name = 'TVRemote'
    ble.start_advertising(advertisement)

    while not ble.connected:
        # Wait for a connection.
        if button_a.value or button_b.value:
            print("All codes")
            time.sleep(0.1)  # wait a moment
            ir_code_send("/full_codes.txt")

    while ble.connected:
        if button_a.value or button_b.value:
            print("all")
            time.sleep(0.1)  # wait a moment
            ir_code_send("/full_codes.txt")
        if uart_service.in_waiting:
            # Packet is arriving.
            packet = Packet.from_stream(uart_service)
            if isinstance(packet, ButtonPacket) and packet.pressed:
                if packet.button == ButtonPacket.UP:
                    print("Select codes")
                    time.sleep(0.1)  # wait a moment
                    ir_code_send("/codes.txt")

                if packet.button == ButtonPacket.DOWN:
                    print("All codes")
                    time.sleep(0.1)  # wait a moment
                    ir_code_send("/full_codes.txt")

                elif packet.button == ButtonPacket.BUTTON_1:
                    print("Sony power")
                    time.sleep(0.1)  # wait a moment
                    ir_code_send("/sony_pwr.txt")

                elif packet.button == ButtonPacket.BUTTON_2:
                    print("Toshiba power")
                    time.sleep(0.1)  # wait a moment
                    ir_code_send("/toshiba_pwr.txt")
