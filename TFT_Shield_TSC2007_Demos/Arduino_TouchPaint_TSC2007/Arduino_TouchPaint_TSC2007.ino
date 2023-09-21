// SPDX-FileCopyrightText: 2023 Limor Fried/Ladyada for Adafruit Industries
// SPDX-License-Identifier: MIT

/***************************************************
  This is our touchscreen painting example for the updated Adafruit
  ILI9341 Shield with TSC2007
  ----> http://www.adafruit.com/products/1651

  Check out the links above for our tutorials and wiring diagrams
  These displays use SPI to communicate, 4 or 5 pins are required to
  interface (RST is optional)
  Adafruit invests time and resources providing this open source code,
  please support Adafruit and open-source hardware by purchasing
  products from Adafruit!

  Written by Limor Fried/Ladyada for Adafruit Industries.
  MIT license, all text above must be included in any redistribution
 ****************************************************/


#include <Adafruit_GFX.h>
#include <SPI.h>
#include <Wire.h>
#include <Adafruit_ILI9341.h>
#include <Adafruit_TSC2007.h>

// This is calibration data for the raw touch data to the screen coordinates
#define TS_MINX 150
#define TS_MINY 130
#define TS_MAXX 3800
#define TS_MAXY 4000
#define TS_MIN_PRESSURE 200

Adafruit_TSC2007 ts;

// The display also uses hardware SPI, plus #9 & #10
#define TFT_CS 10
#define TFT_DC 9
Adafruit_ILI9341 tft = Adafruit_ILI9341(TFT_CS, TFT_DC);

// Size of the color selection boxes and the paintbrush size
#define BOXSIZE 40
#define PENRADIUS 3
int oldcolor, currentcolor;

void setup(void) {

  Serial.begin(115200);
  // while (!Serial) delay(10);
  
  tft.begin();

  if (!ts.begin()) {
    Serial.println("Couldn't start touchscreen controller");
    while (1);
  }
  Serial.println("Touchscreen started");
  
  tft.fillScreen(ILI9341_BLACK);
  
  // make the color selection boxes
  tft.fillRect(0, 0, BOXSIZE, BOXSIZE, ILI9341_RED);
  tft.fillRect(BOXSIZE, 0, BOXSIZE, BOXSIZE, ILI9341_YELLOW);
  tft.fillRect(BOXSIZE*2, 0, BOXSIZE, BOXSIZE, ILI9341_GREEN);
  tft.fillRect(BOXSIZE*3, 0, BOXSIZE, BOXSIZE, ILI9341_CYAN);
  tft.fillRect(BOXSIZE*4, 0, BOXSIZE, BOXSIZE, ILI9341_BLUE);
  tft.fillRect(BOXSIZE*5, 0, BOXSIZE, BOXSIZE, ILI9341_MAGENTA);
 
  // select the current color 'red'
  tft.drawRect(0, 0, BOXSIZE, BOXSIZE, ILI9341_WHITE);
  currentcolor = ILI9341_RED;
}

void loop(){
  uint16_t x, y, z1, z2;
  if (ts.read_touch(&x, &y, &z1, &z2) && (z1 > TS_MIN_PRESSURE)) {

    Serial.print("Touch point: (");
    Serial.print(x); Serial.print(", ");
    Serial.print(y); Serial.print(", ");
    Serial.print(z1); Serial.print(" / ");
    Serial.print(z2); Serial.println(")");  
   
    // Scale from ~0->4000 to tft.width using the calibration #'s
    x = map(x, TS_MINX, TS_MAXX, 0, tft.width());
    y = map(y, TS_MINY, TS_MAXY, 0, tft.height());

    if (y < BOXSIZE) {
       oldcolor = currentcolor;
  
       if (x < BOXSIZE) { 
         currentcolor = ILI9341_RED; 
         tft.drawRect(0, 0, BOXSIZE, BOXSIZE, ILI9341_WHITE);
       } else if (x < BOXSIZE*2) {
         currentcolor = ILI9341_YELLOW;
         tft.drawRect(BOXSIZE, 0, BOXSIZE, BOXSIZE, ILI9341_WHITE);
       } else if (x < BOXSIZE*3) {
         currentcolor = ILI9341_GREEN;
         tft.drawRect(BOXSIZE*2, 0, BOXSIZE, BOXSIZE, ILI9341_WHITE);
       } else if (x < BOXSIZE*4) {
         currentcolor = ILI9341_CYAN;
         tft.drawRect(BOXSIZE*3, 0, BOXSIZE, BOXSIZE, ILI9341_WHITE);
       } else if (x < BOXSIZE*5) {
         currentcolor = ILI9341_BLUE;
         tft.drawRect(BOXSIZE*4, 0, BOXSIZE, BOXSIZE, ILI9341_WHITE);
       } else if (x < BOXSIZE*6) {
         currentcolor = ILI9341_MAGENTA;
         tft.drawRect(BOXSIZE*5, 0, BOXSIZE, BOXSIZE, ILI9341_WHITE);
       }
  
       if (oldcolor != currentcolor) {
          if (oldcolor == ILI9341_RED) 
            tft.fillRect(0, 0, BOXSIZE, BOXSIZE, ILI9341_RED);
          if (oldcolor == ILI9341_YELLOW) 
            tft.fillRect(BOXSIZE, 0, BOXSIZE, BOXSIZE, ILI9341_YELLOW);
          if (oldcolor == ILI9341_GREEN) 
            tft.fillRect(BOXSIZE*2, 0, BOXSIZE, BOXSIZE, ILI9341_GREEN);
          if (oldcolor == ILI9341_CYAN) 
            tft.fillRect(BOXSIZE*3, 0, BOXSIZE, BOXSIZE, ILI9341_CYAN);
          if (oldcolor == ILI9341_BLUE) 
            tft.fillRect(BOXSIZE*4, 0, BOXSIZE, BOXSIZE, ILI9341_BLUE);
          if (oldcolor == ILI9341_MAGENTA) 
            tft.fillRect(BOXSIZE*5, 0, BOXSIZE, BOXSIZE, ILI9341_MAGENTA);
       }
    }
    if (((y-PENRADIUS) > BOXSIZE) && ((y+PENRADIUS) < tft.height())) {
      tft.fillCircle(x, y, PENRADIUS, currentcolor);
    }
  }
}
