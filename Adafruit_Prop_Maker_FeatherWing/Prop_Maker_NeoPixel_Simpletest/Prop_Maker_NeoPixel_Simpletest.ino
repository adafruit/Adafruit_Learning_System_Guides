/*
* Adafruit Prop-Maker Featherwing
* NeoPixel Example
* 
* Rainbow example for 30-Pixel NeoPixel Strip
*/
#include <Adafruit_NeoPixel.h>

// NeoPixel strip length, in pixels
#define NUM_PIXELS 30

#if defined(__SAMD21G18A__) || defined(__AVR_ATmega32U4__)
  #define NEOPIXEL_PIN 5
  #define POWER_PIN    10
#elif defined(__AVR_ATmega328P__)
  #define NEOPIXEL_PIN 5
  #define POWER_PIN    10
#elif defined(NRF52)
  #define NEOPIXEL_PIN 27
  #define POWER_PIN    11
#elif defined(ESP8266)
  #define NEOPIXEL_PIN 2
  #define POWER_PIN    15
#elif defined(TEENSYDUINO)
  #define NEOPIXEL_PIN 8
  #define POWER_PIN    10
#elif defined(ESP32)
  #define NEOPIXEL_PIN 14
  #define POWER_PIN    33
#endif

// create a neopixel strip
Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUM_PIXELS, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);


void setup() {
  Serial.begin(115200);
  Serial.println("\nProp-Maker Wing: NeoPixel");

  // Set power pin to output
  pinMode(POWER_PIN, OUTPUT);
  // Disable the pin, we're not currently writing to the neopixels.
  digitalWrite(POWER_PIN, LOW);

  // This initializes the NeoPixel library.
  strip.begin();
}


uint32_t Wheel(byte WheelPos) {
  // Input a value 0 to 255 to get a color value.
  // The colours are a transition r - g - b - back to r.
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

void rainbow(uint8_t wait) {
  uint16_t i, j;

  for(j=0; j<256; j++) {
    for(i=0; i<strip.numPixels(); i++) {
      strip.setPixelColor(i, Wheel((i+j) & 255));
    }
    // turn on the Prop-Maker FeatherWing's power pin
    digitalWrite(POWER_PIN, HIGH);
    // write the pixel values
    strip.show();
    delay(wait);
  }
}

void loop()
{
  // cycle a the rainbow with a 20ms wait
  rainbow(20);
}
