// rf69 demo tx rx.pde
// -*- mode: C++ -*-
// Example sketch showing how to create a simple messageing client
// with the RH_RF69 class. RH_RF69 class does not provide for addressing or
// reliability, so you should only use RH_RF69  if you do not need the higher
// level messaging abilities.
// It is designed to work with the other example rf69_server.
// Demonstrates the use of AES encryption, setting the frequency and modem 
// configuration

#include <RH_RF69.h>
#include "Adafruit_TestBed.h"

extern Adafruit_TestBed TB;

// Singleton instance of the radio driver
RH_RF69 rf69(PIN_RFM_CS, PIN_RFM_DIO0);

void setup() 
{
  Serial.begin(115200);

  pinMode(PIN_LED, OUTPUT);     
  pinMode(PIN_RFM_RST, OUTPUT);
  digitalWrite(PIN_RFM_RST, LOW);

  TB.neopixelPin = PIN_NEOPIXEL;
  TB.neopixelNum = 1;
  TB.begin();

  Serial.println("Feather RFM69 Feather Self-test!");
  Serial.println();
}

uint8_t x = 0;

void loop() {
  TB.setColor(TB.Wheel(x++));

  if (x == 255) {
    // manual reset
    digitalWrite(PIN_RFM_RST, HIGH);
    delay(10);
    digitalWrite(PIN_RFM_RST, LOW);
    delay(10);
    
    if (!rf69.init()) {
      Serial.println("RFM69 radio init failed");
      while (1);
    }
    Serial.println("RFM69 radio init OK!");
  }

  delay(10);
}
