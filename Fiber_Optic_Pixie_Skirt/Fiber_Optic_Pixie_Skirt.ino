#include <Adafruit_Pixie.h>
#include "SoftwareSerial.h"
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_LSM303DLH_Mag.h>
#include <Adafruit_LSM303_Accel.h>

int ledMode = 0;  //FIRST ACTIVE MODE

#define NUMPIXIES 5 // Number of Pixies in the fiber optics
#define PIXIEPIN 6


SoftwareSerial pixieSerial(-1, PIXIEPIN);

Adafruit_Pixie strip = Adafruit_Pixie(NUMPIXIES, &pixieSerial);

Adafruit_LSM303_Accel_Unified accel = Adafruit_LSM303_Accel_Unified(54321);
Adafruit_LSM303DLH_Mag_Unified mag = Adafruit_LSM303DLH_Mag_Unified(12345);

const float twirl = 7; // accelerometer threshold for toggling modes -- change this number to change sensitivity
long twirlStart = 0;
long twirlTime = 2000;


// Set your colors for RandomFlash mode here.
// just add new {nnn, nnn, nnn}, lines. They will be picked out randomly
//                                  R   G   B
uint8_t myFavoriteColors[][3] = {{255,   0,   0},   // red
                                 {255,   150,   0},   // orange 
                                 {251, 255, 0},   // yellow
                               };
// don't edit the line below
#define FAVCOLORS sizeof(myFavoriteColors) / 3

void setup() 
{
  Serial.begin(9600);
  // Initialize the sensors
  accel.begin();
  mag.begin();
   
  pixieSerial.begin(115200);
  strip.show(); // Initialize all pixels to 'off
}


#define NUM_MODES 4  //change this if you add more modes

//------------------MAIN LOOP------------------
void loop() {
    switch (ledMode) {
       case 0: colorWipe(strip.Color(200, 20, 20), 20); break;   //  red
       case 1: colorWipe(strip.Color(20, 200, 50), 20); break;   //   yellow
       case 2: colorWipe(strip.Color(200, 0, 200), 20); break;  // purple
       case 3: rainbowfill(); break;              //rainbow
       case 4: flashRandom(5, 4); break;      // flash      
    
    }  

   // Now read the accelerometer to control the motion.
   sensors_event_t event; 
   accel.getEvent(&event);
 
   // Check for mode change commands
   CheckFortwirls(event);

  }

// monitor orientation for mode-change 'gestures'
void CheckFortwirls(sensors_event_t event)
{
   if (event.acceleration.x > twirl)
   {
     if (millis() - twirlStart > twirlTime)
     {
    Serial.println("Twirl!");
    colorWipe(strip.Color(0, 0, 0), 10);
    ledMode++;
    if (ledMode > NUM_MODES){
    ledMode=0; }
     }
   }
   else if (event.acceleration.x < -(twirl + 1))
   {
     if (millis() - twirlStart > twirlTime)
     {
       Serial.println("Twirl Back!");
    colorWipe(strip.Color(0, 0, 0), 10);
    ledMode--;
    if (ledMode < 0){
    ledMode=NUM_MODES;     
     }
   }
   else // no nods in progress
   {
     twirlStart = millis(); // reset timer
   }
}
}

void flashRandom(int wait, uint8_t howmany) {

  for(uint16_t i=0; i<howmany; i++) {
    // pick a random favorite color!
    int c = random(FAVCOLORS);
    int red = myFavoriteColors[c][0];
    int green = myFavoriteColors[c][1];
    int blue = myFavoriteColors[c][2]; 

    // get a random pixel from the list
    int j = random(strip.numPixels());
    //Serial.print("Lighting up "); Serial.println(j); 
    
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

}

// Fill the dots one after the other with a color
void colorWipe(uint32_t c, uint8_t wait) {
  for(uint16_t i=0; i<strip.numPixels(); i++) {
    strip.setPixelColor(i, c);
    strip.show();
    delay(wait);
  }
}

// Fill the dots one after the other with a color
void rainbowfill() {
  strip.setPixelColor(0, strip.Color(255, 0, 0));
  strip.setPixelColor(1, strip.Color(200, 100, 0));
  strip.setPixelColor(2, strip.Color(0, 255, 0));
  strip.setPixelColor(3, strip.Color(50, 50, 200));
  strip.setPixelColor(4, strip.Color(255, 0, 255));
  strip.show();
  delay(100);
}
