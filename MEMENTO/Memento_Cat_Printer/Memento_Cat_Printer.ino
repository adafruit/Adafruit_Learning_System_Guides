// SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Arduino.h>
#include "Adafruit_PyCamera.h"
#include <CatGFX.h>
// CatGFX library source is included in the project with modifications
// https://github.com/TheNitek/CatGFX

Adafruit_PyCamera pycamera;

bool frame = true;

String frame_info[] = {"NO", "YES"};

// Buffer which can hold 400 lines
byte buffer[48 * 400] = {0};

// Create a printer supporting those 400 lines
CatPrinter cat(400);

// hard reset
void(* resetFunc) (void) = 0;

// atkinson dithering algorithm parameters from CircuitPython
struct DitherAlgorithmInfo {
    int mx, my;
    int divisor;
    struct { int dx, dy, dl; } terms[4];
} atkinson = {
    1, 1, 8, // mx, my, divisor
    {
        {1, 0, 1}, {-1, 1, 1}, {0, 1, 1}, {1, 1, 1} // dx, dy, dl
    }
};

// this sends a full bitmap to the printer
void gameboy(uint16_t *source, int width, int height, bool createForPrinter) {
    uint16_t *bitmap = new uint16_t[width * height];
    int16_t *errorBuffer = new int16_t[(width + 2) * (height + 2)]();
    uint8_t *bitmapForPrinter = nullptr;
    if (createForPrinter) {
        bitmapForPrinter = new uint8_t[(width * height)]();
    }
    // dither the pixels
    // referenced from CP module
    for (int y = 0; y < height; y++) {
      for (int x = 0; x < width; x++) {
          int idx = (y + 1) * (width + 2) + (x + 1);
          uint16_t rgb = source[y * width + x];
          uint8_t r = (rgb & 0xF800) >> 8;
          uint8_t g = (rgb & 0x07E0) >> 3;
          uint8_t b = (rgb & 0x001F) << 3;
          uint8_t grayscale = (r * 30 + g * 59 + b * 11) / 100;
          grayscale += errorBuffer[idx] / atkinson.divisor;
          uint16_t outPixel = grayscale > 127 ? 0xFFFF : 0x0000; // White or Black for RGB bitmap
          bitmap[y * width + x] = outPixel;
          if (createForPrinter) {
              if (grayscale <= 127) {
                  bitmapForPrinter[(y * width + x) / 8] |= (1 << (7 - (x % 8)));
              }
          }
          int16_t error = grayscale - (outPixel ? 255 : 0);
          for (int i = 0; i < 4; i++) {
              int dx = atkinson.terms[i].dx, dy = atkinson.terms[i].dy;
              errorBuffer[idx + dy * (width + 2) + dx] += error * atkinson.terms[i].dl;
          }
      }
  }
    if (createForPrinter == true) {
        cat.fillScreen(1);
        cat.drawBitmap(72, 25, bitmapForPrinter, 240, 240, 0);
        if (frame == true) {
          cat.drawRect(50, 0, 285, 350, 0);
          cat.drawRect(71, 24, 242, 242, 0);
          cat.setTextSize(2);
          cat.setTextColor(0);
          cat.setCursor(72, 300);
          cat.print("shot on MEMENTO");
        }
        delay(500);
        Serial.println("Printing...");
        cat.printBuffer();
        delay(500);
        Serial.println("scrolling..");
        cat.feed(50);
        Serial.println("Done!");
    } 
    pycamera.drawRGBBitmap(0, 0, bitmap, width, height);
    pycamera.refresh();
    delete[] bitmap;
    delete[] errorBuffer;
    delete[] bitmapForPrinter;
}

void setup() {
  Serial.begin(115200);
  // while (!Serial) delay(10);
  Serial.println();
  if (!pycamera.begin()) {
    Serial.println("Failed to initialize pyCamera interface");
    while (1)
      yield();
  }
  Serial.println("pyCamera hardware initialized!");
  pycamera.fillScreen(pycamera.color565(0, 0, 0));
  pycamera.setCursor(10, 10);
  pycamera.setTextSize(2);
  pycamera.setTextColor(pycamera.color565(0, 0, 255));
  pycamera.print("CONNECTING..");
  Serial.print("Connecting to cat printer..");
  cat.begin(buffer, sizeof(buffer));
  Serial.print(".");
  cat.resetNameArray();
  Serial.print(".");
  cat.addNameArray((char *)"MX06");
  Serial.println(".");
  if (cat.connect()) {
    Serial.println("Connected!");
    }
    else {
    Serial.println("Could not find printer! Resetting..");
    pycamera.fillScreen(pycamera.color565(0, 0, 0));
    pycamera.setCursor(10, 10);
    pycamera.setTextSize(2);
    pycamera.setTextColor(pycamera.color565(255, 0, 0));
    pycamera.print("Could not\nfind printer!\nResetting..");
    delay(200);
    resetFunc();
  }
  Serial.println("going into loop");
}

void loop() {
  pycamera.readButtons();
  pycamera.captureFrame();
  pycamera.setNeopixel(0x00FF00);
  // blits gameboy filter to display but does not print
  gameboy((uint16_t *)pycamera.fb->getBuffer(), 240, 240, false);
  // pressing shutter prints the frame
  if (pycamera.justPressed(SHUTTER_BUTTON)) {
    pycamera.setNeopixel(0x0000FF);
    pycamera.setCursor(25, 25);
    pycamera.setTextSize(3);
    pycamera.setTextColor(pycamera.color565(255, 0, 255));
    pycamera.print("PRINTING..");
    gameboy((uint16_t *)pycamera.fb->getBuffer(), 240, 240, true);
    Serial.println("SHUTTER");
  }

  if (pycamera.justPressed(AWEXP_BUTTON_SEL)) {
    frame = not frame;
    pycamera.fillScreen(pycamera.color565(0, 0, 0));
    pycamera.setCursor(10, 10);
    pycamera.setTextSize(3);
    pycamera.setTextColor(pycamera.color565(255, 0, 0));
    pycamera.println("Print with \nframe?");
    pycamera.println(frame_info[frame]);
    delay(2000);
    Serial.println("SEL");
  }
  if (pycamera.justPressed(AWEXP_BUTTON_DOWN)){
    cat_reconnect();
    Serial.println("DOWN");
  }
}

void cat_reconnect() {
  Serial.println("Disconnecting..");
  pycamera.fillScreen(pycamera.color565(0, 0, 0));
  pycamera.setCursor(10, 10);
  pycamera.setTextSize(2);
  pycamera.setTextColor(pycamera.color565(0, 0, 255));
  pycamera.print("DISCONNECTING..");
  cat.disconnect();
  Serial.println("Disconnected.");
  delay(1000);
  pycamera.fillScreen(pycamera.color565(0, 0, 0));
  pycamera.setCursor(10, 10);
  pycamera.setTextSize(2);
  pycamera.setTextColor(pycamera.color565(0, 0, 255));
  pycamera.print("CONNECTING..");
  cat.resetNameArray();
  cat.addNameArray((char *)"MX06");
  if (cat.connect()) {
    Serial.println("Connected!");
    pycamera.fillScreen(pycamera.color565(0, 0, 0));
    pycamera.setCursor(10, 10);
    pycamera.setTextSize(2);
    pycamera.setTextColor(pycamera.color565(0, 0, 255));
    pycamera.print("CONNECTED!");
  }
    else {
    Serial.println("Could not find printer!");
    pycamera.fillScreen(pycamera.color565(0, 0, 0));
    pycamera.setCursor(10, 10);
    pycamera.setTextSize(2);
    pycamera.setTextColor(pycamera.color565(255, 0, 0));
    pycamera.print("Could not \nfind printer!\nResetting..");
    delay(200);
    resetFunc();
  }
  delay(500);
}
