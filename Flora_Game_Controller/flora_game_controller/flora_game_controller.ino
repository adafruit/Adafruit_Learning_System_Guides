/*
Example code for a Flora game controller with capacitive touch sensing! Full tutorial and video:
http://learn.adafruit.com/plush-game-controller/
Uses Modern Device's Capacitive Sensing library: https://github.com/moderndevice/CapSense
  Adafruit invests time and resources providing this open source code, 
  please support Adafruit and open-source hardware by purchasing 
  products from Adafruit!
  Written by Limor Fried & Becky Stern for Adafruit Industries.  
  BSD license, all text above must be included in any redistribution
  
*/
#include <CapPin.h>

CapPin cPin_10 = CapPin(10);    // read pin 10 (D10 on Flora) - connect to NES B
CapPin cPin_9  = CapPin(9);     // read pin 9 (D9 on Flora)   - connect to NES A
CapPin cPin_6  = CapPin(6);     // read pin 6 (D6 on Flora)   - connect to NES Start
CapPin cPin_12 = CapPin(12);    // read pin 12 (D12 on Flora) - connect to NES Select
CapPin cPin_1  = CapPin(1);     // read pin 1 (TX on Flora)   - connect to NES right
CapPin cPin_0  = CapPin(0);     // read pin 0 (RX on Flora)   - connect to NES up
CapPin cPin_2  = CapPin(2);     // read pin 2 (SDA on Flora)  - connect to NES left
CapPin cPin_3  = CapPin(3);     // read pin 3 (SCL on Flora)  - connect to NES down

CapPin pins[] = {cPin_10, cPin_9, cPin_6, cPin_12, cPin_1, cPin_0, cPin_2, cPin_3};
// check http://arduino.cc/en/Reference/KeyboardModifiers for more info on unique keys

// WASD D-pad, select = Return, start = Space, LeftButton = z, RightButton = x
//char Keys[] =   {  'x',    'z',    ' ',     KEY_RETURN,    'd',     'w',    'a',    's'};

// arrow D-pad, select = Return, start = Space, LeftButton = b, RightButton = a
char Keys[] =   {  'a',    'b',    ' ',     KEY_RETURN, KEY_RIGHT_ARROW, KEY_UP_ARROW, KEY_LEFT_ARROW, KEY_DOWN_ARROW};

boolean currentPressed[] = {false, false, false, false, false, false, false, false};

// Capactive touch threashhold, you might want to mess with this if you find its too
// sensitive or not sensitive enough
#define THRESH 500

float smoothed[8] = {0,0,0,0,0,0,0,0};

void setup()
{
  //while (!Serial)
  Serial.begin(115200);
  Serial.println("start");
  Keyboard.begin();
}


void loop()                    
{ 
  for (int i=0;i<8;i++) {
    delay(1);
    long total1 = 0;
    long start = millis();
    long total =  pins[i].readPin(2000);

    // check if we are sensing that a finger is touching the pad 
    // and that it wasnt already pressed
    if ((total > THRESH) && (! currentPressed[i])) {
      Serial.print("Key pressed #"); Serial.print(i);
      Serial.print(" ("); Serial.print(Keys[i]); Serial.println(")");
      currentPressed[i] = true;

      Keyboard.press(Keys[i]);
    } 
    else if ((total <= THRESH) && (currentPressed[i])) {
      // key was released (no touch, and it was pressed before)
      Serial.print("Key released #"); Serial.print(i);
      Serial.print(" ("); Serial.print(Keys[i]); Serial.println(")");
      currentPressed[i] = false;
      
      Keyboard.release(Keys[i]);
    }
    
/*
    // simple lowpass filter to take out some of the jitter
    // change parameter (0 is min, .99 is max) or eliminate to suit
    smoothed[i] = smooth(total, .8, smoothed[i]);   
    Serial.print(i); Serial.print(": ");
    Serial.print( millis() - start);      // time to execute in mS
    Serial.print("ms \t");
    Serial.print(total);                  // raw total
    Serial.print("\t->\t");
    Serial.println((int) smoothed[i]);       // smoothed
*/
    delay(5);
  }
}

// simple lowpass filter
// requires recycling the output in the "smoothedVal" param
int smooth(int data, float filterVal, float smoothedVal){

  if (filterVal > 1){      // check to make sure param's are within range
    filterVal = .999999;
  }
  else if (filterVal <= 0){
    filterVal = 0;
  }

  smoothedVal = (data * (1 - filterVal)) + (smoothedVal  *  filterVal);

  return (int)smoothedVal;
}
