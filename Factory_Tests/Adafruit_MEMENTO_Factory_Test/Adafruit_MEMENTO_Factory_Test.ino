// SPDX-FileCopyrightText: 2023 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Arduino.h>
#include "Adafruit_PyCamera.h"

Adafruit_PyCamera pycamera;
framesize_t validSizes[] = {FRAMESIZE_QQVGA, FRAMESIZE_QVGA, FRAMESIZE_HVGA, FRAMESIZE_VGA, FRAMESIZE_SVGA, FRAMESIZE_XGA, FRAMESIZE_HD, FRAMESIZE_SXGA, FRAMESIZE_UXGA, FRAMESIZE_QXGA, FRAMESIZE_QSXGA};

// A colection of possible ring light colors
uint32_t ringlightcolors_RGBW[] = {0x00000000, 0x00FF0000, 0x00FFFF00, 0x0000FF00, 0x0000FFFF, 0x000000FF, 0x00FF00FF, 0xFF000000};
uint8_t ringlight_i = 0;
uint8_t ringlightBrightness = 100;

#define IRQ 3


void setup() {
  Serial.begin(115200);
  // while (!Serial) yield();
  delay(100);

  if (! pycamera.begin()) {
    Serial.println("Failed to initialize pyCamera interface");
    while (1) yield();
  }
  Serial.println("pyCamera hardware initialized!");

  pinMode(IRQ, INPUT_PULLUP);
  attachInterrupt(IRQ, [] {
    Serial.println("IRQ!");
  }, FALLING);
}

void loop() {
  static uint8_t loopn=0;
  pycamera.setNeopixel(pycamera.Wheel(loopn));
  loopn += 8;
  
  pycamera.readButtons();
  //Serial.printf("Buttons: 0x%08X\n\r",  pycamera.readButtons());

  //pycamera.timestamp();
  pycamera.captureFrame();
  
  // once the frame is captured we can draw ontot he framebuffer
  if (pycamera.justPressed(AWEXP_SD_DET)) {

    Serial.println(F("SD Card removed"));
    pycamera.endSD();
    pycamera.fb->setCursor(0, 32);
    pycamera.fb->setTextSize(2);
    pycamera.fb->setTextColor(pycamera.color565(255, 0, 0));
    pycamera.fb->print(F("SD Card removed"));
    delay(200);
  }
  if (pycamera.justReleased(AWEXP_SD_DET)) {
    Serial.println(F("SD Card inserted!"));
    pycamera.initSD();
    pycamera.fb->setCursor(0, 32);
    pycamera.fb->setTextSize(2);
    pycamera.fb->setTextColor(pycamera.color565(255, 0, 0));
    pycamera.fb->print(F("SD Card inserted"));
    delay(200);
  }

  float A0_voltage = analogRead(A0) / 4096.0 * 3.3;
  if (loopn == 0) {
    Serial.printf("A0 = %0.1f V, Battery = %0.1f V\n\r", 
                  A0_voltage, pycamera.readBatteryVoltage());
  }
  pycamera.fb->setCursor(0,0);
  pycamera.fb->setTextSize(2);
  pycamera.fb->setTextColor(pycamera.color565(255, 255, 255));
  pycamera.fb->print("A0 = "); pycamera.fb->print(A0_voltage, 1);
  pycamera.fb->print("V\nBattery = "); pycamera.fb->print(pycamera.readBatteryVoltage(), 1); 
  pycamera.fb->print(" V");


  // print the camera frame size
  pycamera.fb->setCursor(0, 200);
  pycamera.fb->setTextSize(2);
  pycamera.fb->setTextColor(pycamera.color565(255, 255, 255));
  pycamera.fb->print("Size:");
  switch (pycamera.photoSize) {
    case FRAMESIZE_QQVGA:
      pycamera.fb->print("160x120");
      break;
    case FRAMESIZE_QVGA:
      pycamera.fb->print("320x240");
      break;
    case FRAMESIZE_HVGA:
      pycamera.fb->print("480x320");
      break;
    case FRAMESIZE_VGA:
      pycamera.fb->print("640x480");
      break;
    case FRAMESIZE_SVGA:
      pycamera.fb->print("800x600");
      break;
    case FRAMESIZE_XGA:
      pycamera.fb->print("1024x768");
      break;
    case FRAMESIZE_HD:
      pycamera.fb->print("1280x720");
      break;
    case FRAMESIZE_SXGA:
      pycamera.fb->print("1280x1024");
      break;
    case FRAMESIZE_UXGA:
      pycamera.fb->print("1600x1200");
      break;
    case FRAMESIZE_QXGA:
      pycamera.fb->print("2048x1536");
      break;
    case FRAMESIZE_QSXGA:
      pycamera.fb->print("2560x1920");
      break;
    default:
      pycamera.fb->print("Unknown");
      break;
  }

  float x_ms2, y_ms2, z_ms2;
  if (pycamera.readAccelData(&x_ms2, &y_ms2, &z_ms2)) {
    //Serial.printf("X=%0.2f, Y=%0.2f, Z=%0.2f\n\r", x_ms2, y_ms2, z_ms2);
    pycamera.fb->setCursor(0, 220);
    pycamera.fb->setTextSize(2);
    pycamera.fb->setTextColor(pycamera.color565(255, 255, 255));
    pycamera.fb->print("3D: "); pycamera.fb->print(x_ms2, 1);
    pycamera.fb->print(", "); pycamera.fb->print(y_ms2, 1);
    pycamera.fb->print(", "); pycamera.fb->print(z_ms2, 1);
  }
  
  pycamera.blitFrame();

  if (pycamera.justPressed(AWEXP_BUTTON_UP)) {
    Serial.println("Up!");
    for (int i = 0; i < sizeof(validSizes) / sizeof(framesize_t) - 1; ++i) {
        if (pycamera.photoSize == validSizes[i]) {
            pycamera.photoSize = validSizes[i + 1];
            break;
        }
    }
  }
  if (pycamera.justPressed(AWEXP_BUTTON_DOWN)) {
    Serial.println("Down!");
    for (int i = sizeof(validSizes) / sizeof(framesize_t) - 1; i > 0; --i) {
        if (pycamera.photoSize == validSizes[i]) {
            pycamera.photoSize = validSizes[i - 1];
            break;
        }
    }
  }

  if (pycamera.justPressed(AWEXP_BUTTON_RIGHT)) {
    pycamera.specialEffect = (pycamera.specialEffect + 1) % 7;
    pycamera.setSpecialEffect(pycamera.specialEffect);
    Serial.printf("set effect: %d\n\r", pycamera.specialEffect);
  }
  if (pycamera.justPressed(AWEXP_BUTTON_LEFT)) {
    pycamera.specialEffect = (pycamera.specialEffect + 6) % 7;
    pycamera.setSpecialEffect(pycamera.specialEffect);
    Serial.printf("set effect: %d\n\r", pycamera.specialEffect);
  }

  if (pycamera.justPressed(AWEXP_BUTTON_OK)) {
    // iterate through all the ring light colors
    ringlight_i = (ringlight_i + 1) % (sizeof(ringlightcolors_RGBW) / sizeof(uint32_t));
    pycamera.setRing(ringlightcolors_RGBW[ringlight_i]);
    Serial.printf("set ringlight: 0x%08X\n\r", (unsigned int)ringlightcolors_RGBW[ringlight_i]);
  }
  if (pycamera.justPressed(AWEXP_BUTTON_SEL)) {
    // iterate through brightness levels, incrementing 25 at a time
    if (ringlightBrightness >= 250) ringlightBrightness = 0;
    else ringlightBrightness += 50;
    pycamera.ring.setBrightness(ringlightBrightness);
    pycamera.setRing(ringlightcolors_RGBW[ringlight_i]);
    Serial.printf("set ringlight brightness: %d\n\r", ringlightBrightness);
  }

  if (pycamera.justPressed(SHUTTER_BUTTON)) {
    Serial.println("Snap!");
    if (pycamera.takePhoto("IMAGE", pycamera.photoSize)) {
      pycamera.fb->setCursor(120, 100);
      pycamera.fb->setTextSize(2);
      pycamera.fb->setTextColor(pycamera.color565(255, 255, 255));
      pycamera.fb->print("Snap!");
      pycamera.speaker_tone(100, 50);  // tone1 - B5
      //pycamera.blitFrame();
    }
  }

  delay(100); 
}
