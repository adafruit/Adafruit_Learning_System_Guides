"""
Read data from a BerryMed pulse oximeter, model BM1000C, BM1000E, etc.
Run this on Feather nRF52840
Log data to SD card on Autologger FeatherWing
"""

# Protocol defined here:
#     https://github.com/zh2x/BCI_Protocol
# Thanks as well to:
#     https://github.com/ehborisov/BerryMed-Pulse-Oximeter-tool
#     https://github.com/ScheindorfHyenetics/berrymedBluetoothOxymeter
#
# The sensor updates the readings at 100Hz.

import time
import adafruit_sdcard
import board
import busio
import digitalio
import storage
import adafruit_pcf8523
import _bleio
import adafruit_ble
from adafruit_ble.advertising.standard import Advertisement
from adafruit_ble.services.standard.device_info import DeviceInfoService
from adafruit_ble_berrymed_pulse_oximeter import BerryMedPulseOximeterService

# Logging setup
SD_CS = board.D10
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
cs = digitalio.DigitalInOut(SD_CS)
sd_card = adafruit_sdcard.SDCard(spi, cs)
vfs = storage.VfsFat(sd_card)
storage.mount(vfs, "/sd_card")

log_interval = 2  # you can adjust this to log at a different rate

# RTC setup
I2C = busio.I2C(board.SCL, board.SDA)
rtc = adafruit_pcf8523.PCF8523(I2C)

days = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")

set_time = False
if set_time:  # change to True if you want to write the time!
    #             year, mon, date, hour, min, sec, wday, yday, isdst
    t = time.struct_time((2020, 4, 21, 18, 13, 0, 2, -1, -1))
    # you must set year, mon, date, hour, min, sec and weekday
    # yearday  not supported, isdst can be set but we don't use it at this time
    print("Setting time to:", t)  # uncomment for debugging
    rtc.datetime = t
    print()

# PyLint can't find BLERadio for some reason so special case it here.
ble = adafruit_ble.BLERadio()  # pylint: disable=no-member

pulse_ox_connection = None

while True:
    t = rtc.datetime
    print("Scanning for Pulse Oximeter...")
    for adv in ble.start_scan(Advertisement, timeout=5):
        name = adv.complete_name
        if not name:
            continue
        # "BerryMed" devices may have trailing nulls on their name.
        if name.strip("\x00") == "BerryMed":
            pulse_ox_connection = ble.connect(adv)
            print("Connected")
            break

    # Stop scanning whether or not we are connected.
    ble.stop_scan()
    print("Stopped scan")

    try:
        if pulse_ox_connection and pulse_ox_connection.connected:
            print("Fetch connection")
            if DeviceInfoService in pulse_ox_connection:
                dis = pulse_ox_connection[DeviceInfoService]
                try:
                    manufacturer = dis.manufacturer
                except AttributeError:
                    manufacturer = "(Manufacturer Not specified)"
                try:
                    model_number = dis.model_number
                except AttributeError:
                    model_number = "(Model number not specified)"
                print("Device:", manufacturer, model_number)
            else:
                print("No device information")

            pulse_ox_service = pulse_ox_connection[BerryMedPulseOximeterService]

            while pulse_ox_connection.connected:
                values = pulse_ox_service.values
                if values is not None:
                    # unpack the message to 'values' list
                    valid, spo2, pulse_rate, pleth, finger = values
                    if not valid:
                        continue
                    if (
                            pulse_rate == 255
                    ):  # device sends 255 as pulse until it has a valid read
                        continue
                    print(
                        "SpO2: {}%  | ".format(spo2),
                        "Pulse Rate: {} BPM  | ".format(pulse_rate),
                        "Pleth: {}".format(pleth),
                    )
                    # print((pleth,))  # uncomment to see graph on Mu plotter

                    try:  # logging to SD card
                        with open("/sd_card/log.txt", "a") as sdc:
                            t = rtc.datetime
                            sdc.write(
                                "{} {}/{}/{} {}:{}:{}, ".format(
                                    days[t.tm_wday],
                                    t.tm_mday,
                                    t.tm_mon,
                                    t.tm_year,
                                    t.tm_hour,
                                    t.tm_min,
                                    t.tm_sec
                                )
                            )
                            sdc.write(
                                "{}, {}, {:.2f}\n".format(
                                    spo2, pulse_rate, pleth
                                )
                            )

                            time.sleep(log_interval)
                    except OSError:
                        pass
                    except RuntimeError:
                        pass
    except _bleio.ConnectionError:
        try:
            pulse_ox_connection.disconnect()
        except _bleio.ConnectionError:
            pass
        pulse_ox_connection = None
