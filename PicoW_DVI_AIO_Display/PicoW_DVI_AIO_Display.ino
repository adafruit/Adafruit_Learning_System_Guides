// SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/************************** Configuration ***********************************/

// edit the config.h tab and enter your Adafruit IO credentials
// and any additional configuration needed for WiFi, cellular,
// or ethernet clients.
#include "config.h"
#include "sprites.h"
#include <PicoDVI.h>                  // Core display & graphics library
#include <Fonts/FreeSansBold18pt7b.h> // A custom font
#include <Fonts/FreeSans9pt7b.h> // A custom font

// put your four feed names here!

AdafruitIO_Feed *temp = io.feed("temperature-feed");
AdafruitIO_Feed *humid = io.feed("humidity-feed");
AdafruitIO_Feed *bat = io.feed("battery-feed");
AdafruitIO_Feed *aqi = io.feed("aqi-feed");

#define IO_LOOP_DELAY 5000
unsigned long lastUpdate = 0;
float temp_data;
float humid_data;
int bat_data;
int aqi_data;

struct outline {
  int16_t x, y; // Top-left corner
};

outline greenOutline = {159, 35};
outline yellowOutline = {204, 35};
outline redOutline = {250, 35};

DVIGFX8 display(DVI_RES_320x240p60, false, adafruit_dvibell_cfg);

void setup() {

  // start the serial connection
  Serial.begin(115200);

  // wait for serial monitor to open
  //while ( !Serial ) delay(10);

  Serial.print("Connecting to Adafruit IO");

  // start connection to io.adafruit.com
  io.connect();

  // set up a message handler for the count feed.
  // the handleMessage function (defined below)
  // will be called whenever a message is
  // received from adafruit io.
  temp->onMessage(tempMessage);
  humid->onMessage(humidMessage);
  bat->onMessage(batMessage);
  aqi->onMessage(aqiMessage);

  // wait for a connection
  while(io.status() < AIO_CONNECTED) {
    Serial.print(".");
    delay(500);
  }
  // we are connected
  Serial.println();
  Serial.println(io.statusText());

  // Because Adafruit IO doesn't support the MQTT retain flag, we can use the
  // get() function to ask IO to resend the last value for this feed to just
  // this MQTT client after the io client is connected.
  temp->get();
  humid->get();
  bat->get();
  aqi->get();

  Serial.println("starting picodvi..");
  if (!display.begin()) { // Blink LED if insufficient RAM
    pinMode(LED_BUILTIN, OUTPUT);
    for (;;) digitalWrite(LED_BUILTIN, (millis() / 500) & 1);
  }
  Serial.println("picodvi good to go");

  // Set up color palette
  display.setColor(0, 0x0000); // black
  display.setColor(1, 0x057D); // blue
  display.setColor(2, 0xB77F); // light blue
  display.setColor(3, 0xE8E4); // red
  display.setColor(4, 0x3DA9); // green
  display.setColor(5, 0xFF80); // yellow
  display.setColor(6, 0xFFFF); // white
  
}

void loop() {
  // io.run(); is required for all sketches.
  // it should always be present at the top of your loop
  // function. it keeps the client connected to
  // io.adafruit.com, and processes any incoming data.
  io.run();
  
  if (millis() > (lastUpdate + IO_LOOP_DELAY)) {
    display.fillScreen(0);
    display.drawBitmap(38, 35, airBitmap, airWidth, airHeight, 2);
    display.drawBitmap(47, 132, tempBitmap, tempWidth, tempHeight, 3);
    display.drawBitmap(145, 132, waterBitmap, waterWidth, waterHeight, 1);
    display.drawBitmap(248, 132, batBitmap, batWidth, batHeight, 6);
    drawBatterySquare(bat_data);
    displayAQI(aqi_data);
    display.setFont(&FreeSansBold18pt7b);
    display.setTextColor(6);
    display.setCursor(38 + airWidth + 15, 38 + airHeight - 10);
    display.println(aqi_data);
    display.setFont(&FreeSans9pt7b);
    display.setCursor(47 - 9, 130 + tempHeight + 25);
    display.print(temp_data, 2);
    display.println(" F");
    display.setCursor(145 - 9, 130 + tempHeight + 25);
    display.print(humid_data, 2);
    display.println("%");
    display.setCursor(248 - 5, 130 + tempHeight + 25);
    display.print(bat_data);
    display.println("%");
    // store the current time
    lastUpdate = millis();
  }

}

void humidMessage(AdafruitIO_Data *data) {
  //Serial.print("received <- ");
  Serial.println(data->value());
  String h = data->value();
  humid_data = h.toFloat();
}

void tempMessage(AdafruitIO_Data *data) {
  //Serial.print("received <- ");
  Serial.println(data->value());
  String d = data->value();
  temp_data = d.toFloat();
}

void batMessage(AdafruitIO_Data *data) {
  //Serial.print("received <- ");
  Serial.println(data->value());
  String b = data->value();
  bat_data = b.toInt();
}

void aqiMessage(AdafruitIO_Data *data) {
  //Serial.print("received <- ");
  Serial.println(data->value());
  String a = data->value();
  aqi_data = a.toInt();
}

void displayAQI(int data) {
  display.fillRoundRect(164, 40, 30, 30, 4, 4);
  display.fillRoundRect(209, 40, 30, 30, 4, 5);
  display.fillRoundRect(255, 40, 30, 30, 4, 3);
  if (data <= 12) { // Good
    display.drawRoundRect(greenOutline.x, greenOutline.y, 40, 40, 4, 6);
  } else if (data <= 35) { // Bad
    display.drawRoundRect(yellowOutline.x, yellowOutline.y, 40, 40, 4, 6);
  } else { // Dangerous
    display.drawRoundRect(redOutline.x, redOutline.y, 40, 40, 4, 6);
  }
}

void drawBatterySquare(int data) {
  int BASE_SQUARE_X = 252;  // Base X position
  int BASE_SQUARE_Y = 140;   // Base Y position
  int SQUARE_WIDTH = 21;    // Width is constant
  int MAX_SQUARE_HEIGHT = 35; // Maximum height for 100% charge
  // Map battery percentage to square height
  int height = map(data, 0, 100, 0, MAX_SQUARE_HEIGHT);
  // Choose color based on battery percentage
  uint16_t color;
  if (data >= 70) {
    color = 4;
  } else if (data >= 40) {
    color = 5;
  } else {
    color = 3;
  }
  // Calculate Y position based on height to draw from bottom up
  int yPos = BASE_SQUARE_Y + (MAX_SQUARE_HEIGHT - height);
  // Draw the battery square
  display.fillRect(BASE_SQUARE_X, yPos, SQUARE_WIDTH, height, color);
}
