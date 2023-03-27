// SPDX-FileCopyrightText: 2023 Carter Nelson for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*
 * Adafruit MCP2515 FeatherWing CAN Receiver Example
 */

#include <Adafruit_MCP2515.h>

// Set pin attached to CS
// CS_PIN 7 for Feather RP2040
#define CS_PIN 7

Adafruit_MCP2515 mcp(CS_PIN);

void setup() {
  Serial.begin(9600);
  while(!Serial);

  if (!mcp.begin()) {
    Serial.println("Error initializing MCP2515.");
    while(1);
  }
}

void loop() {
  // try to parse packet
  int packetSize = mcp.parsePacket();

  if (packetSize) {
    // received a packet
    Serial.print("Received ");

    if (mcp.packetExtended()) {
      Serial.print("extended ");
    }

    if (mcp.packetRtr()) {
      // Remote transmission request, packet contains no data
      Serial.print("RTR ");
    }

    Serial.print("packet with id 0x");
    Serial.print(mcp.packetId(), HEX);

    if (mcp.packetRtr()) {
      Serial.print(" and requested length ");
      Serial.println(mcp.packetDlc());
    } else {
      Serial.print(" and length ");
      Serial.println(packetSize);

      // only print packet data for non-RTR packets
      while (mcp.available()) {
        Serial.print((char)mcp.read());
      }
      Serial.println();
    }

    Serial.println();
  }
}
