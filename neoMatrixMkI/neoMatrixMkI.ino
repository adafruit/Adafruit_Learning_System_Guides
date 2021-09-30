# SPDX-FileCopyrightText: 2017 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

#include "Arduino.h"
#include "Keypad.h"
#include "Neosegment.h"
#include <stdlib.h>

#define SERIAL_BAUD 115200
#define nDigits 6 // number of digits in display
#define NEOSEGPIN 12
#define LEDbrightness 255  // 0 to 255
/*
Segment mapping
             5
            ___
        4  |   |  6
           |___|
           | 3 |
        0  |___|  2

             1
*/
int buttonPin = 11; //pushbutton
int ledPin = 13;      // select the pin for the LED
int knobUpperPin = A3;    // input pin for a potentiometer
int knobLowerPin = A2;    // input pin for a potentiometer
int knobUpper = 0;  // variable to store the value coming from the sensor
int knobLower = 0;  // variable to store the value coming from the sensor

int buttonState;
int lastButtonState = LOW;
long lastDebounceTime = 0;
long debounceDelay = 50;


//initialize the neosegment object
Neosegment neosegment(nDigits, NEOSEGPIN, LEDbrightness);
uint16_t i, j;

//set up the keypad
const byte ROWS = 4; //four rows
const byte COLS = 3; //three columns
char keys[ROWS][COLS] = {
  {'1','2','3'},
  {'4','5','6'},
  {'7','8','9'},
  {'*','0','#'}
};
byte rowPins[ROWS] = {5, 6, 7, 8}; //connect to the row pinouts of the keypad
byte colPins[COLS] = {2, 3, 4}; //connect to the column pinouts of the keypad

//initialize the keypad object
Keypad keypad = Keypad( makeKeymap(keys), rowPins, colPins, ROWS, COLS );

//use to set digit cursor position
int neoCounter = 0;

//gamma correction table
const uint8_t PROGMEM gamma8[] = {
    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,
    1,  1,  1,  1,  1,  1,  1,  1,  1,  2,  2,  2,  2,  2,  2,  2,
    2,  3,  3,  3,  3,  3,  3,  3,  4,  4,  4,  4,  4,  5,  5,  5,
    5,  6,  6,  6,  6,  7,  7,  7,  7,  8,  8,  8,  9,  9,  9, 10,
   10, 10, 11, 11, 11, 12, 12, 13, 13, 13, 14, 14, 15, 15, 16, 16,
   17, 17, 18, 18, 19, 19, 20, 20, 21, 21, 22, 22, 23, 24, 24, 25,
   25, 26, 27, 27, 28, 29, 29, 30, 31, 32, 32, 33, 34, 35, 35, 36,
   37, 38, 39, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 50,
   51, 52, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 66, 67, 68,
   69, 70, 72, 73, 74, 75, 77, 78, 79, 81, 82, 83, 85, 86, 87, 89,
   90, 92, 93, 95, 96, 98, 99,101,102,104,105,107,109,110,112,114,
  115,117,119,120,122,124,126,127,129,131,133,135,137,138,140,142,
  144,146,148,150,152,154,156,158,160,162,164,167,169,171,173,175,
  177,180,182,184,186,189,191,193,196,198,200,203,205,208,210,213,
  215,218,220,223,225,228,231,233,236,239,241,244,247,249,252,255 };

void setup(){
  Serial.begin(SERIAL_BAUD);
  pinMode(ledPin, OUTPUT);
  pinMode(buttonPin, INPUT_PULLUP);
  digitalWrite(ledPin, HIGH);  //turn on the LED

  neosegment.begin();
  neosegment.clearAll();
  for(int i = 0; i < 6; i++){ //turn on green lines, top row, L to R
    neosegment.setSegment(i, 5, 0, 40, 0); //the '3' segment is middle dash
    tone(A1, 330, 100);
    delay(50);
  }
  neosegment.setSegment(5, 6, 0, 40, 0);
  tone(A1, 330, 100);
  delay(50);
  neosegment.setSegment(5, 2, 0, 40, 0);
  tone(A1, 330, 100);
  delay(50);
  neosegment.clearAll();

  for(int i = 5; i > -1; i--){ //turn on green lines, bottom row, R to L
    neosegment.setSegment(i, 1, 0, 40, 0); //the '3' segment is middle dash
    tone(A1, 330, 100);
    delay(50);
  }
  neosegment.setSegment(0, 0, 0, 40, 0);
  tone(A1, 330, 100);
  delay(50);
  neosegment.clearAll();

  for(int i = 0; i < 6; i++){ //turn on green lines, middle row, L to R
    neosegment.setSegment(i, 3, 0, 40, 0); //the '3' segment is middle dash
    tone(A1, 440, 100);
    delay(100);
  }
}

void loop(){
  //read button
  int buttonReading = digitalRead(buttonPin);
  if (buttonReading != lastButtonState) {
    lastDebounceTime = millis();
  }
  if ((millis() - lastDebounceTime) > debounceDelay){
    buttonState = buttonReading;
  }
  Serial.println(buttonState);
  if(buttonState){
    digitalWrite(ledPin, LOW);
  }
  else{
    digitalWrite(ledPin, HIGH);
  }
  lastButtonState = buttonReading;

  //read knobs
  knobUpper = analogRead(knobUpperPin); //used for hue
  knobLower = analogRead(knobLowerPin); //used for value
  //map knob range
  int knobUpperMapped = map(knobUpper, 0, 700, 360, 0);
  int knobLowerMapped = map(knobLower, 0, 700, 700, 0);
  //constrain knob range
  knobUpperMapped = constrain(knobUpperMapped, 0, 360);
  knobLowerMapped = constrain(knobLowerMapped, 0, 700);
  //map to hue range
  //int knobHue = map(knobUpperMapped, 0, 255, 0, 360);
  //knobHue = constrain(knobHue, 0, 360);
  float knobHue = ((float)knobUpperMapped);
  //map to value range
  float knobValue = ((float)knobLowerMapped / 700);

  float r, g, b;
  float h = knobHue;
  float s = 1.0;
  float v = knobValue;

  HSVtoRGB(&r, &g, &b, h, s, v); //convert HSV to RGB
  uint8_t r_byte = (int)(r * 255);
  uint8_t g_byte = (int)(g * 255);
  uint8_t b_byte = (int)(b * 255);

  //apply gamma correction table values
  r_byte = pgm_read_byte(&gamma8[r_byte]);
  g_byte = pgm_read_byte(&gamma8[g_byte]);
  b_byte = pgm_read_byte(&gamma8[b_byte]);

  char key = keypad.getKey();

  if (key != NO_KEY){ // a key has been pressed
    Serial.print("key: ");
    Serial.println(key);
    int neoKey = key - '0'; //terminate w zero so don't get ASCII code

    //enter with '#'
    if(key == '#'){
      neosegment.clearAll();
      delay(35);
      neosegment.setSegment(5, 2, 40, 40, 40);
      neosegment.setSegment(5, 6, 40, 40, 40);
      delay(35);
      tone(A1, 660, 100);
      for(int i = 5; i > -1; i--){ //from right to left
        neosegment.setSegment(i, 1, 40, 40, 40);
        neosegment.setSegment(i, 5, 40, 40, 40);
        delay(35);
        tone(A1, 660, 100);
      }
      neosegment.setSegment(0, 0, 40, 40, 40);
      neosegment.setSegment(0, 4, 40, 40, 40);
      tone(A1, 660, 100);
      neoCounter = 0;

      //letters that appear in upper: A, E, F, H, I, J, L, P, S, U
      //letters that appear in lower: b, c, d, g, n, o, q, r, t
      delay(1000);
      neosegment.clearAll();
      delay(1000);
      neosegment.setDigit(5, 'a', 23, 0, 12);
      tone(A1, 220, 100);
      delay(500);
      neosegment.setDigit(4, 'a', 23, 0, 12);
      neosegment.setDigit(5, 'c', 23, 0, 12);
      tone(A1, 220, 100);
      delay(500);
      neosegment.setDigit(3, 'a', 23, 0, 12);
      neosegment.setDigit(4, 'c', 23, 0, 12);
      neosegment.setDigit(5, 'o', 23, 0, 12);
      tone(A1, 220, 100);
      delay(500);
      neosegment.setDigit(2, 'a', 23, 0, 12);
      neosegment.setDigit(3, 'c', 23, 0, 12);
      neosegment.setDigit(4, 'o', 23, 0, 12);
      neosegment.setDigit(5, 'r', 23, 0, 12);
      tone(A1, 220, 100);
      delay(500);
      neosegment.setDigit(1, 'a', 23, 0, 12);
      neosegment.setDigit(2, 'c', 23, 0, 12);
      neosegment.setDigit(3, 'o', 23, 0, 12);
      neosegment.setDigit(4, 'r', 23, 0, 12);
      neosegment.setDigit(5, 'n', 23, 0, 12);
      tone(A1, 220, 100);
      delay(2000);

      for(int x=0; x<50; x++){
          neosegment.setDigit(2, 'c', 0, x, 0);
          delay(15);
      }
      for(int x=0; x<50; x++){
          neosegment.setDigit(4, 'r', x, x, 0);
          delay(15);
      }
      for(int x=0; x<50; x++){
          neosegment.setDigit(3, 'o', 0, x, x);
          delay(15);
      }
      for(int x=0; x<50; x++){
          neosegment.setDigit(5, 'n', x, 0, 0);
          delay(15);
      }
      for(int x=0; x<50; x++){
          neosegment.setDigit(1, 'A', x/2, x/2, x/2);
          delay(15);
      }
      delay(500);
      neosegment.setDigit(1, 'a', 23, 0, 12);
      neosegment.setDigit(2, 'c', 23, 0, 12);
      neosegment.setDigit(3, 'o', 23, 0, 12);
      neosegment.setDigit(4, 'r', 23, 0, 12);
      neosegment.setDigit(5, 'n', 23, 0, 12);
      tone(A1, 220, 100);
      delay(1700);
      neosegment.clearAll();
      delay(500);
      for(int i = 0; i < 6; i++){ //turn on green lines, middle row, L to R
        neosegment.setSegment(i, 3, 0, 40, 0); //the '3' segment is middle dash
        //tone(A1, 440, 100);
        delay(100);
      }
    }

    //special function with '*'
    else if(key == '*'){ //show HUE value
      neosegment.clearAll();

      neosegment.setDigit(0, 'h', 0, 30, 0);
      neosegment.setDigit(1, 'u', 0, 30, 0);
      neosegment.setDigit(2, 'e', 0, 30, 0);

      int ones = (((int)knobHue) % 10);
      int tens = ((((int)knobHue)/10) % 10);
      int hundreds = ((((int)knobHue)/100) % 10);

      neosegment.setDigit(5, ones, r_byte, g_byte, b_byte);
      neosegment.setDigit(4, tens, r_byte, g_byte, b_byte);
      neosegment.setDigit(3, hundreds, r_byte, g_byte, b_byte);
      Serial.print("red byte: ");
      Serial.println(r_byte);

      tone(A1, ((knobHue+31)), 200);
      neoCounter = 0;
    }

    //number keys
    else{ // display numbers
        if(neoCounter%6 == 0){ //clear when screen gets full
            neosegment.clearAll();
        }
        int neoPosition = (neoCounter % 6); //use modulo operation to loop
        //through the positions
        int BLUE = knobUpperMapped;
        neosegment.setDigit(neoPosition, neoKey, r_byte, g_byte, b_byte);
        neoCounter++;
        tone(A1, ((knobUpperMapped * neoKey) + 31), 170); //+31 deals with
        //the 0 key
    }
  }
}

//function to convert Hue, Saturation, Value to Red, Green, Blue
void HSVtoRGB(float *r, float *g, float *b, float h, float s, float v){
//HSV is in HUE: degrees, SATURATION: 0 to 1.0, VALUE: 0 to 1.0
  int i;
  float f, p, q, t;
  if( s == 0 ) {
    // achromatic (grey)
    *r = *g = *b = v;
    return;
  }
  h /= 60;      // sector 0 to 5
  i = floor( h );
  f = h - i;      // factorial part of h
  p = v * ( 1 - s );
  q = v * ( 1 - s * f );
  t = v * ( 1 - s * ( 1 - f ) );
  switch( i ) {
    case 0:
      *r = v;
      *g = t;
      *b = p;
      break;
    case 1:
      *r = q;
      *g = v;
      *b = p;
      break;
    case 2:
      *r = p;
      *g = v;
      *b = t;
      break;
    case 3:
      *r = p;
      *g = q;
      *b = v;
      break;
    case 4:
      *r = t;
      *g = p;
      *b = v;
      break;
    default:    // case 5:
      *r = v;
      *g = p;
      *b = q;
      break;
  }
}
