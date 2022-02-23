/**************************************************************************
  This is an example of using the built in TFT.

  Written by Limor Fried/Ladyada for Adafruit Industries.
  MIT license, all text above must be included in any redistribution
 **************************************************************************/

#include <Adafruit_GFX.h>    // Core graphics library
#include <Adafruit_ST7789.h> // Hardware-specific library for ST7789
#include <SPI.h>

// DELETE THIS LINE AND THE REST OF THIS COMMENT BELOW THIS LINE BEFORE SUBMITTING TO LEARN
// Replace TFT_WIDTH_IN_PIXELS, TFT_HEIGHT_IN_PIXELS, and TFT_ROTATION_VALUE with the
// appropriate values for the intended board.
// For example, for the TFT Feather, TFT_WIDTH is 240, TFT_HEIGHT is 135 and ROTATION is 3.
#define TFT_WIDTH TFT_WIDTH_IN_PIXELS
#define TFT_HEIGHT TFT_HEIGHT_IN_PIXELS
#define TFT_ROTATION TFT_ROTATION_VALUE

// Use dedicated hardware SPI pins
// DELETE THIS LINE AND THE REST OF THIS COMMENT BELOW THIS LINE BEFORE SUBMITTING TO LEARN
// Update each pin to match the TFT SPI pin names for the appropriate board.
// For example, fort the TFT Feather, update to TFT_CS, TFT_DC, and TFT_RST.
Adafruit_ST7789 tft = Adafruit_ST7789(TFT_CS_PIN_NAME, TFT_DC_PIN_NAME, TFT_RST_PIN_NAME);

float p = 3.1415926;

void setup(void) {
  Serial.begin(9600);
  Serial.print(F("Hello! TFT Test"));

  // Turn on backlight
  // DELETE THIS LINE AND THE REST OF THIS COMMENT BELOW THIS LINE BEFORE SUBMITTING TO LEARN
  // Update TFT_BACKLIGHT_PIN_NAME to the TFT backlight pin for the appropriate board.
  // For example, for the TFT Feather, you would use TFT_BACKLITE
  pinMode(TFT_BACKLIGHT_PIN_NAME, OUTPUT);
  digitalWrite(TFT_BACKLIGHT_PIN_NAME, HIGH);

  // Turn on the TFT / I2C power supply
  // DELETE THIS LINE AND THE REST OF THIS COMMENT BELOW THIS LINE BEFORE SUBMITTING TO LEARN
  // If this section is NOT applicable to the board, remove the entire section including
  // the comment above "DELETE THIS LINE...". If this section IS applicable to the board,
  // update TFT_POWER_PIN_NAME to the TFT power pin for the specific board and delete
  // the instructional-only parts of this comment starting with "DELETE THIS LINE...".
  // For example, for the CLUE, you would remove this entire section through delay(10);.
  // For example, for the TFT Feather, update to TFT_I2C_POWER.
  pinMode(TFT_POWER_PIN_NAME, OUTPUT);
  digitalWrite(TFT_POWER_PIN_NAME, HIGH);
  delay(10);

  // Initialise TFT
  tft.init(TFT_HEIGHT, TFT_WIDTH);
  tft.setRotation(TFT_ROTATION);
  tft.fillScreen(ST77XX_BLACK);

  Serial.println(F("Initialized"));

  uint16_t time = millis();
  tft.fillScreen(ST77XX_BLACK);
  time = millis() - time;

  Serial.println(time, DEC);
  delay(500);

  // Large block of text
  tft.fillScreen(ST77XX_BLACK);
  testdrawtext(
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Curabitur "
      "adipiscing ante sed nibh tincidunt feugiat. Maecenas enim massa, "
      "fringilla sed malesuada et, malesuada sit amet turpis. Sed porttitor "
      "neque ut ante pretium vitae malesuada nunc bibendum. Nullam aliquet "
      "ultrices massa eu hendrerit. Ut sed nisi lorem. In vestibulum purus a "
      "tortor imperdiet posuere. ",
      ST77XX_WHITE);
  delay(1000);

  // TFT print function!
  tftPrintTest();
  delay(4000);

  // A single pixel
  tft.drawPixel(tft.width() / 2, tft.height() / 2, ST77XX_GREEN);
  delay(500);

  // Line draw test
  testlines(ST77XX_YELLOW);
  delay(500);

  // Optimised lines
  testfastlines(ST77XX_RED, ST77XX_BLUE);
  delay(500);

  testdrawrects(ST77XX_GREEN);
  delay(500);

  testfillrects(ST77XX_YELLOW, ST77XX_MAGENTA);
  delay(500);

  tft.fillScreen(ST77XX_BLACK);
  testfillcircles(10, ST77XX_BLUE);
  testdrawcircles(10, ST77XX_WHITE);
  delay(500);

  testroundrects();
  delay(500);

  testtriangles();
  delay(500);

  mediabuttons();
  delay(500);

  Serial.println("done");
  delay(1000);
}

void loop() {
  tft.invertDisplay(true);
  delay(500);
  tft.invertDisplay(false);
  delay(500);
}

void testlines(uint16_t color) {
  tft.fillScreen(ST77XX_BLACK);
  for (int16_t x = 0; x < tft.width(); x += 6) {
    tft.drawLine(0, 0, x, tft.height() - 1, color);
    delay(0);
  }
  for (int16_t y = 0; y < tft.height(); y += 6) {
    tft.drawLine(0, 0, tft.width() - 1, y, color);
    delay(0);
  }

  tft.fillScreen(ST77XX_BLACK);
  for (int16_t x = 0; x < tft.width(); x += 6) {
    tft.drawLine(tft.width() - 1, 0, x, tft.height() - 1, color);
    delay(0);
  }
  for (int16_t y = 0; y < tft.height(); y += 6) {
    tft.drawLine(tft.width() - 1, 0, 0, y, color);
    delay(0);
  }

  tft.fillScreen(ST77XX_BLACK);
  for (int16_t x = 0; x < tft.width(); x += 6) {
    tft.drawLine(0, tft.height() - 1, x, 0, color);
    delay(0);
  }
  for (int16_t y = 0; y < tft.height(); y += 6) {
    tft.drawLine(0, tft.height() - 1, tft.width() - 1, y, color);
    delay(0);
  }

  tft.fillScreen(ST77XX_BLACK);
  for (int16_t x = 0; x < tft.width(); x += 6) {
    tft.drawLine(tft.width() - 1, tft.height() - 1, x, 0, color);
    delay(0);
  }
  for (int16_t y = 0; y < tft.height(); y += 6) {
    tft.drawLine(tft.width() - 1, tft.height() - 1, 0, y, color);
    delay(0);
  }
}

void testdrawtext(char *text, uint16_t color) {
  tft.setCursor(0, 0);
  tft.setTextColor(color);
  tft.setTextWrap(true);
  tft.print(text);
}

void testfastlines(uint16_t color1, uint16_t color2) {
  tft.fillScreen(ST77XX_BLACK);
  for (int16_t y = 0; y < tft.height(); y += 5) {
    tft.drawFastHLine(0, y, tft.width(), color1);
  }
  for (int16_t x = 0; x < tft.width(); x += 5) {
    tft.drawFastVLine(x, 0, tft.height(), color2);
  }
}

void testdrawrects(uint16_t color) {
  tft.fillScreen(ST77XX_BLACK);
  for (int16_t x = 0; x < tft.width(); x += 6) {
    tft.drawRect(tft.width() / 2 - x / 2, tft.height() / 2 - x / 2, x, x,
                 color);
  }
}

void testfillrects(uint16_t color1, uint16_t color2) {
  tft.fillScreen(ST77XX_BLACK);
  for (int16_t x = tft.width() - 1; x > 6; x -= 6) {
    tft.fillRect(tft.width() / 2 - x / 2, tft.height() / 2 - x / 2, x, x,
                 color1);
    tft.drawRect(tft.width() / 2 - x / 2, tft.height() / 2 - x / 2, x, x,
                 color2);
  }
}

void testfillcircles(uint8_t radius, uint16_t color) {
  for (int16_t x = radius; x < tft.width(); x += radius * 2) {
    for (int16_t y = radius; y < tft.height(); y += radius * 2) {
      tft.fillCircle(x, y, radius, color);
    }
  }
}

void testdrawcircles(uint8_t radius, uint16_t color) {
  for (int16_t x = 0; x < tft.width() + radius; x += radius * 2) {
    for (int16_t y = 0; y < tft.height() + radius; y += radius * 2) {
      tft.drawCircle(x, y, radius, color);
    }
  }
}

void testtriangles() {
  tft.fillScreen(ST77XX_BLACK);
  uint16_t color = 0xF800;
  int t;
  int w = tft.width() / 2;
  int x = tft.height() - 1;
  int y = 0;
  int z = tft.width();
  for (t = 0; t <= 15; t++) {
    tft.drawTriangle(w, y, y, x, z, x, color);
    x -= 4;
    y += 4;
    z -= 4;
    color += 100;
  }
}

void testroundrects() {
  tft.fillScreen(ST77XX_BLACK);
  uint16_t color = 100;
  int i;
  int t;
  for (t = 0; t <= 4; t += 1) {
    int x = 0;
    int y = 0;
    int w = tft.width() - 2;
    int h = tft.height() - 2;
    for (i = 0; i <= 16; i += 1) {
      tft.drawRoundRect(x, y, w, h, 5, color);
      x += 2;
      y += 3;
      w -= 4;
      h -= 6;
      color += 1100;
    }
    color += 100;
  }
}

void tftPrintTest() {
  tft.setTextWrap(false);
  tft.fillScreen(ST77XX_BLACK);
  tft.setCursor(0, 30);
  tft.setTextColor(ST77XX_RED);
  tft.setTextSize(1);
  tft.println("Hello World!");
  tft.setTextColor(ST77XX_YELLOW);
  tft.setTextSize(2);
  tft.println("Hello World!");
  tft.setTextColor(ST77XX_GREEN);
  tft.setTextSize(3);
  tft.println("Hello World!");
  tft.setTextColor(ST77XX_BLUE);
  tft.setTextSize(4);
  tft.print(1234.567);
  delay(1500);
  tft.setCursor(0, 0);
  tft.fillScreen(ST77XX_BLACK);
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(0);
  tft.println("Hello World!");
  tft.setTextSize(1);
  tft.setTextColor(ST77XX_GREEN);
  tft.print(p, 6);
  tft.println(" Want pi?");
  tft.println(" ");
  tft.print(8675309, HEX); // print 8,675,309 out in HEX!
  tft.println(" Print HEX!");
  tft.println(" ");
  tft.setTextColor(ST77XX_WHITE);
  tft.println("Sketch has been");
  tft.println("running for: ");
  tft.setTextColor(ST77XX_MAGENTA);
  tft.print(millis() / 1000);
  tft.setTextColor(ST77XX_WHITE);
  tft.print(" seconds.");
}

void mediabuttons() {
  // Play "button"
  tft.fillScreen(ST77XX_BLACK);
  tft.fillRoundRect(25, 5, 78, 60, 8, ST77XX_WHITE);
  tft.fillTriangle(42, 12, 42, 60, 90, 40, ST77XX_RED);
  delay(500);
  // Pause "button"
  tft.fillRoundRect(25, 70, 78, 60, 8, ST77XX_WHITE);
  tft.fillRoundRect(39, 78, 20, 45, 5, ST77XX_GREEN);
  tft.fillRoundRect(69, 78, 20, 45, 5, ST77XX_GREEN);
  delay(500);
  // Play color
  tft.fillTriangle(42, 12, 42, 60, 90, 40, ST77XX_BLUE);
  delay(50);
  // Pause color
  tft.fillRoundRect(39, 78, 20, 45, 5, ST77XX_RED);
  tft.fillRoundRect(69, 78, 20, 45, 5, ST77XX_RED);
  // Play color
  tft.fillTriangle(42, 12, 42, 60, 90, 40, ST77XX_GREEN);
}
