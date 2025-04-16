// SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_MCP23X17.h>

#define NOID_1 0     // MCP23XXX pin LED is attached to
#define NOID_2 4     // MCP23XXX pin LED is attached to

Adafruit_MCP23X17 mcp;

void setup() {
  Serial.begin(115200);
  while (!Serial);
  Serial.println("8 Channel Solenoid Driver Demo");
  if (!mcp.begin_I2C()) {
    Serial.println("Couldn't find MCP23017..");
    while (1);
  }
  mcp.pinMode(NOID_1, OUTPUT);
  mcp.pinMode(NOID_2, OUTPUT);

  Serial.println("Found MCP23017, looping...");
}

void loop() {
  Serial.println("Solenoid 1!");
  mcp.digitalWrite(NOID_1, HIGH);
  delay(500);
  mcp.digitalWrite(NOID_1, LOW);
  delay(500);
  Serial.println("Solenoid 2!");
  mcp.digitalWrite(NOID_2, HIGH);
  delay(500);
  mcp.digitalWrite(NOID_2, LOW);
  delay(500);
  Serial.println("Together!");
  mcp.digitalWrite(NOID_1, HIGH);
  mcp.digitalWrite(NOID_2, HIGH);
  delay(1000);
  mcp.digitalWrite(NOID_1, LOW);
  mcp.digitalWrite(NOID_2, LOW);
  delay(2000);
  Serial.println("Repeat!");
  Serial.println();
  delay(500);
}
