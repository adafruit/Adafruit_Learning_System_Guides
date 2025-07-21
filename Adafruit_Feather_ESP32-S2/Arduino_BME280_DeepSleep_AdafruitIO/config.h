// SPDX-FileCopyrightText: 2025 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT
#define IO_USERNAME "your-aio-username"
#define IO_KEY "your-aio-token"
#define WIFI_SSID "your-wifi-ssid"
#define WIFI_PASS "your-wifi-pass"

#include "AdafruitIO_WiFi.h"
AdafruitIO_WiFi io(IO_USERNAME, IO_KEY, WIFI_SSID, WIFI_PASS);