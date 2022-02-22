// SPDX-FileCopyrightText: 2018 Alex Alves for Adafruit Industries
//
// SPDX-License-Identifier: BSD

//Written by Alex Alves for Adafruit Industries.
//Adafruit invests time and resources providing this open source code,
//please support Adafruit and open-source hardware by purchasing products
//from Adafruit!
//BSD license, all text above must be included in any redistribution.

#include <SoftwareSerial.h>
#include "Adafruit_Soundboard.h"
#include <Adafruit_NeoPixel.h>
#include <Wire.h>
#include <SPI.h>
#include <Adafruit_LSM9DS0.h>
#include <Adafruit_Sensor.h>  // not used in this demo but required!


#define HARDWARETEST 0 // plays sound and test neopixles at start up
#define PRINTDATA 0   // prints out sensor data

////////////    SENSOR SETTINGS     ////////////////////
// these settings may have to be changed and calibrated
// orinetation 
#define VERTICALVAL 11000  // decrease for more senstive
#define HORIZVAL 6000     //  increase for more senstive 

// flick detection
#define FLICKTRIG 17000 // lower = more senstive

// Wrist twist 
#define WRISTDIFF 13000 // lower = more senstive
#define WRISTGY  25000 // higher = more senstive



// Sound
// Choose any two pins that can be used with SoftwareSerial to RX & TX
#define SFX_TX 11
#define SFX_RX 10

// Connect to the RST pin on the Sound Board
#define SFX_RST 18
#define SFX_ACT 23

// we'll be using software serial
SoftwareSerial ss = SoftwareSerial(SFX_TX, SFX_RX);
Adafruit_Soundboard sfx = Adafruit_Soundboard(&ss, NULL, SFX_RST);


// NeoPixels
#define PIXELPIN 9
#define NUM_LEDS 7
#define BRIGHTNESS 255 // max 255
Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUM_LEDS, PIXELPIN, NEO_GRBW + NEO_KHZ800);


// IMU
Adafruit_LSM9DS0 lsm = Adafruit_LSM9DS0();


enum orientation {
  horiz,
  vertical,
  mid
};
// Global state variables
bool wristTwist = false;
bool flick = false;
orientation orient = horiz;

/////////////////////////////////////////////////////////////////////////////////////////////
// setup
/////////////////////////////////////////////////////////////////////////////////////////////

void setup() {
  Serial.begin(115200);
  connectSensor();
  setupSensor();
  setupNeoPixel();
  pinMode(SFX_ACT, INPUT);

  // softwareserial at 9600 baud
  ss.begin(9600);
  // can also do Serial1.begin(9600)

  while (!sfx.reset()) {
    Serial.println("Sound Board not found");
    delay(1000);
  }
  if (HARDWARETEST) {
    if (! sfx.playTrack("BLAST01 WAV") ) {
      Serial.println("Failed to play track1");
    }
    waitSFXFinish();
  }

}


void loop() {
  static bool spellCasting = false;
  static long unsigned int sampleTrig = 0; // trig for when to sample sensors

  // Take new sample
  if (millis() > sampleTrig) {
    reciveData1();
    sampleTrig = millis() + 10;
  }

  // conect basic actions together to make difrent spells
  if (!spellCasting) {
    // trigger spell 1
    if (wristTwist && (orient == vertical) ) {
      spellCasting = true;
      sfx.playTrack("LIGHT01 WAV");
      setColor(strip.Color(255, 255, 255, 255));
      delay(5);
    }

    else if (wristTwist && (orient == horiz) ) {
      spellCasting = true;
      sfx.playTrack("WIND01  WAV");  //temp
      setColor(strip.Color(150, 255, 100));;
      delay(5);
    }

    else if (flick && (orient == horiz)) {
      spellCasting = true;
      sfx.playTrack("FIRE01  WAV");
      setColor(strip.Color(255, 50, 20));
      delay(5);
    }

    else if (flick && (orient == vertical)) {
      spellCasting = true;
      sfx.playTrack("THUNDE~1WAV");
      setColor(strip.Color(0, 0, 255, 100));
      delay(5);
    }
  }

  // spell is being cast
  else {
    // spell just finished
    if (!sfxActive()) {
      spellCasting = false;
      setColor(strip.Color(0, 0, 0));
    }
  }

}

/************************ MENU HELPERS ***************************/

// Is a sound playing
bool sfxActive() {
  return (! digitalRead(SFX_ACT));
}

// block wait till sound is finished
void waitSFXFinish() {
  delay(5);
  while (sfxActive()) {
    delay(1);
  }
  delay(5);
}


/************************ MENU HELPERS ***************************/

// set colors in sequence
void colorWipe(uint32_t c, uint8_t wait) {
  for (uint16_t i = 0; i < strip.numPixels(); i++) {
    strip.setPixelColor(i, c);
    strip.show();
    delay(wait);
  }
}

// set all of pixles to one color
void setColor(uint32_t c) {
  for (uint16_t i = 0; i < strip.numPixels(); i++) {
    strip.setPixelColor(i, c);
  }
  strip.show();
}

// set intial pixles status and set brightness
void setupNeoPixel() {
  strip.setBrightness(BRIGHTNESS);
  strip.begin();
  strip.show(); // Initialize all pixels to 'off'

  if (HARDWARETEST) {
    Serial.println("Testing NeoPixels");
    colorWipe(strip.Color(255, 0, 0), 50); // Red
    colorWipe(strip.Color(0, 255, 0), 50); // Green
    colorWipe(strip.Color(0, 0, 255), 50); // Blue
    colorWipe(strip.Color(0, 0, 0, 255), 50); // White
    setColor(strip.Color(0, 0, 0));
  }
}

/********************** LSM9DSO ********************************/

void setupSensor()
{
  // 1.) Set the accelerometer range
  lsm.setupAccel(lsm.LSM9DS0_ACCELRANGE_2G);

  // 2.) Set the magnetometer sensitivity
  lsm.setupMag(lsm.LSM9DS0_MAGGAIN_2GAUSS);


  // 3.) Setup the gyroscope
  lsm.setupGyro(lsm.LSM9DS0_GYROSCALE_245DPS);
}


void connectSensor()
{
  Serial.println("Connecting to Sensor");

  // Try to initialise and warn if we couldn't detect the chip
  while (!lsm.begin())
  {
    Serial.println("Oops ... unable to initialize the LSM9DS0. Trying again");
    delay(1000);
  }
  Serial.println("Found LSM9DS0 9DOF");
}

// Recive data and update status
void reciveData1()
{
  static long int accelCombineL = 0;
  static int accelZL = 0;
  static long int gyroCombineL = 0;
  static int gyroZL = 0;


  lsm.read();
  // combine data from x and y axis to make it more simple
  long int accelCombine = sqrt( (sq((long int)lsm.accelData.x) + sq((long int)lsm.accelData.y)));
  int accelZ = (int)lsm.accelData.z;

  long int gyroCombine = sqrt( (sq((long int)lsm.gyroData.x) + sq((long int)lsm.gyroData.y)));
  int gyroZ = (int)lsm.gyroData.z;



  // Numerical differentiante
  int accelCombineDiff = abs((accelCombine - accelCombineL));
  int accelZDiff = abs((accelZ - accelZL));
  int gyroCombineDiff = abs((gyroCombine - gyroCombineL));
  int gyroZDiff = abs((gyroZ - gyroZL));

  int magz = lsm.magData.z;

  //Transfer to static variables for next time
  accelCombineL = accelCombine;
  accelZL = accelZ;
  gyroCombineL = gyroCombine;
  gyroZL = gyroZ;


  if (PRINTDATA) {
        Serial.print(accelCombine); Serial.print(',');
        Serial.print(accelCombineDiff); Serial.print(',');
    
        Serial.print(accelZ); Serial.print(',');
        Serial.print(accelZDiff); Serial.print(',');
    
        Serial.print(gyroCombine);      Serial.print(',');
        Serial.print(gyroCombineDiff); Serial.print(',');

        Serial.print(gyroZ);        Serial.print(',');
        Serial.print(gyroZDiff);    Serial.print(',');

        Serial.print(magz);       Serial.println(' ');
  }

  // orientation detection
  if (magz < -VERTICALVAL) {
    orient = vertical;
  }

  else if (magz > -HORIZVAL) {
    orient = horiz;
  }
  else {
    orient = mid;
  }


  // wrist twist detection
  if ((gyroZDiff > WRISTDIFF ) && (abs(gyroZ) > WRISTGY)) {
    wristTwist = true;
  }
  else {
    wristTwist = false;
  }

  // Flick detection
  if ((gyroCombineDiff > FLICKTRIG)) { // (gyroCombine > 16000) &&
    flick = true;
  }
  else {
    flick = false;
  }
}

