// SPDX-FileCopyrightText: 2026 Mikey Sklar for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// 4-gray panel info card for the 2.66" 296x152 SSD1680 E-Ink display (#6392,
// ribbon FPC-A003). Flashes a card with the panel's size, chipset, product #,
// and ribbon label, plus a 4-level gray ramp.

#include "Adafruit_ThinkInk.h"

#ifdef ARDUINO_ADAFRUIT_FEATHER_RP2040_THINKINK // Feather RP2040 ThinkInk
#define EPD_DC PIN_EPD_DC
#define EPD_CS PIN_EPD_CS
#define EPD_BUSY PIN_EPD_BUSY
#define SRAM_CS -1
#define EPD_RESET PIN_EPD_RESET
#define EPD_SPI &SPI1
#else
#define EPD_DC 10
#define EPD_CS 9
#define EPD_BUSY 7
#define SRAM_CS 6
#define EPD_RESET 8
#define EPD_SPI &SPI
#endif

ThinkInk_266_Grayscale4_MFGN display(EPD_DC, EPD_RESET, EPD_CS, SRAM_CS, EPD_BUSY, EPD_SPI);

#define CARD_FONT_TITLE 2
#define CARD_FONT_BODY 2

void setup() {
  display.begin(THINKINK_GRAYSCALE4);
  display.clearBuffer();
  display.fillScreen(EPD_WHITE);

  const int16_t w = display.width();
  const int16_t h = display.height();
  const int16_t pad = 6;
  const int16_t row = CARD_FONT_BODY * 8 + 4;

  display.setTextColor(EPD_BLACK);
  display.setTextSize(CARD_FONT_TITLE);
  display.setCursor(pad, pad);
  display.print("Adafruit ThinkInk");

  int16_t y = pad + CARD_FONT_TITLE * 8 + 6;
  display.setTextSize(CARD_FONT_BODY);
  display.setCursor(pad, y);
  display.print("2.66\" 296x152");
  y += row;
  display.setCursor(pad, y);
  display.print("SSD1680  #6392");
  y += row;
  display.setCursor(pad, y);
  display.print("FPC-A003");
  y += row;

  // 4-level gray ramp: black | dark | light | white
  const int16_t rampTop = (y + 8 < h - 16) ? (y + 8) : (h - 16);
  const int16_t rampH = h - rampTop;
  const int16_t seg = w / 4;
  const uint16_t order[4] = {EPD_BLACK, EPD_DARK, EPD_LIGHT, EPD_WHITE};
  for (int i = 0; i < 4; i++) {
    int16_t x = i * seg;
    display.fillRect(x, rampTop, (i < 3) ? seg : (w - x), rampH, order[i]);
  }
  display.drawRect(0, rampTop, w, rampH, EPD_BLACK);
  for (int i = 1; i < 4; i++) {
    display.drawFastVLine(i * seg, rampTop, rampH, EPD_BLACK);
  }

  display.display();
}

void loop() {}
