#include <Adafruit_NeoPixel.h>
#define PIN 1
#define NUM_LEDS 3

Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUM_LEDS, PIN, NEO_GRB + NEO_KHZ800);

//                          R   G   B
uint8_t myColors[][5] = {
                         {30, 144, 255},   // dodger blue
                         {232, 100, 255},  // purple
                         {204, 0, 204},    //  
                         {200, 200, 20},   // yellow 
                         {30, 200, 200},   // blue
                         };
                               
// don't edit the line below
#define FAVCOLORS sizeof(myColors) / 5

void setup() {
  strip.begin();
  strip.setBrightness(20);
  strip.show(); // Initialize all pixels to 'off'
}

void loop() {
  flashRandom(10, 1);  // first number is 'wait' delay, shorter num == shorter twinkle
  flashRandom(10, 3);  // second number is how many neopixels to simultaneously light up
  flashRandom(10, 2);
}

void flashRandom(int wait, uint8_t howmany) {
 
  for(uint16_t i=0; i<howmany; i++) {
    // pick a random favorite color!
    int c = random(FAVCOLORS);
    int red = myColors[c][0];
    int green = myColors[c][1];
    int blue = myColors[c][2]; 
 
    // get a random pixel from the list
    int j = random(strip.numPixels());
    
    // now we will 'fade' it in 5 steps
    for (int x=0; x < 5; x++) {
      int r = red * (x+1); r /= 5;
      int g = green * (x+1); g /= 5;
      int b = blue * (x+1); b /= 5;
      
      strip.setPixelColor(j, strip.Color(r, g, b));
      strip.show();
      delay(wait);
    }
    // & fade out in 5 steps
    for (int x=5; x >= 0; x--) {
      int r = red * x; r /= 5;
      int g = green * x; g /= 5;
      int b = blue * x; b /= 5;
      
      strip.setPixelColor(j, strip.Color(r, g, b));
      strip.show();
      delay(wait);
    }
  }
  // LEDs will be off when done (they are faded to 0)
}
