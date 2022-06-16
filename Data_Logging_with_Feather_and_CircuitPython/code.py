# SPDX-FileCopyrightText: 2018 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import analogio
import board
import storage
import adafruit_am2320

vbat_voltage = analogio.AnalogIn(board.D9)

i2c = board.I2C()  # uses board.SCL and board.SDA
am2320 = adafruit_am2320.AM2320(i2c)

SD_CS = board.D10
spi = board.SPI()

try:
    import sdcardio

    sdcard = sdcardio.SDCard(spi, SD_CS)
except ImportError:
    import adafruit_sdcard
    import digitalio

    cs = digitalio.DigitalInOut(SD_CS)
    sd_card = adafruit_sdcard.SDCard(spi, cs)

vfs = storage.VfsFat(sd_card)
storage.mount(vfs, "/sd_card")


def get_voltage(pin):
    return (pin.value * 3.3) / 65536 * 2


print("Logging temperature and humidity to log file")

initial_time = time.monotonic()

while True:
    try:
        with open("/sd_card/log.txt", "a") as sdc:
            temperature = am2320.temperature
            humidity = am2320.relative_humidity
            battery_voltage = get_voltage(vbat_voltage)
            current_time = time.monotonic()
            time_stamp = current_time - initial_time
            print("Seconds since current data log started:", int(time_stamp))
            print("Temperature:", temperature)
            print("Humidity:", humidity)
            print("VBat voltage: {:.2f}".format(battery_voltage))
            print()
            sdc.write(
                "{}, {}, {}, {:.2f}\n".format(
                    int(time_stamp), temperature, humidity, battery_voltage
                )
            )
        time.sleep(3)
    except OSError:
        pass
    except RuntimeError:
        pass
