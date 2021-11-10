// SPDX-FileCopyrightText: 2014 Becky Stern for Adafruit Industries
// SPDX-FileCopyrightText: 2018 Mikey Sklar for Adafruit Industries
//
// SPDX-License-Identifier: MIT
//
int brightness = 0;    // how bright the LED is
int fadeAmount = 5;    // how many points to fade the LED by
int counter = 0;       // counter to keep track of cycles

// the setup routine runs once when you press reset:
void setup()  { 
  // declare pins to be an outputs:
  pinMode(0, OUTPUT);
  pinMode(2, OUTPUT);
} 

// the loop routine runs over and over again forever:
void loop()  { 
  // set the brightness of the analog-connected LEDs:
  analogWrite(0, brightness);
  
  // change the brightness for next time through the loop:
  brightness = brightness + fadeAmount;

  // reverse the direction of the fading at the ends of the fade: 
  if (brightness == 0 || brightness == 255) {
    fadeAmount = -fadeAmount; 
    counter++;
  }     
  // wait for 15 milliseconds to see the dimming effect    
  delay(15); 

// turns on the other LEDs every four times through the fade by 
// checking the modulo of the counter.
// the modulo function gives you the remainder of 
// the division of two numbers:
  if (counter % 4 == 0) {
    digitalWrite(2, HIGH);
  } else {
   digitalWrite(2, LOW);
  }  
}
