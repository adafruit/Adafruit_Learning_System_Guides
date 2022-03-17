#include "Adafruit_TestBed.h"

extern Adafruit_TestBed TB;

void setup() {
  Serial.begin(115200);
  //while (!Serial) { yield(); delay(10); }     // wait till serial port is opened
  delay(100);  // RP2040 delay is not a bad idea

  Serial.println("KB2040 self-tester!");

  TB.neopixelPin = 17;
  TB.neopixelNum = 1;
  
  TB.begin();
}

uint8_t x = 0;
  
void loop() {
  TB.setColor(TB.Wheel(x++));
  delay(10);
}
