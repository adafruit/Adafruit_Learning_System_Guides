// SPDX-FileCopyrightText: 2024 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_MCP2515.h>
#include <Adafruit_SSD1306.h>
#include <Fonts/FreeSans9pt7b.h>

#define CS_PIN    A3
#define CAN_BAUDRATE (250000)

Adafruit_MCP2515 mcp(CS_PIN);
Adafruit_SSD1306 oled(128, 64, &Wire1, -1);


void setup() {
  Serial.begin(115200);
  while(!Serial) delay(10);
  Serial.println("MCP2515 OLED Receiver test!");

  if (!mcp.begin(CAN_BAUDRATE)) {
    Serial.println("Error initializing MCP2515.");
    while(1) delay(10);
  }
  Serial.println("MCP2515 chip found");

  if (!oled.begin(SSD1306_SWITCHCAPVCC, 0x3D)) {
    Serial.println(F("SSD1306 allocation failed"));
    while(1) delay(10);
  }
  oled.display();
  delay(1000);
  oled.clearDisplay();
  oled.display();
  oled.setFont(&FreeSans9pt7b);
  oled.setTextColor(SSD1306_WHITE);
}

void loop() {
  // try to parse packet
  int packetSize = mcp.parsePacket();

  if (packetSize) {
    // received a packet
    Serial.print("Received ");


    Serial.print("packet with id 0x");
    Serial.print(mcp.packetId(), HEX);
    Serial.print(" and length ");
    Serial.println(packetSize);

    // only look for correct length packets
    if (packetSize != 3) return;
    
    // wait till all data is ready!
    while (mcp.available() != 3) {
      delay(1);
    }
    uint8_t button_state = 0;
    int16_t val = 0;
    
    button_state = mcp.read();
    val = mcp.read();
    val <<= 8;
    val |= mcp.read();

    Serial.print("Button is ");
    if (button_state) Serial.print("pressed");
    else  Serial.print("released");
    Serial.print(" & value is ");
    Serial.println(val);

    oled.clearDisplay();
    oled.setCursor(0, 15);
    oled.println("CAN receiver");
    oled.print("Val: "); oled.println(val);
    oled.print("Button ");
    if (button_state) oled.print("DOWN");
    else  oled.print("UP");
    oled.display();
  }
}
