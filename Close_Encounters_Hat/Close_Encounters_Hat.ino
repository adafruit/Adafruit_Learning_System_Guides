// SPDX-FileCopyrightText: 2017 Becky Stern for Adafruit Industries
// SPDX-FileCopyrightText: 2017 Anne Barela for Adafruit Industries
// SPDX-FileCopyrightText: 2017 T Main for Adafruit Industries
// SPDX-FileCopyrightText: 2017 Leslie Birch for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/* 
Close Encounters hat with 10 neopixels by Leslie Birch for Adafruit Industries.
Notes play with each corresponding light. 
Based on code by Becky Stern, Anne Barela and T Main for Adafruit Industries
http://learn.adafruit.com/adafruit-trinket-modded-stuffed-animal/animal-sounds
*/

const int speaker = 0;      // the number of the speaker
#define PHOTOCELL 1         // cDS photocell on A1

// this section is Close Encounters Sounds
#define toneC    1046.50
#define toneG    1567.98
#define tonec     2093.00
#define toned     2349.32
#define tonee     2637.02
#define tonep       0 

#define darkness_min 512 // analog 0-1024 0-512 (light, 513-1023 dark)

long vel = 20000;

// This section is NeoPixel Variables

#include <Adafruit_NeoPixel.h>

#define PIN 1

// Parameter 1 = number of pixels in strip
// Parameter 2 = pin number (most are valid)
// Parameter 3 = pixel type flags, add together as needed:
//   NEO_KHZ800  800 KHz bitstream (most NeoPixel products w/WS2812 LEDs)
//   NEO_KHZ400  400 KHz (classic 'v1' (not v2) FLORA pixels, WS2811 drivers)
//   NEO_GRB     Pixels are wired for GRB bitstream (most NeoPixel products)
//   NEO_RGB     Pixels are wired for RGB bitstream (v1 FLORA pixels, not v2)
//Adafruit_NeoPixel strip = Adafruit_NeoPixel(10, 1, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel strip = Adafruit_NeoPixel(10, 1);


void setup() {
  pinMode(speaker, OUTPUT);

  Serial.println("setup");
  
  //This is for Neopixel Setup
  strip.begin();
  strip.show(); // Initialize all pixels to 'off'
}

void loop() 
{ 
    // turn lights and audio on when dark
    // less than 50% light on analog pin
    if ( analogRead(PHOTOCELL) > darkness_min ) { 

        alien(); // Close Encounters Loop

     }
    
  }
  
// the sound producing function

void beep (unsigned char speakerPin, int frequencyInHertz, long timeInMilliseconds)
{  // http://web.media.mit.edu/~leah/LilyPad/07_sound_code.html
int x;  
long delayAmount = (long)(1000000/frequencyInHertz);
long loopTime = (long)((timeInMilliseconds*1000)/(delayAmount*2));
for (x=0;x<loopTime;x++)  
{ 
digitalWrite(speakerPin,HIGH);
delayMicroseconds(delayAmount);
digitalWrite(speakerPin,LOW);
delayMicroseconds(delayAmount);
} 
}

// Generate the Close Encounters LEDs 
void alien() {
   
  strip.setBrightness(64);
  strip.setPixelColor(8, 255, 255, 0); //yellow front
  strip.setPixelColor(3, 255, 255, 0); //yellow back
  strip.show();
  beep(speaker,toned,1000);
  delay(25);
  strip.setPixelColor(8, 0, 0, 0); //clear front
  strip.setPixelColor(3, 0, 0, 0); //clear back
  strip.show();
  delay(25);
  strip.setPixelColor(7, 255, 0, 255); //pink front
  strip.setPixelColor(2, 255, 0, 255); //pink back
  strip.show();
  beep(speaker,tonee,1000);
  delay(25);
  strip.setPixelColor(7, 0, 0, 0); //clear front
  strip.setPixelColor(2, 0, 0, 0); //clear back
  strip.show();
  delay(25);
  strip.setPixelColor(4, 128, 255, 0); //green front
  strip.setPixelColor(9, 128, 255, 0); //green back
  strip.show();
  beep(speaker,tonec,1000);
  delay(25);
  strip.setPixelColor(4, 0, 0, 0); //clear front
  strip.setPixelColor(9, 0, 0, 0); //clear back
  strip.show();
  delay(25);
  strip.setPixelColor(5, 0, 0, 255); //blue front
  strip.setPixelColor(0, 0, 0, 255); //blue back
  strip.show();
  beep(speaker,toneC,1000);
  delay(75);
  strip.setPixelColor(5, 0, 0, 0); //clear front
  strip.setPixelColor(0, 0, 0, 0); //clear back
  strip.show();
  delay(100);
  strip.setPixelColor(6, 255, 0, 0); //red front
  strip.setPixelColor(1, 255, 0, 0); //red back
  strip.show();
  beep(speaker,toneG,1000);
  delay(100);
  strip.setPixelColor(6, 0, 0, 0); //clear front
  strip.setPixelColor(1, 0, 0, 0); //clear back
  strip.show();
  delay(100);
 
}
