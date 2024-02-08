// SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Arduino.h>
#include <Arduino_GFX.h>
#include "databus/Arduino_XCA9554SWSPI.h"
#include "databus/Arduino_ESP32RGBPanel.h"
#include "display/Arduino_RGB_Display.h"

#define IMG_WIDTH 146
#define IMG_HEIGHT 135

// uncomment for 240x960 bar display
//#define long_display

// otherwise comment out for 320x820 bar display

Arduino_XCA9554SWSPI *expander = new Arduino_XCA9554SWSPI(
    PCA_TFT_RESET, PCA_TFT_CS, PCA_TFT_SCK, PCA_TFT_MOSI,
    &Wire, 0x3F);

#ifdef long_display 
  #include "sushi_960x240.h"
  Arduino_ESP32RGBPanel *rgbpanel = new Arduino_ESP32RGBPanel(
    TFT_DE, TFT_VSYNC, TFT_HSYNC, TFT_PCLK,
    TFT_R1, TFT_R2, TFT_R3, TFT_R4, TFT_R5,
    TFT_G0, TFT_G1, TFT_G2, TFT_G3, TFT_G4, TFT_G5,
    TFT_B1, TFT_B2, TFT_B3, TFT_B4, TFT_B5,
    1 /* hync_polarity */, 20 /* hsync_front_porch */, 8 /* hsync_pulse_width */, 20 /* hsync_back_porch */,
    1 /* vsync_polarity */, 20 /* vsync_front_porch */, 8 /* vsync_pulse_width */, 20 /* vsync_back_porch, */,
    0 /* pclk_active_neg */, GFX_NOT_DEFINED /* prefer_speed */, false /* useBigEndian */, 0 /* de_idle_high */,
    0 /* pclk_idle_high */ );

Arduino_RGB_Display *gfx = new Arduino_RGB_Display(
// 3.2" 320x820 rectangle bar display
    240 /* width */, 960 /* height */, rgbpanel, 0 /* rotation */, true /* auto_flush */,
    expander, GFX_NOT_DEFINED /* RST */, HD371001C40_init_operations, sizeof(HD371001C40_init_operations), 120 /* col_offset1 */);

const int numberOfBitmaps = 8;
int display_w = 240;
int display_h = 960;
int sushi_h = 15;
int sushi_offset = 62;

#else
  #include "sushi_320x820.h"
  Arduino_ESP32RGBPanel *rgbpanel = new Arduino_ESP32RGBPanel(
    TFT_DE, TFT_VSYNC, TFT_HSYNC, TFT_PCLK,
    TFT_R1, TFT_R2, TFT_R3, TFT_R4, TFT_R5,
    TFT_G0, TFT_G1, TFT_G2, TFT_G3, TFT_G4, TFT_G5,
    TFT_B1, TFT_B2, TFT_B3, TFT_B4, TFT_B5,
    1 /* hsync_polarity */, 50 /* hsync_front_porch */, 2 /* hsync_pulse_width */, 44 /* hsync_back_porch */,
    1 /* vsync_polarity */, 16 /* vsync_front_porch */, 2 /* vsync_pulse_width */, 18 /* vsync_back_porch */
    );

Arduino_RGB_Display *gfx = new Arduino_RGB_Display(
// 3.2" 320x820 rectangle bar display
    320 /* width */, 820 /* height */, rgbpanel, 0 /* rotation */, true /* auto_flush */,
    expander, GFX_NOT_DEFINED /* RST */, tl032fwv01_init_operations, sizeof(tl032fwv01_init_operations));

const int numberOfBitmaps = 7;
int display_w = 320;
int display_h = 820;
int sushi_h = 29;
int sushi_offset = 55;

#endif

struct BitmapInfo {
  int yPosition;
  int bitmapIndex;
};

BitmapInfo bitmaps[numberOfBitmaps];

void setup(void)
{  
  Serial.begin(115200);
  //while (!Serial) delay(100);

#ifdef GFX_EXTRA_PRE_INIT
  GFX_EXTRA_PRE_INIT();
#endif

  Serial.println("Beginning");

  Wire.setClock(400000);
  if (!gfx->begin()) {
    Serial.println("gfx->begin() failed!");
  }

  Serial.println("Initialized!");

  gfx->fillScreen(BLACK);

  expander->pinMode(PCA_TFT_BACKLIGHT, OUTPUT);
  expander->digitalWrite(PCA_TFT_BACKLIGHT, HIGH);

  Serial.println("Adafruit Sushi Conveyer Belt!");

#ifdef GFX_EXTRA_PRE_INIT
  GFX_EXTRA_PRE_INIT();
#endif

#ifdef GFX_BL
  pinMode(GFX_BL, OUTPUT);
  digitalWrite(GFX_BL, HIGH);
#endif

  for (int i = 0; i < numberOfBitmaps; i++) {
    bitmaps[i].yPosition = (-IMG_WIDTH) * i;
    bitmaps[i].bitmapIndex = random(0, myBitmapallArray_LEN - 1);
  }
  
  gfx->draw16bitRGBBitmap(0, 0, (uint16_t *)myBitmapallArray[6], display_w, display_h);

}

void loop()
{

 for (int i = 0; i < numberOfBitmaps; i++) {
    bitmaps[i].yPosition++;
    if (bitmaps[i].yPosition > gfx->height()) {

      bitmaps[i].yPosition = -IMG_WIDTH - sushi_offset;
      bitmaps[i].bitmapIndex = random(0, myBitmapallArray_LEN - 1);
    }
    gfx->draw16bitRGBBitmap(sushi_h, bitmaps[i].yPosition, (uint16_t *)myBitmapallArray[bitmaps[i].bitmapIndex], IMG_HEIGHT, IMG_WIDTH);
  }
  delay(1);
  
}