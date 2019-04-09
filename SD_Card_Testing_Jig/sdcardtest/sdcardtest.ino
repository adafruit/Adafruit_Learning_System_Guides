/*
  SD card breakout tester!
  Uses fat16lib's fantastic FAT library
  tests:
  1. CD pin works (goes low when card inserted)
  2. 3.3V LDO output is in proper range
  3. Can communicate with card
 */

#include <SD.h>

Sd2Card card;

#define CD 15 // A1 (D15) -> CardDetect
#define LDO 0 // analog 0

void setup()   {                
  // initialize the digital pin as an output:
  Serial.begin(9600);
  
  digitalWrite(CD, HIGH); // pull up on CD
}


void loop()                     
{
  Serial.println("waiting for SD card detect");
 
  while (digitalRead(CD)) {
   Serial.print('.');
   delay(100);
  }
   
  Serial.println("Detected Card!");
 
  // first check 3.3V regulator
  int a = analogRead(LDO);
  if ((a > 710) || (a < 650)) {
    // LDO not in the right range
    Serial.println(a);
    return;
  }
  
  Serial.println("3.3V LDO ok");
  
  // try to talk to the card
  uint8_t r = card.init(1);
  if (!r) {
    // failed to talk to SD card :(
    Serial.println(r, DEC);
    return;
  }
  
  Serial.println("Card interface ok");
  
  // beep to indicate all is good
  tone(9, 4000, 500);
  
  delay(1000);
 
}
