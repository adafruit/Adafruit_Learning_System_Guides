#include <Adafruit_NeoPixel.h>
#include "Adafruit_FreeTouch.h"

// Create the neopixel strip with the built in definitions NUM_NEOPIXEL and PIN_NEOPIXEL
Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUM_NEOPIXEL, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);
// Create the touch pad
Adafruit_FreeTouch qt = Adafruit_FreeTouch(PIN_TOUCH, OVERSAMPLE_4, RESISTOR_50K, FREQ_MODE_NONE);

int16_t neo_brightness = 255; // initialize with highest brightness

void setup() {
  Serial.begin(9600);
  //while (!Serial);
  
  strip.begin();
  strip.setBrightness(neo_brightness);
  strip.show(); // Initialize all pixels to 'off'

  analogReadResolution(12);  // set highest resolution

  if (! qt.begin())  
    Serial.println("Failed to begin qt");
}

void loop() {
  uint16_t touch = qt.measure();
  Serial.print("Touch: "); Serial.println(touch);

  uint16_t potval = analogRead(PIN_POTENTIOMETER);
  Serial.print("Slider: ");
  Serial.println((float)potval / 4095);
  
  uint8_t wheelval = map(potval, 0, 4095, 0, 255);
  //Serial.print("Wheel: ");
  //Serial.println(wheelval);
  
  // If the pad is touched, turn off neopix!
  if (touch > 500) {
    Serial.println("Touched!");
    strip.setBrightness(0);
  } else {
    strip.setBrightness(255);
  }
  
  for(int i=0; i< strip.numPixels(); i++) {
    strip.setPixelColor(i, Wheel((wheelval+85) % 255));
  }
  
  strip.show();
  delay(10);
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
