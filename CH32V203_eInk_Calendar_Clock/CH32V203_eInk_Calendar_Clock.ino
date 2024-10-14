// SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Arduino.h>
#include <SPI.h>
#include "Adafruit_TinyUSB.h"
#include "Adafruit_ThinkInk.h"
#include "RTClib.h"
#include <Wire.h>
#include <Fonts/FreeSans24pt7b.h>
#include <Fonts/FreeSans18pt7b.h>
#include <Fonts/FreeSans12pt7b.h>

#define EPD_DC PA3
#define EPD_CS PA2
#define EPD_BUSY -1 // can set to -1 to not use a pin (will wait a fixed delay)
#define SRAM_CS PA1
#define EPD_RESET -1  // can set to -1 and share with microcontroller Reset!
#define EPD_SPI &SPI // primary SPI

// 1.54" Monochrome displays with 200x200 pixels and SSD1681 chipset
ThinkInk_154_Mono_D67 display(EPD_DC, EPD_RESET, EPD_CS, SRAM_CS, EPD_BUSY, EPD_SPI);

RTC_DS3231 rtc;

char daysOfTheWeek[7][4] = {"SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"};
char monthsOfYear[13][4] = {"NULL", "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"};

bool start = true;

String lastTimeStr = "00:00";

void setup() {
  Serial.begin(115200);

  /*while (!Serial) {
    delay(10);
  }*/
  Serial.println("eInk Calendar & Clock with CH32V203");
  SPI.begin();
  Serial.println("SPI started");
  pinMode(EPD_CS, OUTPUT);
  digitalWrite(EPD_CS, HIGH);

  Wire.begin();
  Serial.println("Wire started");
  Serial.println("starting display, might take a bit..");
  display.begin(THINKINK_MONO);
  Serial.println("display started");

  while (! rtc.begin()) {
    Serial.println("Couldn't find RTC");
    delay(10);
  }
}

void loop() {
    Serial.println("we did it!");
    DateTime now = rtc.now();
    Serial.println("read rtc");
    char timeChar[6];
    sprintf(timeChar, "%02d:%02d", now.hour(), now.minute());
    String timeStr = String(timeChar);
    String monthStr = monthsOfYear[now.month()];
    String dateStr = String(now.day());
    String yearStr = String(now.year());
    String dayOfWeekStr = daysOfTheWeek[now.dayOfTheWeek()];
    Serial.println(timeStr);
    int16_t x1, y1;
    uint16_t w, h;
    if (lastTimeStr != timeStr) {
      display.clearBuffer();
      display.fillRect(0, 0, 200, 60, EPD_BLACK);
      display.drawRect(0, 0, 200, 170, EPD_BLACK);
      display.setTextColor(EPD_WHITE);
      display.setFont(&FreeSans24pt7b);
      display.getTextBounds(dayOfWeekStr.c_str(), 0, 0, &x1, &y1, &w, &h);
      display.setCursor((200 - w) / 2, (60 - h) / 2 + h);
      display.println(dayOfWeekStr);
      display.setTextColor(EPD_BLACK);
      display.getTextBounds(dateStr.c_str(), 0, 0, &x1, &y1, &w, &h);
      display.setCursor((200 - w) / 2, (170 - h) / 2 + h + 28);
      display.println(dateStr);
      display.setFont(&FreeSans18pt7b);
      display.getTextBounds(monthStr.c_str(), 0, 0, &x1, &y1, &w, &h);
      display.setCursor((200 - w) / 2, (60 + h) + 3);
      display.println(monthStr);
      display.getTextBounds(yearStr.c_str(), 0, 0, &x1, &y1, &w, &h);
      display.setCursor((200 - w) / 2, (170 - h) - 5 + h);
      display.println(yearStr);
      display.setFont(&FreeSans12pt7b);
      display.getTextBounds(timeStr.c_str(), 0, 0, &x1, &y1, &w, &h);
      display.setCursor((200 - w) / 2, (200 - h) - 5 + h);
      display.println(timeStr);
      display.display();
      lastTimeStr = timeStr;
    }
    delay(30000);
}
