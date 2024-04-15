// SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_ADG72x.h>

Adafruit_ADG72x adg72x;

bool isADG728 = false; // which chip are we connected to?

int analogIn = A0;
int analogValue = 0;
unsigned long switchTimer = 1000; // 1000 ms = 1 second for channel switch
unsigned long readTimer = 10; // 10 ms for analog read
unsigned long lastSwitchTime = 0; // Last time the channels were switched
unsigned long lastReadTime = 0; // Last time the analog was read
uint8_t currentChannel = 0; // Current channel being selected

void setup() {
  Serial.begin(115200);

  // Wait for serial port to open
  while (!Serial) {
    delay(1);
  }

  // Try with the ADG728 default address first...
  if (adg72x.begin(ADG728_DEFAULT_ADDR, &Wire)) {
    Serial.println("ADG728 found!");
    isADG728 = true;
  }
  // Maybe they have an ADG729?
  else if (adg72x.begin(ADG729_DEFAULT_ADDR, &Wire)) {
    Serial.println("ADG729 found!");
    isADG728 = false;
  }
  else {
    Serial.println("No ADG device found? Check wiring!");
    while (1); // Stop here if no device was found
  }
}

void loop() {
  unsigned long currentTime = millis();

  // read and print analog value every 10ms
  if ((currentTime - lastReadTime) >= readTimer) {
    analogValue = analogRead(analogIn);
    Serial.println(analogValue);
    lastReadTime = currentTime;
  }

  // switch channels every 1 second
  if ((currentTime - lastSwitchTime) >= switchTimer) {
    uint8_t bits = 1 << currentChannel; // Shift a '1' from LSB to MSB
    if (!adg72x.selectChannels(bits)) {
      Serial.println("Failed to set channels...");
    }
    /*Serial.print((currentChannel % 4) + 1);
    if (currentChannel < 4) Serial.println("A");
    else       Serial.println("B");*/
    currentChannel = (currentChannel + 1) % 8; // Move to the next channel, wrap around at 8
    lastSwitchTime = currentTime;
  }
}
