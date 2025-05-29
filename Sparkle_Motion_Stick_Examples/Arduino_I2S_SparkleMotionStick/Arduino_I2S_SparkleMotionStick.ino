// SPDX-FileCopyrightText: 2025 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Arduino.h>
#include "ESP_I2S.h"

// I2S pin definitions for Sparklemotion
const uint8_t I2S_SCK = 14;  // BCLK
const uint8_t I2S_WS = 12;   // LRCLK
const uint8_t I2S_DIN = 13;  // DATA_IN

// Create I2S instance
I2SClass i2s;

void setup() {
  // Fast serial for plotting
  Serial.begin(500000);

  // Initialize I2S
  i2s.setPins(I2S_SCK, I2S_WS, -1, I2S_DIN);
  if (!i2s.begin(I2S_MODE_STD, 44100, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO, I2S_STD_SLOT_LEFT)) {
    Serial.println("Failed to initialize I2S bus!");
    return;
  }

  Serial.println("I2S Mic Plotter Ready");
}

void loop() {
  static uint32_t lastPlot = 0;

  // Get a sample
  int32_t sample = i2s.read();

  // Only plot every 1ms (1000 samples/sec is plenty for visualization)
  if (millis() - lastPlot >= 1) {
    if (sample >= 0) {  // Valid sample
      // Plot both raw and absolute values
      Serial.printf("%d,%d\n", (int16_t)sample, abs((int16_t)sample));
    }
    lastPlot = millis();
  }
}
