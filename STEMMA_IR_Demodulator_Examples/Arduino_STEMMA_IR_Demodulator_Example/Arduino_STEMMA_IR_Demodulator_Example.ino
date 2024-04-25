// SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*
 * Based on the ReceiverDump.cpp from the
 * Arduino-IRremote https://github.com/Arduino-IRremote/Arduino-IRremote.
 * by Armin Joachimsmeyer
 ************************************************************************************
 * MIT License
 *
 * Copyright (c) 2020-2023 Armin Joachimsmeyer
 * 
 */

#include <Arduino.h>
#include <IRremote.hpp>

#define IR_RECEIVE_PIN      5
#define MARK_EXCESS_MICROS    20    // Adapt it to your IR receiver module. 20 is recommended for the cheap VS1838 modules.

int ir_count = 0;
bool ir_state = false;

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);

  Serial.begin(115200);
  // Start the receiver and if not 3. parameter specified, take LED_BUILTIN pin from the internal boards definition as default feedback LED
  IrReceiver.begin(IR_RECEIVE_PIN, ENABLE_LED_FEEDBACK);
  Serial.print(F("Ready to receive IR signals "));
  Serial.print("at pin ");
  Serial.println(IR_RECEIVE_PIN);

}

void loop() {
  // put your main code here, to run repeatedly:
  if (IrReceiver.decode()) {  // Grab an IR code
        // At 115200 baud, printing takes 200 ms for NEC protocol and 70 ms for NEC repeat
        ir_state = true;
        Serial.println(); // blank line between entries
        Serial.println(); // 2 blank lines between entries
        IrReceiver.printIRResultShort(&Serial);
        if (IrReceiver.decodedIRData.flags & IRDATA_FLAGS_WAS_OVERFLOW) {
            Serial.print("Try to increase the \"RAW_BUFFER_LENGTH\" value of ");
            Serial.println(RAW_BUFFER_LENGTH);
            // see also https://github.com/Arduino-IRremote/Arduino-IRremote#compile-options--macros-for-this-library
        } else {
          Serial.println(); 
          Serial.println("IR signal received!");
          IrReceiver.printIRResultRawFormatted(&Serial, true);  // Output the results in RAW format
          ir_count += 1;
          Serial.print("Signal count: ");
          Serial.println(ir_count);
          Serial.println(); 
        }
   IrReceiver.resume();
  }
  else {
    ir_state = false;
  }
  
}
