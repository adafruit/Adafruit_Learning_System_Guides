# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import adafruit_connection_manager
import adafruit_requests
import board
import busio
import digitalio

from adafruit_wiznet5k.adafruit_wiznet5k import WIZNET5K

print("Wiz5100 Breakout WebClient Test")

TEXT_URL = "http://wifitest.adafruit.com/testwifi/index.html"

cs = digitalio.DigitalInOut(board.D10)
spi_bus = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

# Initialize ethernet interface with DHCP
eth = WIZNET5K(spi_bus, cs)

# Initialize a requests session
pool = adafruit_connection_manager.get_radio_socketpool(eth)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(eth)
requests = adafruit_requests.Session(pool, ssl_context)

print("Chip Version:", eth.chip)
print("MAC Address:", [hex(i) for i in eth.mac_address])
print("My IP address is:", eth.pretty_ip(eth.ip_address))
print("IP lookup adafruit.com: %s" % eth.pretty_ip(eth.get_host_by_name("adafruit.com")))


# eth._debug = True
print("Fetching text from", TEXT_URL)
r = requests.get(TEXT_URL)
print("-" * 40)
print(r.text)
print("-" * 40)
r.close()

print("Done!")
