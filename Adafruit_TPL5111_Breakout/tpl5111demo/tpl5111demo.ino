// SPDX-FileCopyrightText: 2017 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_NeoPixel.h>

#if defined(ESP8266)
  #define NEOPIX   4
  #define DONEPIN  5
#else
  #include <Adafruit_SleepyDog.h>
  #define NEOPIX   13
  #define DONEPIN  12
#endif

Adafruit_NeoPixel strip = Adafruit_NeoPixel(12, NEOPIX, NEO_GRB + NEO_KHZ800);


void setup() {
  pinMode(DONEPIN, OUTPUT);
  digitalWrite(DONEPIN, LOW);
  Serial.begin(115200);
  Serial.println("Light up NeoPixels!");

  strip.begin();
  strip.show(); // Initialize all pixels to 'off'
  strip.setBrightness(20);
}

void loop() {
  rainbowCycle(5);

  Serial.println("NeoPixels done, sleeping");

  // toggle DONE so TPL knows to cut power!
  while (1) {
    digitalWrite(DONEPIN, HIGH);
    delay(1);
    digitalWrite(DONEPIN, LOW);
    delay(1);
  }
  
  Serial.println("Awake!");
}

// Slightly different, this makes the rainbow equally distributed throughout
void rainbowCycle(uint8_t wait) {
  uint16_t i, j;

  for(j=0; j<256*1; j++) { // 5 cycles of all colors on wheel
    for(i=0; i< strip.numPixels(); i++) {
      strip.setPixelColor(i, Wheel(((i * 256 / strip.numPixels()) + j) & 255));
    }
    strip.show();
    delay(wait);
  }
}


// Input a value 0 to 255 to get a color value.
// The colours are a transition r - g - b - back to r.
uint32_t Wheel(byte WheelPos) {
  WheelPos = 255 - WheelPos;
  if(WheelPos < 85) {
    return strip.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  }
  if(WheelPos < 170) {
    WheelPos -= 85;
    return strip.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
  WheelPos -= 170;
  return strip.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
}