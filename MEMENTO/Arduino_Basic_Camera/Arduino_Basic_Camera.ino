#include "Adafruit_PyCamera.h"
#include <Arduino.h>

Adafruit_PyCamera pycamera;
framesize_t validSizes[] = {FRAMESIZE_QQVGA, FRAMESIZE_QVGA, FRAMESIZE_HVGA,
                            FRAMESIZE_VGA,   FRAMESIZE_SVGA, FRAMESIZE_XGA,
                            FRAMESIZE_HD,    FRAMESIZE_SXGA, FRAMESIZE_UXGA,
                            FRAMESIZE_QXGA,  FRAMESIZE_QSXGA};

void setup() {
  Serial.begin(115200);
  // while (!Serial) yield();
  // delay(1000);

  // Serial.setDebugOutput(true);
  Serial.println("PyCamera Basic Example");
  if (!pycamera.begin()) {
    Serial.println("Failed to initialize PyCamera interface");
    while (1)
      yield();
  }
  Serial.println("PyCamera hardware initialized!");

  pycamera.photoSize = FRAMESIZE_SVGA;
}

void loop() {

  pycamera.readButtons();
  // Serial.printf("Buttons: 0x%08X\n\r",  pycamera.readButtons());

  // pycamera.timestamp();
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

  pycamera.blitFrame();

  if (pycamera.justPressed(SHUTTER_BUTTON)) {
    Serial.println("Snap!");
    if (pycamera.takePhoto("IMAGE", pycamera.photoSize)) {
      pycamera.fb->setCursor(120, 100);
      pycamera.fb->setTextSize(2);
      pycamera.fb->setTextColor(pycamera.color565(255, 255, 255));
      pycamera.fb->print("Snap!");
      pycamera.speaker_tone(100, 50); // tone1 - B5
      // pycamera.blitFrame();
    }
  }

  delay(100);
}
