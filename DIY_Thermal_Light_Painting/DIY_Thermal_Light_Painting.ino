/*************************************************** 
This is a library for the MLX90614 temperature sensor SPECIFICALLY
FOR USE WITH TINYWIREM ON TRINKET/GEMMA

Requires the latest TinyWireM with repeated-start support
https://github.com/adafruit/TinyWireM

NOT FOR REGULAR ARDUINOS! Use the regular Adafruit_MLX90614 for that

  Designed specifically to work with the MLX90614 sensors in the
  adafruit shop
  ----> https://www.adafruit.com/products/1748
  ----> https://www.adafruit.com/products/1749

  These sensors use I2C to communicate, 2 pins are required to  
  interface
  Adafruit invests time and resources providing this open source code, 
  please support Adafruit and open-source hardware by purchasing 
  products from Adafruit!

  Written by Limor Fried/Ladyada for Adafruit in any redistribution
 ****************************************************/

#include <TinyWireM.h>
#include <Adafruit_MiniMLX90614.h>
#include <Adafruit_NeoPixel.h>

// change these to adjust the range of temperatures you want to measure 
// (these are in Farenheit)
#define COLDTEMP 60
#define HOTTEMP  80


#define PIN 1
Adafruit_NeoPixel strip = Adafruit_NeoPixel(24, PIN, NEO_GRB + NEO_KHZ800);

Adafruit_MiniMLX90614 mlx = Adafruit_MiniMLX90614();

void setup() {
  mlx.begin();  
  strip.begin();
  strip.show(); // Initialize all pixels to 'off'
}

void loop() {
  uint8_t red, blue;
  float temp = mlx.readObjectTempF();

  if (temp < COLDTEMP) temp = COLDTEMP;
  if (temp > HOTTEMP) temp = HOTTEMP;

  // map temperature to red/blue color
  // hotter temp -> more red
  red = map(temp, COLDTEMP, HOTTEMP, 0, 255);  
  // hotter temp -> less blue
  blue = map(temp, COLDTEMP, HOTTEMP, 255, 0);  

  colorWipe(strip.Color(red, 0, blue), 0);
  
  delay(50); // can adjust this for faster/slower updates
}

// Fill the dots one after the other with a color
void colorWipe(uint32_t c, uint8_t wait) {
  for(uint16_t i=0; i<strip.numPixels(); i++) {
      strip.setPixelColor(i, c);
      strip.show();
      delay(wait);
  }
}
