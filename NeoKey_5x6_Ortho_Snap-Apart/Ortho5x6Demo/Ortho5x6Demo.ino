#include <Adafruit_NeoPixel.h>
#include "Adafruit_Keypad.h"

#define ROWS 5 // rows
#define COLS 6 // columns

#define NEOPIXEL_PIN 7
#define NUM_PIXELS (ROWS * COLS)

Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUM_PIXELS, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);


//define the symbols on the buttons of the keypads
char keys[ROWS][COLS] = {
  {'1','2','3','4','5','6'},
  {'7','8','9','A','B','C'},
  {'D','E','F','G','H','I'},
  {'J','K','L','M','N','O'},
  {'P','Q','R','S','T','U'}
};

uint8_t rowPins[ROWS] = {6, 29, 28, 27, 26}; //connect to the row pinouts of the keypad
uint8_t colPins[COLS] = {13, 12, 11, 10, 9, 8}; //connect to the column pinouts of the keypad

//initialize an instance of class NewKeypad
Adafruit_Keypad customKeypad = Adafruit_Keypad( makeKeymap(keys), rowPins, colPins, ROWS, COLS);

bool lit[ROWS*COLS] = {0};

void setup() {
  Serial.begin(115200);
  //while (!Serial);
  Serial.println("Ortho 5x6 keypad demo");
  strip.begin();
  strip.setBrightness(40);
  strip.show(); // Initialize all pixels to 'off'

  customKeypad.begin();
  for (int i=0; i<ROWS*COLS; i++) {
    lit[i] = false;
  }
}

uint8_t j=0; // color ticker

void loop() {
  //Serial.println("Test NeoPixels");
  customKeypad.tick();
  
  while(customKeypad.available()){
    keypadEvent e = customKeypad.read();
    Serial.print((char)e.bit.KEY);
    if (e.bit.EVENT == KEY_JUST_PRESSED) {
      Serial.println(" pressed");
      uint8_t row = e.bit.ROW;
      uint8_t col = e.bit.COL;
      Serial.print("Row: "); Serial.print(row);
      Serial.print(" col: "); Serial.print(col);
      Serial.print(" -> ");
      uint16_t keynum;
      if (row % 2 == 0) { // even row
        keynum = row * COLS + col;
      } else { // odd row the neopixels go BACKWARDS!
        keynum = row * COLS + (5 - col);
      }
      Serial.println(keynum);
      lit[keynum] = !lit[keynum]; // invert neopixel status
    }
    else if(e.bit.EVENT == KEY_JUST_RELEASED) {
      Serial.println(" released");
    }
  }

  for(int i=0; i< strip.numPixels(); i++) {
    if (lit[i]) {
      strip.setPixelColor(i, Wheel(((i * 256 / strip.numPixels()) + j) & 255));
    } else {
      strip.setPixelColor(i, 0);
    }
  }
  strip.show();
  j++;
  
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
