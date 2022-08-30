// SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_LSM6DS3TRC.h>

int x;
int y;
int z;

Adafruit_LSM6DS3TRC lsm6ds;

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);

  if (!lsm6ds.begin_I2C()) {
    while (1) {
      delay(10);
    }
  }
  lsm6ds.setAccelRange(LSM6DS_ACCEL_RANGE_2_G);
  lsm6ds.setGyroRange(LSM6DS_GYRO_RANGE_250_DPS);
  lis3mdl.setRange(LIS3MDL_RANGE_4_GAUSS);

  lsm6ds.setAccelDataRate(LSM6DS_RATE_104_HZ);
  lsm6ds.setGyroDataRate(LSM6DS_RATE_104_HZ);
  lis3mdl.setDataRate(LIS3MDL_DATARATE_1000_HZ);
  lis3mdl.setPerformanceMode(LIS3MDL_MEDIUMMODE);
  lis3mdl.setOperationMode(LIS3MDL_CONTINUOUSMODE);

}

void loop() {
  // put your main code here, to run repeatedly:

  sensors_event_t accel;
  sensors_event_t gyro;
  sensors_event_t temp;
  lsm6ds.getEvent(&accel, &gyro, &temp);

  x = map(accel.acceleration.x, -12, 11, 180, -180); 
  y = map(accel.acceleration.y, -19, 20, -180, 180); 
  z = map(accel.acceleration.z, -17, 15, 180, -180); 

  Serial.print("|");
  Serial.print(x);
  Serial.print("|");
  Serial.print(y);
  Serial.print("|");
  Serial.print(z);
  Serial.println();
  delay(50);
}
