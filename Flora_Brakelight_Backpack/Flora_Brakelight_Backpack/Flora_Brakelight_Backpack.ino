#include <Wire.h>
#include <Adafruit_LSM303.h>
#include <SPI.h>
#include <Adafruit_WS2801.h>

Adafruit_LSM303 lsm;

#define BRAKETHRESHOLD        350
#define BRAKETIMETHRESHOLD    200

int dataPin  = 2;    // Yellow wire on Adafruit Pixels
int clockPin = 3;    // Green wire on Adafruit Pixels
const int cPin = 11;
const int dPin = 6;

// Set the first variable to the NUMBER of pixels. 32 = 32 pixels in a row
// The LED strips are 32 LEDs per meter but you can extend/cut the strip
Adafruit_WS2801 strip = Adafruit_WS2801(36,dataPin,clockPin);

int start = 0;

int prevX = 0;
int currentX = 0;

int cState = 0;
int dState = 0;

long brakeTime = 0;

void setup() 
{
  Serial.begin(9600);
  
  // Start up the LED strip
  strip.begin();
  // Update the strip, to start they are all 'off'
  strip.show();
  // Try to initialise and warn if we couldn't detect the chip
  if (!lsm.begin())
  {
    Serial.println("Oops ... unable to initialize the LSM303. Check your wiring!");
    while (1);
  }
  pinMode(cPin, INPUT); 
  pinMode(dPin, INPUT);
}

void loop() 
{
  check_switches();      // when we check the switches we'll get the current state
  
  lsm.read();
  currentX = abs(lsm.accelData.x);
  
  if (start == 0){
    prevX = currentX;
    start = 1;
  }
  
  int i = currentX - prevX;

  if (abs(i) > BRAKETHRESHOLD) {
    brakeTime = millis();
    int strikes = 0;
    while ((abs(i) > BRAKETHRESHOLD) && (strikes < 3)) {
      if (abs(i) < BRAKETHRESHOLD) {
        strikes = strikes + 1; 
      }
      lsm.read();
      currentX = abs(lsm.accelData.x);
      i = currentX - prevX;
      
      if ((millis() - brakeTime) > BRAKETIMETHRESHOLD) {
        brakeLights(Color(255,0,0),250);
        while (abs(i) > BRAKETHRESHOLD) {
          lsm.read();
          currentX = abs(lsm.accelData.x);
          i = currentX - prevX;
          Serial.println(i);
          delay(100);
        }
        hideAll();
        brakeTime = millis();
        i = 0;
                  lsm.read();
          currentX = abs(lsm.accelData.x);
      }
    }
  }

  prevX = currentX;
  delay(200);
}

void check_switches()
{
  cState = digitalRead(cPin);
  dState = digitalRead(dPin);

  if (cState == HIGH) {     
    // left blinker
     Serial.println("left blink on"); 
    hideAll();
    leftTurn(Color(255,63,0),250);
    delay(300);
    Serial.println("left blink off");
    hideAll();
    delay(300);  
  }
  
  if (dState == HIGH) {     
    // right blinker
    Serial.println("right blink on"); 
    hideAll();
    rightTurn(Color(255,63,0),250);
    delay(300);
    Serial.println("right blink off");
    hideAll();
    delay(300);  
  }
}

void leftTurn(uint32_t c,uint8_t wait){
 innerLeftBottom(c);
 innerLeftTop(c);
   strip.show(); 
 delay(wait);
 hideAll();
 outerLeftTop(c);
 outerLeftBottom(c);
   strip.show(); 
 delay(wait);
 hideAll();
}

void rightTurn(uint32_t c,uint8_t wait){
 innerRightBottom(c);
 innerRightTop(c);
   strip.show(); 
 delay(wait);
 hideAll();
 outerRightTop(c);
 outerRightBottom(c);
   strip.show(); 
 delay(wait);
 hideAll();
}

void brakeLights(uint32_t c, uint8_t wait){
  innerRightBottom(c);
 innerRightTop(c);
 innerLeftBottom(c);
 innerLeftTop(c);
   strip.show(); 
 delay(wait);
 hideAll();
 outerLeftTop(c);
 outerLeftBottom(c);
 outerRightTop(c);
 outerRightBottom(c);
   strip.show(); 
 delay(wait);
 hideAll();
}


/* Helper functions */

//Input a value 0 to 384 to get a color value.
//The colours are a transition r - g - b - back to r

void outerRightBottom(uint32_t c){
  for (int i=0; i < 5; i++) {
    strip.setPixelColor(i, c);
  }
}
void outerRightTop(uint32_t c){
  for (int i=5; i < 10; i++) {
    strip.setPixelColor(i, c);
  }
}
void innerRightTop(uint32_t c){
  for (int i=10; i < 14; i++) {
    strip.setPixelColor(i, c);
  }
}
void innerRightBottom(uint32_t c){
  for (int i=14; i < 18; i++) {
    strip.setPixelColor(i, c);
  }
}

void innerLeftBottom(uint32_t c){
  for (int i=18; i < 22; i++) {
    strip.setPixelColor(i, c);
    strip.show();
  }
}

void innerLeftTop(uint32_t c){
  for (int i=22; i < 26; i++) {
    strip.setPixelColor(i, c);
  }
}

void outerLeftTop(uint32_t c){
  for (int i=26; i < 31; i++) {
    strip.setPixelColor(i, c);
  }
}
void outerLeftBottom(uint32_t c){
  for (int i=31; i < 36; i++) {
    strip.setPixelColor(i, c);
  }
}

void hideAll(){
  for(int i = 0; i > strip.numPixels();i++){
   strip.setPixelColor(i,Color(0,0,0));
  }
  strip.show();
}

// Create a 24 bit color value from R,G,B
uint32_t Color(byte r, byte g, byte b)
{
  uint32_t c;
  c = r;
  c <<= 8;
  c |= g;
  c <<= 8;
  c |= b;
  return c;
}
