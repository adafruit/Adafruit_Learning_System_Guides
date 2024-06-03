// SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_NeoPixel.h>

#define NUMPIXELS 64
Adafruit_NeoPixel neostrip(NUMPIXELS, PIN_DATA, NEO_GRB + NEO_KHZ800);

char colorBuffer[9]; // Buffer to hold the incoming color data (0x000000)
int bufferIndex = 0; // Index for the buffer

void setup() {
  Serial.begin(115200);

  neostrip.begin();
  neostrip.setBrightness(25);
  neostrip.show();
  memset(colorBuffer, 0, sizeof(colorBuffer)); // Clear the buffer
}

void loop() {
  // Check if data is available on the serial port
  while (Serial.available() > 0) {
    char incomingByte = Serial.read();
    
    // Check if the incoming byte is part of the color data
    if (isxdigit(incomingByte) || incomingByte == 'x') {
      colorBuffer[bufferIndex++] = incomingByte; // Add the byte to the buffer
    }
    
    // If the buffer is full, process the color data
    if (bufferIndex == 8) {
      colorBuffer[8] = '\0'; // Null-terminate the string
      
      // Convert the hex string to a 32-bit integer
      uint32_t color = strtoul(colorBuffer, NULL, 16);
      
      // Extract RGB values from the color
      uint8_t r = (color >> 16) & 0xFF;
      uint8_t g = (color >> 8) & 0xFF;
      uint8_t b = color & 0xFF;
      
      // Set the NeoPixels to the received color
      for (int i = 0; i < NUMPIXELS; i++) {
        neostrip.setPixelColor(i, neostrip.Color(r, g, b));
      }
      neostrip.show();
      
      // Clear the buffer and reset the bufferIndex
      memset(colorBuffer, 0, sizeof(colorBuffer));
      bufferIndex = 0;
    }
  }
}
