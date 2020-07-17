// please read credits at the bottom of file

#include <Adafruit_Arcada.h>
#include <Arcada_GifDecoder.h>

/*************** Display setup */
Adafruit_Arcada arcada;
GifDecoder<ARCADA_TFT_WIDTH, ARCADA_TFT_HEIGHT, 12> decoder;

File file;
int16_t  gif_offset_x, gif_offset_y;
#define GIF_DIRECTORY        "/"    // on SD or QSPI

float hotTemp = 24;       // how warm it has to be to be considered hot
float coldTemp = 20;      // how cool it has to be to be considered cold


#if defined(ARDUINO_NRF52840_CIRCUITPLAY)
void setupTemperature() {
}
float readTemperature() {
  return CircuitPlayground.temperature();
}
#endif

#define BRIGHTER_BUTTON        ARCADA_BUTTONMASK_A
#define DIMMER_BUTTON          ARCADA_BUTTONMASK_B


// Setup method runs once, when the sketch starts
void setup() {
  decoder.setScreenClearCallback(screenClearCallback);
  decoder.setUpdateScreenCallback(updateScreenCallback);
  decoder.setDrawPixelCallback(drawPixelCallback);
  decoder.setDrawLineCallback(drawLineCallback);

  decoder.setFileSeekCallback(fileSeekCallback);
  decoder.setFilePositionCallback(filePositionCallback);
  decoder.setFileReadCallback(fileReadCallback);
  decoder.setFileReadBlockCallback(fileReadBlockCallback);

  // Start arcada!
  if (!arcada.arcadaBegin()) {
    Serial.println("Couldn't start Arcada");
    while(1) yield();
  }
  // If we are using TinyUSB & QSPI we will have the filesystem show up!
  arcada.filesysBeginMSD();

  //while (!Serial) delay(10);
  
  Serial.begin(115200);
  Serial.println("Animated GIFs Demo");
  
  arcada.displayBegin();
  arcada.display->fillScreen(ARCADA_BLUE);
  arcada.setBacklight(255);

  if (arcada.filesysBegin()) {
    Serial.println("Found filesystem!");
  } else {
    arcada.haltBox("No filesystem found! For QSPI flash, load CircuitPython. For SD cards, format with FAT");
  }

  if (! arcada.loadConfigurationFile()) {
     //arcada.infoBox("No configuration file found, using default 10 seconds per GIF");
     arcada.display->fillScreen(ARCADA_BLUE);
  } else {
    if (arcada.configJSON.containsKey("hot_temp")) {
      hotTemp = arcada.configJSON["hot_temp"];
    }
    if (arcada.configJSON.containsKey("cold_temp")) {
      coldTemp = arcada.configJSON["hot_temp"];
    }
  }
}

uint32_t cycle_start = 0L;
int8_t currGIF = 0, nextGIF = 0;       // 0 for no change, +1 for hot gif, -1 for cool gif

void loop() {
    if (arcada.recentUSB()) { 
      yield();
      return;       // prioritize USB over GIF decoding
    }

    // Check button presses
    arcada.readButtons();
    uint8_t buttons = arcada.justPressedButtons();
    if (buttons & BRIGHTER_BUTTON) {
      int16_t newbrightness = arcada.getBacklight();   // brightness up
      newbrightness = min(255, newbrightness+25);      // about 10 levels
      Serial.printf("New brightness %d", newbrightness);
      arcada.setBacklight(newbrightness, true);   // save to disk
    }
    if (buttons & DIMMER_BUTTON) {
      int16_t newbrightness = arcada.getBacklight();   // brightness down
      newbrightness = max(25, newbrightness-25);       // about 10 levels
      Serial.printf("New brightness %d", newbrightness);
      arcada.setBacklight(newbrightness, true);   // save to disk
    }

    uint32_t now = millis();

    // at least one 'cycle' elapsed, check if its time to change gifs
    if(decoder.getCycleNo() > 1) {
      // Print the stats for this GIF    
      char buf[80];
      int32_t frames       = decoder.getFrameCount();
      int32_t cycle_design = decoder.getCycleTime();  // Intended duration
      int32_t cycle_actual = now - cycle_start;       // Actual duration
      int32_t percent = 100 * cycle_design / cycle_actual;
      sprintf(buf, "[%ld frames = %ldms] actual: %ldms speed: %ld%%",
              frames, cycle_design, cycle_actual, percent);
      Serial.println(buf);

      float temp = readTemperature();
      Serial.printf("Temp = %0.1f C\n", temp);
      if (temp >= hotTemp) {
        file = arcada.open("hot.gif");
      } else if (temp <= coldTemp) {
        file = arcada.open("cold.gif");
      } else {
        file = arcada.open("neutral.gif");
      }

      cycle_start = now;
      
      if (!file) {
        Serial.println("Gif not found!");
        return;
      }

      arcada.display->dmaWait();
      arcada.display->endWrite();   // End transaction from any prior callback
      arcada.display->fillScreen(ARCADA_BLACK);
      decoder.startDecoding();

      // Center the GIF
      uint16_t w, h;
      decoder.getSize(&w, &h);
      Serial.print("Width: "); Serial.print(w); Serial.print(" height: "); Serial.println(h);
      if (w < arcada.display->width()) {
        gif_offset_x = (arcada.display->width() - w) / 2;
      } else {
        gif_offset_x = 0;
      }
      if (h < arcada.display->height()) {
        gif_offset_y = (arcada.display->height() - h) / 2;
      } else {
        gif_offset_y = 0;
      }
    }

    decoder.decodeFrame();
}

/******************************* Drawing functions */

void updateScreenCallback(void) {  }

void screenClearCallback(void) {  }

void drawPixelCallback(int16_t x, int16_t y, uint8_t red, uint8_t green, uint8_t blue) {
    arcada.display->drawPixel(x, y, arcada.display->color565(red, green, blue));
#ifdef ADAFRUIT_MONSTER_M4SK_EXPRESS
    arcada.display2->drawPixel(x, y, arcada.display->color565(red, green, blue));
#endif
}

void drawLineCallback(int16_t x, int16_t y, uint8_t *buf, int16_t w, uint16_t *palette, int16_t skip) {
    uint16_t maxline = arcada.display->width();
    bool splitdisplay = false;
    
    uint8_t pixel;
    //uint32_t t = millis();
    x += gif_offset_x;
    y += gif_offset_y;
    if (y >= arcada.display->height() || x >= maxline ) {
      return;
    }
    
#ifdef ADAFRUIT_MONSTER_M4SK_EXPRESS
    // two possibilities
    if ((x + w) > 2*maxline) {
      w = 2*maxline - x;
    } 
    if ((x + w) > maxline) {
      splitdisplay = true;  // split the gif over both displays
    }
#else
    if (x + w > maxline) {
      w = maxline - x;
    }
#endif
    if (w <= 0) return;

    //Serial.printf("Line (%d, %d) %d pixels skipping %d\n", x, y, w, skip);

    uint16_t buf565[2][w];
    bool first = true; // First write op on this line?
    uint8_t bufidx = 0;
    uint16_t *ptr;

    for (int i = 0; i < w; ) {
        int n = 0, startColumn = i;
        ptr = &buf565[bufidx][0];
        // Handle opaque span of pixels (stop at end of line or first transparent pixel)
        if (skip == -1) {// no transparent pixels
          while(i < w) {
            ptr[n++] = palette[buf[i++]];
          }
        }
        else {
          while((i < w) && ((pixel = buf[i++]) != skip)) {
            ptr[n++] = palette[pixel];
          }
        }
        if (n) {
            arcada.display->dmaWait(); // Wait for prior DMA transfer to complete
#ifdef ADAFRUIT_MONSTER_M4SK_EXPRESS
            arcada.display2->dmaWait(); // Wait for prior DMA transfer to complete
#endif
            if (first) {
              arcada.display->endWrite();   // End transaction from prior callback
              arcada.display->startWrite(); // Start new display transaction
#ifdef ADAFRUIT_MONSTER_M4SK_EXPRESS
              arcada.display2->endWrite();   // End transaction from prior callback
              arcada.display2->startWrite(); // Start new display transaction
#endif
              first = false;
            }
            arcada.display->setAddrWindow(x + startColumn, y, min(maxline, n), 1);
            arcada.display->writePixels(ptr, min(maxline, n), false, true);
#ifdef ADAFRUIT_MONSTER_M4SK_EXPRESS
            if (! splitdisplay) { // same image on both!
              arcada.display2->setAddrWindow(x + startColumn, y, min(maxline, n), 1);
              arcada.display2->writePixels(ptr, min(maxline, n), false, true);
            } else {
              arcada.display2->setAddrWindow(x + startColumn, y, n-maxline, 1);
              arcada.display2->writePixels(ptr+maxline, n-maxline, false, true);
            }
#endif
            bufidx = 1 - bufidx;
        }
    }
//    arcada.display->dmaWait(); // Wait for last DMA transfer to complete
#ifdef ADAFRUIT_MONSTER_M4SK_EXPRESS
    arcada.display2->dmaWait(); // Wait for last DMA transfer to complete
#endif
}


bool fileSeekCallback(unsigned long position) {
  return file.seek(position);
}

unsigned long filePositionCallback(void) { 
  return file.position(); 
}

int fileReadCallback(void) {
    return file.read(); 
}

int fileReadBlockCallback(void * buffer, int numberOfBytes) {
    return file.read((uint8_t*)buffer, numberOfBytes); //.kbv
}


/*
    Animated GIFs Display Code for SmartMatrix and 32x32 RGB LED Panels

    Uses SmartMatrix Library for Teensy 3.1 written by Louis Beaudoin at pixelmatix.com

    Written by: Craig A. Lindley

    Copyright (c) 2014 Craig A. Lindley
    Refactoring by Louis Beaudoin (Pixelmatix)

    Permission is hereby granted, free of charge, to any person obtaining a copy of
    this software and associated documentation files (the "Software"), to deal in
    the Software without restriction, including without limitation the rights to
    use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
    the Software, and to permit persons to whom the Software is furnished to do so,
    subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
    FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
    COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
    IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
    CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
*/

/*
    This example displays 32x32 GIF animations loaded from a SD Card connected to the Teensy 3.1
    The GIFs can be up to 32 pixels in width and height.
    This code has been tested with 32x32 pixel and 16x16 pixel GIFs, but is optimized for 32x32 pixel GIFs.

    Wiring is on the default Teensy 3.1 SPI pins, and chip select can be on any GPIO,
    set by defining SD_CS in the code below
    Function     | Pin
    DOUT         |  11
    DIN          |  12
    CLK          |  13
    CS (default) |  15

    This code first looks for .gif files in the /gifs/ directory
    (customize below with the GIF_DIRECTORY definition) then plays random GIFs in the directory,
    looping each GIF for displayTimeSeconds

    This example is meant to give you an idea of how to add GIF playback to your own sketch.
    For a project that adds GIF playback with other features, take a look at
    Light Appliance and Aurora:
    https://github.com/CraigLindley/LightAppliance
    https://github.com/pixelmatix/aurora

    If you find any GIFs that won't play properly, please attach them to a new
    Issue post in the GitHub repo here:
    https://github.com/pixelmatix/AnimatedGIFs/issues
*/

/*
    CONFIGURATION:
    - If you're using SmartLED Shield V4 (or above), uncomment the line that includes <SmartMatrixShieldV4.h>
    - update the "SmartMatrix configuration and memory allocation" section to match the width and height and other configuration of your display
    - Note for 128x32 and 64x64 displays with Teensy 3.2 - need to reduce RAM:
      set kRefreshDepth=24 and kDmaBufferRows=2 or set USB Type: "None" in Arduino,
      decrease refreshRate in setup() to 90 or lower to get good an accurate GIF frame rate
    - Set the chip select pin for your board.  On Teensy 3.5/3.6, the onboard microSD CS pin is "BUILTIN_SDCARD"
*/
