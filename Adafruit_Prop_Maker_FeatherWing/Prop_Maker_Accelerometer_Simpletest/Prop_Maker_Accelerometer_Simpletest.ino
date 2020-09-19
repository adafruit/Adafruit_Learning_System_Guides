/*
* Adafruit Prop-Maker Featherwing
* Accelerometer Example
* 
* Prints acceleration data to the Serial Monitor
*/
// include the accelerometer library
#include <Adafruit_LIS3DH.h>

// Adjust this number for the sensitivity of the 'click' force
// this strongly depend on the range! for 16G, try 5-10
// for 8G, try 10-20. for 4G try 20-40. for 2G try 40-80
#define CLICKTHRESHHOLD 40

// inst. i2c accelerometer
Adafruit_LIS3DH lis = Adafruit_LIS3DH();

void setup() {
  Serial.begin(115200);
  Serial.println("\nProp-Maker Wing: Accelerometer");

  Serial.println("Starting LIS3DH...");
  if (! lis.begin(0x18)) {   // change this to 0x19 for alternative i2c address
    Serial.println("Couldnt start LIS3DH");
    while (1);
  }
  Serial.println("LIS3DH Started!");

  // Set Accelerometer Range (2, 4, 8, or 16 G!)
  lis.setRange(LIS3DH_RANGE_4_G);

  /* Set Accelerometer Click Detection
  * 0 = turn off click detection & interrupt
  * 1 = single click only interrupt output
  * 2 = double click only interrupt output   
  * NOTE: Higher numbers are less sensitive
  */
  lis.setClick(1, CLICKTHRESHHOLD);

}

void loop() {

  // Detect a click 
  uint8_t click = lis.getClick();
  
  // Get a new accel. sensor event
  sensors_event_t event; 
  lis.getEvent(&event);
  
  /* Display the results (acceleration is measured in m/s^2) */
  Serial.print("\t\tX: "); Serial.print(event.acceleration.x);
  Serial.print(" \tY: "); Serial.print(event.acceleration.y); 
  Serial.print(" \tZ: "); Serial.print(event.acceleration.z); 
  Serial.println(" m/s^2 ");
  Serial.println();

  delay(1000); 
  
  // detect click
  if (click & 0x10) Serial.print(" single click");
}
