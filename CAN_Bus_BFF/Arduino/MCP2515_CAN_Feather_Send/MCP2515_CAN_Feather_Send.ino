// SPDX-FileCopyrightText: 2024 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include "Adafruit_seesaw.h"
#include <seesaw_neopixel.h>
#include <Adafruit_MCP2515.h>
#include <Adafruit_NeoPixel.h>


#define CS_PIN    PIN_CAN_CS // for Feather RP2040 CAN, change if needed!
Adafruit_MCP2515 mcp(CS_PIN);


#define CAN_BAUDRATE     (250000) // must match the other devices!   
#define SS_SWITCH        24
#define SS_NEOPIX        6
#define SEESAW_ADDR      0x36

Adafruit_seesaw ss;
seesaw_NeoPixel sspixel = seesaw_NeoPixel(1, SS_NEOPIX, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel pixel(1, 21, NEO_GRB + NEO_KHZ800);


int16_t encoder_position;
bool button_state;

void setup() {
  Serial.begin(115200);
  delay(500);
  while (!Serial) delay(10);

  Serial.println("MCP2515 Sender test!");
  if (!mcp.begin(CAN_BAUDRATE)) {
    Serial.println("Error initializing MCP2515.");
    while(1) delay(10);
  }
  Serial.println("MCP2515 chip found");

  Serial.println("Looking for seesaw!");
  if (! ss.begin(SEESAW_ADDR) || ! sspixel.begin(SEESAW_ADDR)) {
    Serial.println("Couldn't find seesaw on default address");
    while(1) delay(10);
  }
  Serial.println("seesaw started");

  uint32_t version = ((ss.getVersion() >> 16) & 0xFFFF);
  if (version  != 4991){
    Serial.print("Wrong firmware loaded? ");
    Serial.println(version);
    while(1) delay(10);
  }
  Serial.println("Found Product 4991");

  // set not so bright!
  sspixel.setBrightness(20);
  sspixel.show();

  // ditto built in pixel
  pinMode(NEOPIXEL_POWER, OUTPUT);
  digitalWrite(NEOPIXEL_POWER, HIGH);
  pixel.begin();
  pixel.setBrightness(20);
  pixel.show();
  
  // use a pin for the built in encoder switch
  ss.pinMode(SS_SWITCH, INPUT_PULLUP);

  // get starting position
  encoder_position = ss.getEncoderPosition();
  button_state = ss.digitalRead(SS_SWITCH);
}

void loop() {
  bool new_button = ss.digitalRead(SS_SWITCH);
  
  if (new_button != button_state) {
    Serial.println("Button pressed!");
  }

  int32_t new_position = ss.getEncoderPosition();
  // did we move around or button change?
  if ((new_button != button_state) ||
      (encoder_position != new_position)) {

    encoder_position = new_position;      // and save for next round
    button_state = new_button;

    pixel.setPixelColor(0, Wheel(new_position & 0xFF));
    pixel.show();
    
    Serial.print("Sending Position ");
    Serial.print(encoder_position);
    Serial.print(" & Button ");
    Serial.println(button_state);
    
    mcp.beginPacket(0x12);
    if (ss.digitalRead(SS_SWITCH)) {
      mcp.write(0);
    } else {
      mcp.write(1);
    }
    mcp.write(encoder_position >> 8);
    mcp.write(encoder_position & 0xFF);
    if (mcp.endPacket()) {
      Serial.println("Done");
      // change the neopixel color on success
      sspixel.setPixelColor(0, Wheel(new_position & 0xFF));
    } else {
      Serial.println("Failure");
      // turn off neopixel on failure
      sspixel.setPixelColor(0, 0x00);
    }
    sspixel.show();
  }

  // don't overwhelm serial port
  delay(10);
}


uint32_t Wheel(byte WheelPos) {
  WheelPos = 255 - WheelPos;
  if (WheelPos < 85) {
    return sspixel.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  }
  if (WheelPos < 170) {
    WheelPos -= 85;
    return sspixel.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
  WheelPos -= 170;
  return sspixel.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
}
