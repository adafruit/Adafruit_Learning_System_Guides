// SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT
/**
 * PCA9546 I2C Multi Sensor Example
 *
 * Using two VL53L4CD sensors on ports 0 and 1
 *
 */

#include <Arduino.h>
#include <Wire.h>
#include <vl53l4cd_class.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <assert.h>

#define PCAADDR 0x70
#define DEV_I2C Wire

#define SerialPort Serial

// create two instances of the sensor
VL53L4CD tof1(&DEV_I2C, A1);
VL53L4CD tof2(&DEV_I2C, A1);

void pcaselect(uint8_t i) {
  if (i > 3) return;
 
  Wire.beginTransmission(PCAADDR);
  Wire.write(1 << i);
  Wire.endTransmission();  
}

// standard Arduino setup()
void setup()
{
    while (!Serial);
    delay(1000);

    Wire.begin();
    
    Serial.begin(115200);
    Serial.println("\nMultiSensor PCA9546");
    
    // define the port on the PCA9546 for the first sensor
    pcaselect(0);
    // setup the first sensor
    tof1.begin();
    tof1.VL53L4CD_Off();
    tof1.InitSensor();
    tof1.VL53L4CD_SetRangeTiming(200, 0);
    tof1.VL53L4CD_StartRanging();
  
    // define the port on the PCA9546 for the 2nd sensor
    pcaselect(1);
    
    // setup the 2nd sensor
    tof2.begin();
    tof2.VL53L4CD_Off();
    tof2.InitSensor();
    tof2.VL53L4CD_SetRangeTiming(200, 0);
    tof2.VL53L4CD_StartRanging();
      
}

void loop() 
{
  uint8_t NewDataReady = 0;
  VL53L4CD_Result_t results;
  uint8_t status;
  char report[64];
  
  // define port on the PCA9546
  pcaselect(0);

  // loop for time of flight sensor 1
  do {
    status = tof1.VL53L4CD_CheckForDataReady(&NewDataReady);
  } while (!NewDataReady);

  if ((!status) && (NewDataReady != 0)) {
    // (Mandatory) Clear HW interrupt to restart measurements
    tof1.VL53L4CD_ClearInterrupt();

    // Read measured distance. RangeStatus = 0 means valid data
    tof1.VL53L4CD_GetResult(&results);
    snprintf(report, sizeof(report), "ToF 1 - Status = %3u, Distance = %5u mm, Signal = %6u kcps/spad\r\n",
             results.range_status,
             results.distance_mm,
             results.signal_per_spad_kcps);
    SerialPort.println(report);
  }

  // define port on PCA9546
  pcaselect(1);

  // loop for time of flight sensor 2
  do {
    status = tof2.VL53L4CD_CheckForDataReady(&NewDataReady);
  } while (!NewDataReady);

  if ((!status) && (NewDataReady != 0)) {
    // (Mandatory) Clear HW interrupt to restart measurements
    tof2.VL53L4CD_ClearInterrupt();

    // Read measured distance. RangeStatus = 0 means valid data
    tof2.VL53L4CD_GetResult(&results);
    snprintf(report, sizeof(report), "ToF 2 - Status = %3u, Distance = %5u mm, Signal = %6u kcps/spad\r\n",
             results.range_status,
             results.distance_mm,
             results.signal_per_spad_kcps);
    SerialPort.println(report);
  }
}
