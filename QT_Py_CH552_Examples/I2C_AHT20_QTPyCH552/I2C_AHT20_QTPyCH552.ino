// SPDX-FileCopyrightText: 2024 ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT
// https://chat.openai.com/share/5dddee44-3196-4a6b-b445-58ac6ef18501

#include <SoftI2C.h>

extern uint8_t scl_pin;
extern uint8_t sda_pin;

void Wire_begin(uint8_t scl, uint8_t sda);
bool Wire_scan(uint8_t i2caddr);
bool Wire_writeBytes(uint8_t i2caddr, uint8_t *data, uint8_t bytes);
bool Wire_readBytes(uint8_t i2caddr, uint8_t *data, uint8_t bytes);
bool Wire_readRegister(uint8_t i2caddr, uint8_t regaddr, uint8_t *data, uint8_t bytes);

bool readAHT20(float *temperature, float *humidity);
#define AHTX0_I2CADDR_DEFAULT 0x38

void setup() {
  while (!USBSerial()); // wait for serial port to connect. Needed for native USB port only
  delay(100);
  
  USBSerial_println("CH552 QT Py I2C sensor test");
  Wire_begin(33, 34); // set up I2C on CH552 QT Py

  USBSerial_print("I2C Scan: ");
  for (uint8_t a=0; a<=0x7F; a++) {
    if (!Wire_scan(a)) continue;
    USBSerial_print("0x");
    USBSerial_print(a, HEX);
    USBSerial_print(", ");
  }
  USBSerial_println();

  if (! Wire_scan(AHTX0_I2CADDR_DEFAULT)) {
    USBSerial_println("No AHT20 found!");
    while (1);
  }
}

void loop() {
  delay(100);
  
  float t, h;
  if (!readAHT20(&t, &h)) {
    USBSerial_println("Failed to read from AHT20");
  }
  USBSerial_print("Temp: ");
  USBSerial_print(t);
  USBSerial_print(" *C, Hum: ");
  USBSerial_print(h);
  USBSerial_println(" RH%");
}

/*********************** AHT20 'driver */

#define AHTX0_CMD_TRIGGER 0xAC
#define AHTX0_STATUS_BUSY 0x80

bool AHT20_getStatus(uint8_t *status) {
  return Wire_readBytes(AHTX0_I2CADDR_DEFAULT, status, 1);
}

bool readAHT20(float *temperature, float *humidity) {
  uint8_t cmd[3] = {AHTX0_CMD_TRIGGER, 0x33, 0x00};
  uint8_t data[6], status;
  uint32_t rawHumidity, rawTemperature;

  // Trigger AHT20 measurement
  if (!Wire_writeBytes(AHTX0_I2CADDR_DEFAULT, cmd, 3)) {
    return false;
  }

  // Wait until the sensor is no longer busy
  do {
    if (!AHT20_getStatus(&status)) {
      return false;
    }
    delay(10); // Delay 10ms to wait for measurement
  } while (status & AHTX0_STATUS_BUSY);

  // Read the measurement data
  if (!Wire_readBytes(AHTX0_I2CADDR_DEFAULT, data, 6)) {
    return false;
  }

  // Parse humidity data
  rawHumidity = data[1];
  rawHumidity = (rawHumidity << 8) | data[2];
  rawHumidity = (rawHumidity << 4) | (data[3] >> 4);
  *humidity = ((float)rawHumidity * 100.0) / 0x100000;

  // Parse temperature data
  rawTemperature = (data[3] & 0x0F);
  rawTemperature = (rawTemperature << 8) | data[4];
  rawTemperature = (rawTemperature << 8) | data[5];
  *temperature = ((float)rawTemperature * 200.0 / 0x100000) - 50.0;

  return true;
}

/**************************** Wire I2C interface */

void Wire_begin(uint8_t scl, uint8_t sda) {
  scl_pin = scl; //extern variable in SoftI2C.h
  sda_pin = sda;
  I2CInit();
}

bool Wire_scan(uint8_t i2caddr) {
  return Wire_writeBytes(i2caddr, NULL, 0);
}

bool Wire_readRegister(uint8_t i2caddr, uint8_t regaddr, uint8_t *data, uint8_t bytes) {
  if (!Wire_writeBytes(i2caddr, &regaddr, 1)) {
    return false;
  }

  return Wire_readBytes(i2caddr, data, bytes);
}


bool Wire_writeBytes(uint8_t i2caddr, uint8_t *data, uint8_t bytes) {
  uint8_t ack_bit;

  I2CStart();
  ack_bit = I2CSend(i2caddr << 1 | 0); // Shift address and append write bit
  if (ack_bit != 0) {
    I2CStop();
    return false;
  }

  for (uint8_t i = 0; i < bytes; i++) {
    if (I2CSend(data[i]) != 0) {
      I2CStop();
      return false;
    }
  }
  I2CStop();
  return true;
}

bool Wire_readBytes(uint8_t i2caddr, uint8_t *data, uint8_t bytes) {
  uint8_t ack_bit;

  I2CStart();
  ack_bit = I2CSend(i2caddr << 1 | 1); // Shift address and append read bit
  if (ack_bit != 0) {
    I2CStop();
    return false;
  }

  for (uint8_t i = 0; i < bytes; i++) {
    data[i] = I2CRead();
    if (i == bytes - 1) {
        I2CNak();  // NAK on last byte
    } else {
        I2CAck();  // ACK on other bytes
    }
  }

  I2CStop();
  return true;
}
