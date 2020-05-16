// Read analog potentiometer on Circuit Playground Express or other board with changes
// Mike Barela for Adafruit Industries 9/2018 based on
// NeoPixel Ring simple sketch (c) 2013 Shae Erisson
// released under the GPLv3 license to match the rest of the AdaFruit NeoPixel library

#include <Adafruit_NeoPixel.h>
#ifdef __AVR__
  #include <avr/power.h>
#endif

// Which pin on the microcontroller board is connected to the NeoPixels?
#define PIN             8  // For Circuit Playground Express

// How many NeoPixels are attached to the board?
#define NUMPIXELS      10

// When we setup the NeoPixel library, we tell it how many pixels, and which pin to use to send signals.
// Note that for older NeoPixel strips you might need to change the third parameter--see the strandtest
// example for more information on possible values.
Adafruit_NeoPixel pixels = Adafruit_NeoPixel(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

int delayval = 500; // delay for half a second

void setup() {
  Serial.begin(9600);
  pixels.begin(); // This initializes the NeoPixel library.
}

void loop() {
   int i;              // loop variable
   int value;          // analog read of potentiometer
   int display_value;  // number of NeoPixels to display out of NUMPIXELS

   // Read PIN value and scale from 0 to NUMPIXELS -1
   value = analogRead(A1);
   Serial.print(value);
   Serial.print(", ");
   display_value = int(value  * NUMPIXELS / 1023);
   Serial.println(display_value);

   // For a set of NeoPixels the first NeoPixel is 0, second is 1, all the way up to the count of pixels minus one

   for(i=0; i<display_value; i++){

      // pixels.Color takes RGB values, from 0,0,0 up to 255,255,255
      pixels.setPixelColor(i, 0, 050, 0); // Moderately bright green color
   }
   for(i=display_value; i<NUMPIXELS; i++) {
      pixels.setPixelColor(i, 0, 0, 0);    // turn off all pixels after value displayed
   }

   pixels.show(); // This sends the updated pixel color to the hardware.

   delay(delayval); // Delay for a period of time (in milliseconds).
}
