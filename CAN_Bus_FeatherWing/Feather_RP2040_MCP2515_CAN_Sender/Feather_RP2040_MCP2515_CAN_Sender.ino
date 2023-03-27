// SPDX-FileCopyrightText: 2023 Carter Nelson for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*
 * Adafruit MCP2515 FeatherWing CAN Sender Example
 */

#include <Adafruit_MCP2515.h>

// Set pin attached to CS
// CS_PIN 7 for Feather RP2040
#define CS_PIN 7

Adafruit_MCP2515 mcpcan(CS_PIN);

void setup() {
  Serial.begin(9600);
  while(!Serial);

  if (!mcpcan.begin()) {
    Serial.println("Error initializing MCP2515.");
    while(1);
  }
}

void loop() {
  // send packet: id is 11 bits, packet can contain up to 8 bytes of data
  Serial.println("Sending packet ... ");
  mcpcan.beginPacket(0x12);
  mcpcan.write('h');
  mcpcan.write('e');
  mcpcan.write('l');
  mcpcan.write('l');
  mcpcan.write('o');
  if (!mcpcan.endPacket()) {
      Serial.println("Failed!");
      return;
    }
  Serial.println("Packet done");

  delay(1000);

  // send extended packet: id is 29 bits, packet can contain up to 8 bytes of data
  Serial.println("Sending extended packet ... ");

  mcpcan.beginExtendedPacket(0xabcdef);
  mcpcan.write('w');
  mcpcan.write('o');
  mcpcan.write('r');
  mcpcan.write('l');
  mcpcan.write('d');
  if (!mcpcan.endPacket()) {
      Serial.println("Failed!");
      return;
    }
  Serial.println("Extended packet done");

  delay(1000);
}
