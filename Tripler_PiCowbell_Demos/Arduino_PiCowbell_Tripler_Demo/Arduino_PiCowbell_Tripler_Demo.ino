// SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_NeoPixel.h>
#include <Adafruit_GFX.h>    // Core graphics library
#include <Adafruit_ST7789.h> // Hardware-specific library for ST7789
#include <SPI.h>
#include <Fonts/FreeSansBold24pt7b.h>

#define LED    LED_BUILTIN
#define TFT_CS        21
#define TFT_RST       -1
#define TFT_DC        20
#define NEO_PIN       A2

uint32_t Wheel(byte WheelPos);

Adafruit_ST7789 tft = Adafruit_ST7789(TFT_CS, TFT_DC, TFT_RST);

Adafruit_NeoPixel pixel = Adafruit_NeoPixel(1, NEO_PIN, NEO_GRB + NEO_KHZ800);

unsigned long lastMillis = 0;
uint8_t j = 0;

void setup() {
  Serial.begin(115200);
  //while (!Serial)  delay(1);  // wait for serial port
  tft.init(240, 240);
  pinMode(LED, OUTPUT);
  delay (100);
  Serial.println("PiCowbell Tripler Demo");
  tft.setFont(&FreeSansBold24pt7b);
  pixel.begin();
  pixel.setBrightness(50);
  pixel.show(); // Initialize all pixels to 'off'
  lastMillis = millis();

}

void loop() {
  if (millis() > (lastMillis + 5000)) {
    digitalWrite(LED, HIGH);
    // get the on-board voltage
    float vsys = analogRead(A3) * 3 * 3.3 / 1023.0;
    Serial.printf("Vsys: %0.1f V", vsys);
    Serial.println();
    digitalWrite(LED, LOW);
    tft.fillScreen(ST77XX_BLACK);
    tft.setCursor(240 / 4, 240 / 2);
    tft.setTextColor(ST77XX_WHITE);
    tft.printf("%0.1f V", vsys);
    lastMillis = millis();
  }
  pixel.setPixelColor(0, Wheel(j++));
  pixel.show();
  delay(20);
}

uint32_t Wheel(byte WheelPos) {
  WheelPos = 255 - WheelPos;
  if(WheelPos < 85) {
    return pixel.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  }
  if(WheelPos < 170) {
    WheelPos -= 85;
    return pixel.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
  WheelPos -= 170;
  return pixel.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
}
