// SPDX-FileCopyrightText: 2023 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include "Adafruit_TestBed.h"
#include <Arduino_GFX_Library.h>

extern Adafruit_TestBed TB;

Arduino_XCA9554SWSPI *expander = new Arduino_XCA9554SWSPI(
    PCA_TFT_RESET, PCA_TFT_CS, PCA_TFT_SCK, PCA_TFT_MOSI,
    &Wire, 0x3F);
    
Arduino_ESP32RGBPanel *rgbpanel = new Arduino_ESP32RGBPanel(
    TFT_DE, TFT_VSYNC, TFT_HSYNC, TFT_PCLK,
    TFT_R1, TFT_R2, TFT_R3, TFT_R4, TFT_R5,
    TFT_G0, TFT_G1, TFT_G2, TFT_G3, TFT_G4, TFT_G5,
    TFT_B1, TFT_B2, TFT_B3, TFT_B4, TFT_B5,
    1 /* hsync_polarity */, 50 /* hsync_front_porch */, 2 /* hsync_pulse_width */, 44 /* hsync_back_porch */,
    1 /* vsync_polarity */, 16 /* vsync_front_porch */, 2 /* vsync_pulse_width */, 18 /* vsync_back_porch */
    //,1, 30000000
    );

Arduino_RGB_Display *gfx = new Arduino_RGB_Display(
    480 /* width */, 480 /* height */, rgbpanel, 0 /* rotation */, true /* auto_flush */,
    expander, GFX_NOT_DEFINED /* RST */, TL021WVC02_init_operations, sizeof(TL021WVC02_init_operations));

uint16_t *colorWheel;
  
void setup(void)
{  
  Serial.begin(115200);
  //while (!Serial) delay(100);
  
#ifdef GFX_EXTRA_PRE_INIT
  GFX_EXTRA_PRE_INIT();
#endif

  Serial.println("Beginning");
  // Init Display

  Wire.setClock(1000000); // speed up I2C 
  if (!gfx->begin()) {
    Serial.println("gfx->begin() failed!");
  }

  Serial.println("Initialized!");

  gfx->fillScreen(BLACK);

  expander->pinMode(PCA_TFT_BACKLIGHT, OUTPUT);
  expander->digitalWrite(PCA_TFT_BACKLIGHT, HIGH);

  TB.begin();
  colorWheel = (uint16_t *) ps_malloc(480 * 480 * sizeof(uint16_t));
  if (colorWheel) generateColorWheel(colorWheel);
}


uint8_t allpins[] = {SS, SCK, MOSI, MISO, A1, A0};

bool test = false;
void loop()
{  
  if (!test) {
    gfx->draw16bitRGBBitmap(0, 0, colorWheel, 480, 480);
    delay(100);
    return;
  }
  Serial.println("** Test Display!");
  gfx->fillScreen(BLACK);
  gfx->setTextSize(5);
  gfx->setTextColor(WHITE);
  gfx->setTextWrap(false);
  gfx->setCursor(100, gfx->height() / 2 - 175);
  gfx->println("Display OK!");

  if (! TB.testpins(MOSI, A1, allpins, sizeof(allpins))) return;
  if (! TB.testpins(MISO, SS, allpins, sizeof(allpins))) return;
  if (! TB.testpins(SCK, A0, allpins, sizeof(allpins))) return;
  gfx->setCursor(100, gfx->height() / 2 - 125);
  gfx->println("GPIO OK!");

  gfx->setCursor(100, gfx->height() / 2 - 75);
  gfx->println("I2C OK!");
  
  gfx->setCursor(100, gfx->height() / 2 - 25);
  gfx->setTextColor(RED);
  gfx->println("RED");

  gfx->setCursor(100, gfx->height() / 2 + 25);
  gfx->setTextColor(GREEN);
  gfx->println("GREEN");

  gfx->setCursor(100, gfx->height() / 2 + 75);
  gfx->setTextColor(BLUE);
  gfx->println("BLUE");

  Serial.println("** TEST OK!");
  test = false;
}

// https://chat.openai.com/share/8edee522-7875-444f-9fea-ae93a8dfa4ec
void generateColorWheel(uint16_t *colorWheel) {
  float angle;
  uint8_t r, g, b;
  int scaled_index;

  for(int y = 0; y < 240; y++) {
    for(int x = 0; x < 240; x++) {
      angle = atan2(y - 120, x - 120);
      r = uint8_t(127.5 * (cos(angle) + 1));
      g = uint8_t(127.5 * (sin(angle) + 1));
      b = uint8_t(255 - (r + g) / 2);
      uint16_t color = RGB565(r, g, b);

      // Scale this pixel into 4 pixels in the 480x480 buffer
      for(int dy = 0; dy < 2; dy++) {
        for(int dx = 0; dx < 2; dx++) {
          scaled_index = (y * 2 + dy) * 480 + (x * 2 + dx);
          colorWheel[scaled_index] = color;
        }
      }
    }
  }
}
