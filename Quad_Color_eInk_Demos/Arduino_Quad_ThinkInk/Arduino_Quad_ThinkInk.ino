// SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/***************************************************
  Adafruit invests time and resources providing this open source code,
  please support Adafruit and open-source hardware by purchasing
  products from Adafruit!

  Written by Limor Fried/Ladyada for Adafruit Industries.
  MIT license, all text above must be included in any redistribution
 ****************************************************/

#include "Adafruit_ThinkInk.h"

#ifdef ARDUINO_ADAFRUIT_FEATHER_RP2040_THINKINK // detects if compiling for
                                                // Feather RP2040 ThinkInk
#define EPD_DC PIN_EPD_DC       // ThinkInk 24-pin connector DC
#define EPD_CS PIN_EPD_CS       // ThinkInk 24-pin connector CS
#define EPD_BUSY PIN_EPD_BUSY   // ThinkInk 24-pin connector Busy
#define SRAM_CS -1              // use onboard RAM
#define EPD_RESET PIN_EPD_RESET // ThinkInk 24-pin connector Reset
#define EPD_SPI &SPI1           // secondary SPI for ThinkInk
#else
#define EPD_DC 10
#define EPD_CS 9
#define EPD_BUSY 7 // can set to -1 to not use a pin (will wait a fixed delay)
#define SRAM_CS 6
#define EPD_RESET 8  // can set to -1 and share with microcontroller Reset!
#define EPD_SPI &SPI // primary SPI
#endif

// 2.13" Quadcolor EPD with JD79661 chipset
ThinkInk_213_Quadcolor_AJHE5 display(EPD_DC, EPD_RESET, EPD_CS, SRAM_CS, EPD_BUSY,
                                     EPD_SPI);

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }
  Serial.println("Adafruit EPD full update test in red/yellow/black/white");
  display.begin(THINKINK_QUADCOLOR);
}

void loop() {
  Serial.println("Banner demo");
  display.clearBuffer();
  display.setTextSize(3);
  display.setCursor((display.width() - 144) / 2, (display.height() - 24) / 2);
  String text = "QuadColor";
  uint16_t colors[] = {EPD_BLACK, EPD_RED, EPD_YELLOW};
  
  for (int i = 0; i < text.length(); i++) {
    // Change color for every character (0: BLACK, 1: RED, 2: YELLOW, 3: BLACK, etc.)
    display.setTextColor(colors[i % 3]);
    display.print(text.charAt(i));
  }
  display.display();
  
  delay(15000);

  Serial.println("Color quadrant demo");
  display.clearBuffer();
  // Top-left quadrant - EPD_BLACK
  display.fillRect(0, 0, display.width() / 2, display.height() / 2, EPD_BLACK);
  // Top-right quadrant - EPD_RED  
  display.fillRect(display.width() / 2, 0, display.width() / 2, display.height() / 2, EPD_RED);
  // Bottom-left quadrant - EPD_YELLOW
  display.fillRect(0, display.height() / 2, display.width() / 2, display.height() / 2, EPD_YELLOW);
  // Bottom-right quadrant - assume you have a 4th color like EPD_WHITE or another color
  display.fillRect(display.width() / 2, display.height() / 2, display.width() / 2, display.height() / 2, EPD_WHITE);

  display.display();

  delay(15000);

  Serial.println("Text demo");
  // large block of text
  display.clearBuffer();
  display.setTextSize(1);
  testdrawtext(
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Curabitur "
      "adipiscing ante sed nibh tincidunt feugiat. Maecenas enim massa, "
      "fringilla sed malesuada et, malesuada sit amet turpis. Sed porttitor "
      "neque ut ante pretium vitae malesuada nunc bibendum. Nullam aliquet "
      "ultrices massa eu hendrerit. Ut sed nisi lorem. In vestibulum purus a "
      "tortor imperdiet posuere. ",
      EPD_BLACK);
  display.display();

  delay(15000);

  display.clearBuffer();
  for (int16_t i = 0; i < display.width(); i += 4) {
    display.drawLine(0, 0, i, display.height() - 1, EPD_BLACK);
  }
  for (int16_t i = 0; i < display.height(); i += 4) {
    display.drawLine(display.width() - 1, 0, 0, i, EPD_RED);
  }
  for (int16_t i = 0; i < display.width(); i += 4) {
     display.drawLine(display.width()/2, display.height()-1, i, 0, 
                      EPD_YELLOW);
  }
  
  display.display();

  delay(15000);
}

void testdrawtext(const char *text, uint16_t color) {
  display.setCursor(0, 0);
  display.setTextColor(color);
  display.setTextWrap(true);
  display.print(text);
}
