// SPDX-FileCopyrightText: 2021 Phil Burgess for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*
BLUETOOTH THING for Adafruit EyeLights (LED Glasses + Driver).
*/

#include <Adafruit_IS31FL3741.h> // For LED driver
#include <bluefruit.h>
#include "EyeLightsCanvasFont.h"

// function prototypes over in packetParser.cpp
uint8_t readPacket(BLEUart *ble, uint16_t timeout);
float parsefloat(uint8_t *buffer);
void printHex(const uint8_t * data, const uint32_t numBytes);
int8_t packetType(uint8_t *buf, uint8_t len);

// GLOBAL VARIABLES -------

// Packet buffer
extern uint8_t packetbuffer[];

// BLE Service
BLEDis  bledis;
BLEUart bleuart;

Adafruit_EyeLights_buffered glasses; // LED matrix is buffered for smooth animation

// Crude error handler, prints message to Serial console, flashes LED
void err(char *str, uint8_t hz) {
  Serial.println(str);
  pinMode(LED_BUILTIN, OUTPUT);
  for (;;) digitalWrite(LED_BUILTIN, (millis() * hz / 500) & 1);
}

void setup() { // Runs once at program start...

  Serial.begin(115200);
  //while(!Serial);

  Bluefruit.begin();
  Bluefruit.setTxPower(4);    // Check bluefruit.h for supported values

  // Configure and start the BLE Uart service
  bleuart.begin();

  // Set up and start advertising
  startAdv();

  if (! glasses.begin()) err("IS3741 not found", 2);

  // Configure glasses for max brightness, enable output
  glasses.setLEDscaling(0xFF);
  glasses.setGlobalCurrent(0xFF);
  glasses.enable(true);
}

void startAdv(void)
{
  // Advertising packet
  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  Bluefruit.Advertising.addTxPower();
  
  // Include the BLE UART (AKA 'NUS') 128-bit UUID
  Bluefruit.Advertising.addService(bleuart);

  // Secondary Scan Response packet (optional)
  // Since there is no room for 'Name' in Advertising packet
  Bluefruit.ScanResponse.addName();

  /* Start Advertising
   * - Enable auto advertising if disconnected
   * - Interval:  fast mode = 20 ms, slow mode = 152.5 ms
   * - Timeout for fast mode is 30 seconds
   * - Start(timeout) with timeout = 0 will advertise forever (until connected)
   * 
   * For recommended advertising interval
   * https://developer.apple.com/library/content/qa/qa1931/_index.html   
   */
  Bluefruit.Advertising.restartOnDisconnect(true);
  Bluefruit.Advertising.setInterval(32, 244);    // in unit of 0.625 ms
  Bluefruit.Advertising.setFastTimeout(30);      // number of seconds in fast mode
  Bluefruit.Advertising.start(0);                // 0 = Don't stop advertising after n seconds  
}

void loop() { // Repeat forever...

  uint8_t len = readPacket(&bleuart, 500);
  if (len == 0) return;

  switch(packetType(packetbuffer, len)) {
  case 0: // Accelerometer
    Serial.println("Accel");
    break;
  case 1: // Gyro:
    Serial.println("Gyro");
    break;
  case 2: // Magnetometer
    Serial.println("Mag");
    break;
  case 3: // Quaternion
    Serial.println("Quat");
    break;
  case 4: // Button
    Serial.println("Button");
    break;
  case 5: // Color
    Serial.println("Color");
    printHex(&packetbuffer[2], 3);
    break;
  case 6: // Location
    Serial.println("Location");
    break;
  default:
    Serial.println((char *)packetbuffer);
  }

  glasses.fill(0);

  glasses.show(); // Buffered mode MUST use show() to refresh matrix
}
