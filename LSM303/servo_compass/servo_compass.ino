// SPDX-FileCopyrightText: 2019 Bill Earl for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// **********************************************
// Zax-O-Meter Sketch 
// for the Adafruit LSM303 Magnetometer Breakout
//
// Written by Bill Earl for Adafruit Industries
//
// **********************************************

#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_LIS2MDL.h>

//Uncomment this line and comment out the above for the LSM303DLH
//#include <Adafruit_LSM303DLH_Mag.h>
#include <Servo.h>

/* Assign a unique ID to this sensor at the same time */
Adafruit_LIS2MDL mag = Adafruit_LIS2MDL(12345);
//Uncomment this line and comment out the above for the LSM303DLH
//Adafruit_LSM303DLH_Mag_Unified mag = Adafruit_LSM303AGR_Mag_Unified(12345);

// This is our continuous rotation servo
Servo servo;

// Pi for calculations - not the raspberry type
const float Pi = 3.14159;

// This is the value that gives you minimal rotation on
// a continuous rotation servo.  It is usually about 90.
// adjust this value to give minimal rotation for your servo
const float ServoNeutral = 90;  

// This is the desired direction of travel
// expressed as a 0-360 degree compass heading
// 0.0 = North
// 90.0 = East
// 180.0 = South
// 270 = West
const float targetHeading = 0.0;


void setup(void) 
{
  Serial.begin(115200);
  Serial.println("Magnetometer Test"); Serial.println("");
  
  /* Initialise the sensor */
  if(!mag.begin())
  {
    /* There was a problem detecting the LSM303 ... check your connections */
    Serial.println("Ooops, no LSM303 detected ... Check your wiring!");
    while(1);
  }
  
  servo.attach(9);  // Attach servo to pin 9

}

void loop(void) 
{
  /* Get a new sensor event */ 
  sensors_event_t event; 
  mag.getEvent(&event);
     
  // Calculate the angle of the vector y,x
  float heading = (atan2(event.magnetic.y,event.magnetic.x) * 180) / Pi;
  // Normalize to 0-360
  if (heading < 0)
  {
    heading = 360 + heading;
  }
  
  // Calculate the error between tha measured heading and the target heading.
  float error = heading - targetHeading;
  if (error > 180)
  {
    error = error - 360;  // for angles > 180, correct in the opposite direction.
  }
  // A non-zero difference between the heading and the 
  // targetHeading will bias the servoNeutral value and 
  // cause the servo to rotate back toward the targetHeading.
  // The divisor is to reduce the reaction speed and avoid oscillations
  servo.write(ServoNeutral + error / 4 );

  delay(40);
}
