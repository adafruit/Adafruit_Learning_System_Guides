#include <Adafruit_NeoPixel.h>

#define NEOPIXEL_PIN A3
#define NUM_PIXELS 2

#define SWITCHA_PIN A1
#define SWITCHB_PIN A2

Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUM_PIXELS, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  Serial.begin(115200);
  //while (!Serial);
  strip.begin();
  strip.setBrightness(25);
  strip.show(); // Initialize all pixels to 'off'
  pinMode(SWITCHA_PIN, INPUT_PULLUP);
  pinMode(SWITCHB_PIN, INPUT_PULLUP);
}

uint8_t j=0;
void loop() {
  for(int i=0; i< strip.numPixels(); i++) {
    strip.setPixelColor(i, Wheel(((i * 256 / strip.numPixels()) + j) & 255));
  }

  // turn off LED if not pressed!
  if (!digitalRead(SWITCHA_PIN)) {
    Serial.println("A");
    strip.setPixelColor(0, 0);
  }
  if (!digitalRead(SWITCHB_PIN)) {
    Serial.println("B");
    strip.setPixelColor(1, 0);
  }
  
  strip.show();

  j++; // go to next color
  delay(10);
}

// Slightly different, this makes the rainbow equally distributed throughout
void rainbowCycle(uint8_t wait) {

}

// Input a value 0 to 255 to get a color value.
// The colours are a transition r - g - b - back to r.
uint32_t Wheel(byte WheelPos) {
  if(WheelPos < 85) {
   return strip.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
  } else if(WheelPos < 170) {
   WheelPos -= 85;
   return strip.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  } else {
   WheelPos -= 170;
   return strip.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
}
