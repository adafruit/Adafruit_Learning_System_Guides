// SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*
 * HyperHDR AWA Protocol Implementation for SAMD21 (Pixel Trinkey)
 * 
 * Based on the HyperSerialESP32 AWA protocol
 * Compatible with SAMD21-based boards like the Adafruit Pixel Trinkey
 */

#include <Adafruit_NeoPixel.h>

// Configuration - ADJUST THESE FOR YOUR SETUP
#define LED_PIN      2           // Data pin for NeoPixels (Pin 1 on Pixel Trinkey)
#define LED_COUNT    204         // Number of LEDs (must match HyperHDR config)
#define BRIGHTNESS   180         // Max brightness (0-255) - reduced to prevent washout
#define SERIAL_BAUD  2000000     // Serial baud rate (2Mbps for HyperHDR)

// Color correction - adjust these to fine-tune color balance
// Lower values = less of that color, higher = more
// Default is 255 (no correction), try 200-240 for less washed out colors
#define COLOR_CORRECT_RED    255  // Reduce if reds are too bright
#define COLOR_CORRECT_GREEN  230  // Green often needs reduction
#define COLOR_CORRECT_BLUE   240  // Reduce if blues are too bright

// LED type configuration
// For RGB strips (WS2812B): use NEO_GRB
// For RGBW strips (SK6812): use NEO_GRBW and uncomment USE_RGBW below
#define LED_TYPE     NEO_GRBW
#define USE_RGBW  // Uncomment ONLY for RGBW strips

// Protocol constants
#define MAX_BUFFER   4096        // Maximum buffer size
#define MAX_LEDS     1024        // Maximum supported LEDs

// Create NeoPixel object
Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, LED_TYPE + NEO_KHZ800);

// Gamma correction lookup table (2.2 gamma curve)
#ifdef USE_GAMMA_CORRECTION
const uint8_t PROGMEM gamma8[] = {
    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,
    1,  1,  1,  1,  1,  1,  1,  1,  1,  2,  2,  2,  2,  2,  2,  2,
    2,  3,  3,  3,  3,  3,  3,  3,  4,  4,  4,  4,  4,  5,  5,  5,
    5,  6,  6,  6,  6,  7,  7,  7,  7,  8,  8,  8,  9,  9,  9, 10,
   10, 10, 11, 11, 11, 12, 12, 13, 13, 13, 14, 14, 15, 15, 16, 16,
   17, 17, 18, 18, 19, 19, 20, 20, 21, 21, 22, 22, 23, 24, 24, 25,
   25, 26, 27, 27, 28, 29, 29, 30, 31, 32, 32, 33, 34, 35, 35, 36,
   37, 38, 39, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 50,
   51, 52, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 66, 67, 68,
   69, 70, 72, 73, 74, 75, 77, 78, 79, 81, 82, 83, 85, 86, 87, 89,
   90, 92, 93, 95, 96, 98, 99,101,102,104,105,107,109,110,112,114,
  115,117,119,120,122,124,126,127,129,131,133,135,137,138,140,142,
  144,146,148,150,152,154,156,158,160,162,164,167,169,171,173,175,
  177,180,182,184,186,189,191,193,196,198,200,203,205,208,210,213,
  215,218,220,223,225,228,231,233,236,239,241,244,247,249,252,255
};
#endif

// Apply color corrections and gamma
uint8_t applyCorrection(uint8_t value, uint16_t correction) {
  #ifdef USE_GAMMA_CORRECTION
    // Apply gamma first, then color correction
    uint8_t gammaValue = pgm_read_byte(&gamma8[value]);
    return (gammaValue * correction) / 255;
  #else
    // Just apply color correction
    return (value * correction) / 255;
  #endif
}

// AWA Protocol states (matching ESP32 implementation)
enum class AwaProtocol {
  HEADER_A,
  HEADER_w,
  HEADER_a,
  HEADER_HI,
  HEADER_LO,
  HEADER_CRC,
  VERSION2_GAIN,
  VERSION2_RED,
  VERSION2_GREEN,
  VERSION2_BLUE,
  RED,
  GREEN,
  BLUE,
  FLETCHER1,
  FLETCHER2,
  FLETCHER_EXT
};

// Frame state tracking
struct FrameState {
  AwaProtocol state = AwaProtocol::HEADER_A;
  bool protocolVersion2 = false;
  uint8_t crc = 0;
  uint16_t count = 0;
  uint16_t currentLed = 0;
  uint16_t fletcher1 = 0;
  uint16_t fletcher2 = 0;
  uint16_t fletcherExt = 0;
  uint8_t position = 0;
  
  // Current pixel color being assembled
  uint8_t r = 0, g = 0, b = 0;
  #ifdef USE_RGBW
    uint8_t w = 0;
  #endif
  
  // Calibration data for V2 protocol
  struct {
    uint8_t gain = 0xFF;
    uint8_t red = 0xB0;
    uint8_t green = 0xB0;
    uint8_t blue = 0x70;
  } calibration;
  
  void init(uint8_t hiCount) {
    currentLed = 0;
    count = hiCount * 0x100;
    crc = hiCount;
    fletcher1 = 0;
    fletcher2 = 0;
    fletcherExt = 0;
    position = 0;
  }
  
  void computeCRC(uint8_t loCount) {
    count += loCount;
    crc = crc ^ loCount ^ 0x55;
  }
  
  void addFletcher(uint8_t input) {
    fletcher1 = (fletcher1 + input) % 255;
    fletcher2 = (fletcher2 + fletcher1) % 255;
    fletcherExt = (fletcherExt + (input ^ (position++))) % 255;
  }
  
  uint16_t getFletcher1() { return fletcher1; }
  uint16_t getFletcher2() { return fletcher2; }
  uint16_t getFletcherExt() { 
    return (fletcherExt != 0x41) ? fletcherExt : 0xaa; 
  }
};

// Global state
FrameState frameState;
uint32_t lastDataTime = 0;
uint32_t frameCount = 0;
uint32_t errorCount = 0;
uint32_t lastStatsTime = 0;
uint16_t ledCount = 0;

// Statistics
struct Statistics {
  uint32_t totalFrames = 0;
  uint32_t goodFrames = 0;
  uint32_t showFrames = 0;
  uint32_t lastPrint = 0;
} stats;

void setup() {
  // Initialize serial
  Serial.begin(SERIAL_BAUD);
  Serial.setTimeout(50);
  
  // Initialize NeoPixels  
  strip.begin();
  strip.setBrightness(BRIGHTNESS);
  strip.clear();
  strip.show();
  
  // Show startup animation
  startupAnimation();
  
  lastDataTime = millis();
  lastStatsTime = millis();
}

void loop() {
  // Process all available serial data
  while (Serial.available() > 0) {
    uint8_t input = Serial.read();
    lastDataTime = millis();
    processAwaByte(input);
  }
  
  // Timeout - clear display if no data for 5 seconds
  if ((millis() - lastDataTime) > 5000) {
    if (strip.getBrightness() > 0) {
      strip.clear();
      strip.show();
    }
  }
  
  // Print statistics every 5 seconds if no data
  if ((millis() - stats.lastPrint) > 5000 && (millis() - lastDataTime) > 1000) {
    printStatistics();
  }
}

void processAwaByte(uint8_t input) {
  switch (frameState.state) {
    case AwaProtocol::HEADER_A:
      frameState.protocolVersion2 = false;
      if (input == 'A') {
        frameState.state = AwaProtocol::HEADER_w;
      }
      break;
      
    case AwaProtocol::HEADER_w:
      if (input == 'w') {
        frameState.state = AwaProtocol::HEADER_a;
      } else {
        frameState.state = AwaProtocol::HEADER_A;
      }
      break;
      
    case AwaProtocol::HEADER_a:
      if (input == 'a') {
        frameState.state = AwaProtocol::HEADER_HI;
        frameState.protocolVersion2 = false;
      } else if (input == 'A') {
        frameState.state = AwaProtocol::HEADER_HI;
        frameState.protocolVersion2 = true;
      } else {
        frameState.state = AwaProtocol::HEADER_A;
      }
      break;
      
    case AwaProtocol::HEADER_HI:
      stats.totalFrames++;
      frameState.init(input);
      frameState.state = AwaProtocol::HEADER_LO;
      break;
      
    case AwaProtocol::HEADER_LO:
      frameState.computeCRC(input);
      frameState.state = AwaProtocol::HEADER_CRC;
      break;
      
    case AwaProtocol::HEADER_CRC:
      if (frameState.crc == input) {
        ledCount = frameState.count + 1;
        
        // Sanity check
        if (ledCount > MAX_LEDS) {
          frameState.state = AwaProtocol::HEADER_A;
          errorCount++;
        } else {
          // Limit to actual strip size
          if (ledCount > LED_COUNT) {
            ledCount = LED_COUNT;
          }
          frameState.state = AwaProtocol::RED;
        }
      } else if (frameState.count == 0x2aa2 && (input == 0x15 || input == 0x35)) {
        // Statistics request
        printStatistics();
        if (input == 0x15) {
          Serial.println("\r\nWelcome!\r\nAwa driver SAMD21 v1.0");
        }
        frameState.state = AwaProtocol::HEADER_A;
      } else {
        frameState.state = AwaProtocol::HEADER_A;
        errorCount++;
      }
      break;
      
    case AwaProtocol::RED:
      frameState.r = input;
      frameState.addFletcher(input);
      frameState.state = AwaProtocol::GREEN;
      break;
      
    case AwaProtocol::GREEN:
      frameState.g = input;
      frameState.addFletcher(input);
      frameState.state = AwaProtocol::BLUE;
      break;
      
    case AwaProtocol::BLUE:
      frameState.b = input;
      frameState.addFletcher(input);
      
      // Apply color to LED
      if (frameState.currentLed < LED_COUNT && frameState.currentLed < ledCount) {
        // Apply color corrections to reduce washout
        uint8_t correctedR = applyCorrection(frameState.r, COLOR_CORRECT_RED);
        uint8_t correctedG = applyCorrection(frameState.g, COLOR_CORRECT_GREEN);
        uint8_t correctedB = applyCorrection(frameState.b, COLOR_CORRECT_BLUE);
        
        #ifdef USE_RGBW
          // For RGBW, calculate white channel (simplified version)
          uint8_t w = min(correctedR, min(correctedG, correctedB));
          correctedR -= w;
          correctedG -= w;
          correctedB -= w;
          strip.setPixelColor(frameState.currentLed, strip.Color(correctedR, correctedG, correctedB, w));
        #else
          // For RGB strips
          strip.setPixelColor(frameState.currentLed, strip.Color(correctedR, correctedG, correctedB));
        #endif
      }
      
      frameState.currentLed++;
      
      // Check if we have more LEDs to process
      if (frameState.currentLed < ledCount) {
        frameState.state = AwaProtocol::RED;
      } else {
        // All LEDs processed, move to checksum or calibration
        if (frameState.protocolVersion2) {
          frameState.state = AwaProtocol::VERSION2_GAIN;
        } else {
          frameState.state = AwaProtocol::FLETCHER1;
        }
      }
      break;
      
    case AwaProtocol::VERSION2_GAIN:
      frameState.calibration.gain = input;
      frameState.addFletcher(input);
      frameState.state = AwaProtocol::VERSION2_RED;
      break;
      
    case AwaProtocol::VERSION2_RED:
      frameState.calibration.red = input;
      frameState.addFletcher(input);
      frameState.state = AwaProtocol::VERSION2_GREEN;
      break;
      
    case AwaProtocol::VERSION2_GREEN:
      frameState.calibration.green = input;
      frameState.addFletcher(input);
      frameState.state = AwaProtocol::VERSION2_BLUE;
      break;
      
    case AwaProtocol::VERSION2_BLUE:
      frameState.calibration.blue = input;
      frameState.addFletcher(input);
      frameState.state = AwaProtocol::FLETCHER1;
      break;
      
    case AwaProtocol::FLETCHER1:
      if (input != frameState.getFletcher1()) {
        frameState.state = AwaProtocol::HEADER_A;
        errorCount++;
      } else {
        frameState.state = AwaProtocol::FLETCHER2;
      }
      break;
      
    case AwaProtocol::FLETCHER2:
      if (input != frameState.getFletcher2()) {
        frameState.state = AwaProtocol::HEADER_A;
        errorCount++;
      } else {
        frameState.state = AwaProtocol::FLETCHER_EXT;
      }
      break;
      
    case AwaProtocol::FLETCHER_EXT:
      if (input == frameState.getFletcherExt()) {
        // Frame is valid! Show it
        strip.show();
        stats.goodFrames++;
        stats.showFrames++;
        frameCount++;
      } else {
        errorCount++;
      }
      frameState.state = AwaProtocol::HEADER_A;
      break;
  }
}

void printStatistics() {
  char output[128];
  snprintf(output, sizeof(output), 
    "HyperHDR frames: %lu (FPS), total: %lu, good: %lu, errors: %lu\r\n",
    stats.showFrames, stats.totalFrames, stats.goodFrames, errorCount);
  Serial.print(output);
  
  // Reset stats
  stats.totalFrames = 0;
  stats.goodFrames = 0;
  stats.showFrames = 0;
  errorCount = 0;
  stats.lastPrint = millis();
}

void startupAnimation() {
  // Quick color cycle to show we're ready
  uint32_t colors[] = {
    strip.Color(255, 0, 0),    // Red
    strip.Color(0, 255, 0),    // Green
    strip.Color(0, 0, 255),    // Blue
    strip.Color(255, 255, 255) // White
  };
  
  for (int c = 0; c < 4; c++) {
    for (int i = 0; i < min((int)strip.numPixels(), 8); i++) {
      strip.setPixelColor(i, colors[c]);
    }
    strip.show();
    delay(200);
  }
  
  // Clear
  strip.clear();
  strip.show();
}
