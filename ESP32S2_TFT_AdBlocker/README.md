# ESP32_AdBlocker

ESP32_AdBlocker acts as a DNS Sinkhole (like [Pi-Hole](https://pi-hole.net/)) by returning 0.0.0.0 for any domain names in its blocklist, else forwards to an external DNS server to resolve IP addresses. This prevents content being retrieved from or sent to blocked domains. Domain searches generally take <200 micro seconds. A web server is provided to control the service and monitor its operation. 

## Requirements

ESP32_AdBlocker is an Arduino sketch. The ESP32 module needs 4MB PSRAM in order to be host a reasonably sized blocklist of up to 64K domains. The blocklist can be persisted on either flash (SPIFFS) or an SD card. ESP-Cam modules are available at low cost and include both PSRAM and SD card reader. Without PSRAM only a very small blocklist can be used for testing purposes. 

## Operation

On first use, the ESP32_AdBlocker web page is used to enter the URL (must be `https`) of the blocklist to be downloaded: 
![image1](extras/webpage.png)
Press __Update__ to load the file. It will take a couple of minutes and restarts for ESP32_AdBlocker to be ready. Progress can be monitored on the Arduino Serial Monitor.
As only one file can be downloaded, a consolidated blocklist should be used. Select a file with less than 64K entries or it will be truncated. The file format should be in either HOSTS format or Adblock format (only domain name entries processed). The following site for example provides a list of suitable files: https://github.com/StevenBlack/hosts.

ESP32_AdBlocker will subsequently download the selected file daily at a given time to keep the blocklist updated.

To use a different blocklist, first press the web page __Reset__ button, then enter the new URL as before.

To make ESP32_AdBlocker your preferred DNS server, enter its IPv4 address in place of the current DNS server IPs in your router / devices. Currently ESP32_AdBlocker does not have an IPv6 address but some devices use IPv6 by default, so disable IPv6 DNS on your device / router to force it to use IPv4 DNS.

## Installation & Configuration

Download files into the Arduino IDE sketch location, removing `-master` from the folder name. Set the following constants (documented in the code) to suitable values:
* `USESPIFFS`
* `WIFISSID`
* `WIFIPASS`
* `TIMEZONE`
* `ADBLOCKER`
* `RESOLVER`
* `GATEWAY`

Compile with partition scheme: ___No OTA (2M APP/2M SPIFFS)___

