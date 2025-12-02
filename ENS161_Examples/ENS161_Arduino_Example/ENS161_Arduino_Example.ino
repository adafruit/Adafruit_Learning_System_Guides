// SPDX-FileCopyrightText: 2021 Sciosense
//
// SPDX-License-Identifier: MIT

/***************************************************************************
  ENS161 - Digital Air Quality Sensor
  
  This is an example for ENS161 basic reading in standard mode
    
  Updated by Sciosense / 25-Nov-2021
 ***************************************************************************/

#include <Wire.h>
int ArduinoLED = 13;

#include "ScioSense_ENS160.h"  // ENS160 library
ScioSense_ENS160      ens160(ENS160_I2CADDR_1);

/*--------------------------------------------------------------------------
  SETUP function
  initiate sensor
 --------------------------------------------------------------------------*/
void setup() {

  Serial.begin(115200);

  while (!Serial) {}

  //Switch on LED for init
  pinMode(ArduinoLED, OUTPUT);
  digitalWrite(ArduinoLED, LOW);

  Serial.println("------------------------------------------------------------");
  Serial.println("ENS161 - Digital air quality sensor");
  Serial.println();
  Serial.println("Sensor readout in standard mode");
  Serial.println();
  Serial.println("------------------------------------------------------------");
  delay(1000);

  Serial.print("ENS161...");
  ens160.begin();
  Serial.println(ens160.available() ? "done." : "failed!");
  if (ens160.available()) {
    // Print ENS160 versions
    Serial.print("\tRev: "); Serial.print(ens160.getMajorRev());
    Serial.print("."); Serial.print(ens160.getMinorRev());
    Serial.print("."); Serial.println(ens160.getBuild());
  
    Serial.print("\tStandard mode ");
    Serial.println(ens160.setMode(ENS160_OPMODE_STD) ? "done." : "failed!");
  }
}

/*--------------------------------------------------------------------------
  MAIN LOOP FUNCTION
  Cylce every 1000ms and perform measurement
 --------------------------------------------------------------------------*/

void loop() {
  
  if (ens160.available()) {
    ens160.measure(true);
    ens160.measureRaw(true);
  
    Serial.print("AQI: ");Serial.print(ens160.getAQI());Serial.print("\t");
    Serial.print("TVOC: ");Serial.print(ens160.getTVOC());Serial.print("ppb\t");
    Serial.print("eCO2: ");Serial.print(ens160.geteCO2());Serial.print("ppm\t");
    Serial.print("R HP0: ");Serial.print(ens160.getHP0());Serial.print("Ohm\t");
    Serial.print("R HP1: ");Serial.print(ens160.getHP1());Serial.print("Ohm\t");
    Serial.print("R HP2: ");Serial.print(ens160.getHP2());Serial.print("Ohm\t");
    Serial.print("R HP3: ");Serial.print(ens160.getHP3());Serial.println("Ohm");
  }
  delay(1000);
}
