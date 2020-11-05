#if 0 // Change to 1 to enable this code (must enable ONE user*.cpp only!)

#include <Adafruit_NeoPixel.h>

#define LED_PIN    8
#define LED_COUNT  4
Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

void user_setup(void) {
  strip.begin();           // INITIALIZE NeoPixel strip object (REQUIRED)
  strip.show();            // Turn OFF all pixels ASAP
  strip.setBrightness(50); // Set BRIGHTNESS to about 1/5 (max = 255)
}

long firstPixelHue = 0;

// Called once after the processing of the configuration file. This allows
// user configuration to also be done based on the config file.
#define ARDUINOJSON_ENABLE_COMMENTS 1	// ARDUINOJSON_ENABLE_COMMENTS must be set to 1 before including the library.
										// The same value of ARDUINOJSON_ENABLE_COMMENTS must be set in each compilation unit.
#include <ArduinoJson.h>				// JSON config file functions
void user_setup(StaticJsonDocument<2048> &doc) {
}

void user_loop(void) {
  for(int i=0; i<strip.numPixels(); i++) { // For each pixel in strip...
    // Offset pixel hue by an amount to make one full revolution of the
    // color wheel (range of 65536) along the length of the strip
    // (strip.numPixels() steps):
    int pixelHue = firstPixelHue + (i * 65536L / strip.numPixels());
    // strip.ColorHSV() can take 1 or 3 arguments: a hue (0 to 65535) or
    // optionally add saturation and value (brightness) (each 0 to 255).
    // Here we're using just the single-argument hue variant. The result
    // is passed through strip.gamma32() to provide 'truer' colors
    // before assigning to each pixel:
    strip.setPixelColor(i, strip.gamma32(strip.ColorHSV(pixelHue)));
  }
  strip.show(); // Update strip with new contents
  firstPixelHue += 256;
}

#endif // 0
