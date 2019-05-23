// Adafruit 32u4 Feather Color Sensing Holiday Lights
// See the full guide at:
//   https://learn.adafruit.com/feather-holiday-lights/overview
// Author: Tony DiCola
// Released under a MIT license:
//   https://opensource.org/licenses/MIT
#include "Adafruit_NeoPixel.h"
#include "Adafruit_TCS34725.h"
#include "Adafruit_VCNL4000.h"
#include "Adafruit_VCNL4010.h"
#include "Wire.h"


#define PIXEL_COUNT 60    // The number of NeoPixels connected to the board.

#define PIXEL_PIN   6     // The pin connected to the input of the NeoPixels.

#define PIXEL_TYPE  NEO_GRB + NEO_KHZ800  // The type of NeoPixels, see the NeoPixel
                                          // strandtest example for more options.

#define ANIMATION_PERIOD_MS  300  // The amount of time (in milliseconds) that each
                                  // animation frame lasts.  Decrease this to speed
                                  // up the animation, and increase it to slow it down.

#define TCS_LED_PIN 5     // The digital pin connected to the TCS color sensor LED pin.
                          // Will control turning the sensor's LED on and off.

#define PROXIMITY_THRESHOLD  10000   // The threshold value to consider an object near
                                     // and attempt to read its color.  This is a good
                                     // default but you can modify it to fine tune your
                                     // setup (use the serial monitor to review what
                                     // proximity values you observe).


// Create NeoPixel strip from above parameters.
Adafruit_NeoPixel strip = Adafruit_NeoPixel(PIXEL_COUNT, PIXEL_PIN, PIXEL_TYPE);

// Create TCS color sensor object.
Adafruit_TCS34725 tcs = Adafruit_TCS34725(TCS34725_INTEGRATIONTIME_50MS, TCS34725_GAIN_4X);

// Create VCNL sensor object (defined in this sketch).
// If you're using a VCNL4010 sensor use this line:
Adafruit_VCNL4010 vcnl = Adafruit_VCNL4010();
// However if you're using a VCNL4000 sensor comment the above line and uncomment this one:
//Adafruit_VCNL4000 vcnl = Adafruit_VCNL4000();

// Build a gamma correction table for better color accuracy.
// Borrowed from TCS library examples.
uint8_t gammatable[256];

// Global variable to hold the current pixel color.  Starts out red but will be
// changed by color sensor.
int r = 255;
int g = 0;
int b = 0;

  
void setup() {
  Serial.begin(115200);
  Serial.println(F("Adafruit 32u4 Feather Color Sensing Holiday Lights"));

  // Setup TCS sensor LED pin as an output and turn off the LED.
  pinMode(TCS_LED_PIN, OUTPUT);
  digitalWrite(TCS_LED_PIN, LOW);

  // Initialize NeoPixels.
  strip.begin();
  strip.show();

  // Initialize TCS sensor library.
  if (tcs.begin()) {
    Serial.println("Found TCS sensor");
  }
  else {
    Serial.println("No TCS34725 found ... check your connections");
    while (1);
  }

  // Initialize VCNL sensor library.
  if (vcnl.begin()) {
    Serial.println("Found VNCL sensor");
  }
  else {
    Serial.println("No VNCL found ... check your connections");
    while (1);
  }

  // Generate gamma correction table.
  // Taken from TCS color sensor examples.
  for (int i=0; i<256; i++) {
    float x = i;
    x /= 255;
    x = pow(x, 2.5);
    x *= 255;
    gammatable[i] = x;      
  }
}

void loop() {
  // Animate pixels.
  animatePixels(strip, r, g, b, 300);
  
  // Grab VCNL proximity measurement.
  uint16_t proximity = vcnl.readProximity();
  Serial.print("\t\tProximity = ");   
  Serial.println(proximity);

  // Take a TCS color sensor reading if an object is near (proximity measurement is larger than threshold).
  if (proximity > PROXIMITY_THRESHOLD) {
    // First turn on the LED and wait a bit for a good reading.
    digitalWrite(TCS_LED_PIN, HIGH);
    delay(500);
    // Grab TCS color sensor reading.
    uint16_t raw_r, raw_g, raw_b, raw_c;
    tcs.getRawData(&raw_r, &raw_g, &raw_b, &raw_c);
    // Convert raw values to a value within 0...255, then run it through gamma correction curve.
    r = gammatable[(int)(((float)raw_r / (float)raw_c)*255.0)];
    g = gammatable[(int)(((float)raw_g / (float)raw_c)*255.0)];
    b = gammatable[(int)(((float)raw_b / (float)raw_c)*255.0)];
    // Print color value.
    Serial.print("R = ");
    Serial.print(r);
    Serial.print(" G = ");
    Serial.print(g);
    Serial.print(" B = ");
    Serial.println(b);
    // Turn off the LED.
    digitalWrite(TCS_LED_PIN, LOW);
    // Pause a bit to prevent constantly reading the color.
    delay(1000);
  }

  // Small delay before looping.
  delay(50);
}

void animatePixels(Adafruit_NeoPixel& strip, uint8_t r, uint8_t g, uint8_t b, int periodMS) {
  // Animate the NeoPixels with a simple theater chase/marquee animation.
  // Must provide a NeoPixel object, a color, and a period (in milliseconds) that controls how
  // long an animation frame will last.
  // First determine if it's an odd or even period.
  int mode = millis()/periodMS % 2;
  // Now light all the pixels and set odd and even pixels to different colors.
  // By alternating the odd/even pixel colors they'll appear to march along the strip.
  for (int i = 0; i < strip.numPixels(); ++i) {
    if (i%2 == mode) {
      strip.setPixelColor(i, r, g, b);  // Full bright color.
    }
    else {
      strip.setPixelColor(i, r/4, g/4, b/4);  // Quarter intensity color.
    }
  }
  strip.show();
}
