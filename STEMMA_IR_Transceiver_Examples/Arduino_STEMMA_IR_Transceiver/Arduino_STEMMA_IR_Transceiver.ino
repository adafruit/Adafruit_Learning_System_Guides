// SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*
 * Based on the SimpleReceiver.cpp and SimpleSender.cpp from the
 * Arduino-IRremote https://github.com/Arduino-IRremote/Arduino-IRremote.
 * by Armin Joachimsmeyer
 ************************************************************************************
 * MIT License
 *
 * Copyright (c) 2020-2023 Armin Joachimsmeyer
 * 
 */

#include <Arduino.h>

#include <IRremote.hpp> // include the library
#define IR_RECEIVE_PIN   5
#define IR_SEND_PIN      6

void setup() {
    Serial.begin(115200);
    while (!Serial)
        ;
    Serial.println("Adafruit STEMMA IR Transceiver Demo");
    IrReceiver.begin(IR_RECEIVE_PIN);
    IrSender.begin(IR_SEND_PIN); // Start with IR_SEND_PIN -which is defined in PinDefinitionsAndMore.h- as send pin and enable feedback LED at default feedback LED pin
    Serial.print("IRin on pin ");
    Serial.print(IR_RECEIVE_PIN);
    Serial.print(", IRout on pin ");
    Serial.println(IR_SEND_PIN);
}

uint8_t sCommand = 0x34;
uint8_t sRepeats = 0;

void loop() {
    /*
     * Check if received data is available and if yes, try to decode it.
     * Decoded result is in the IrReceiver.decodedIRData structure.
     *
     * E.g. command is in IrReceiver.decodedIRData.command
     * address is in command is in IrReceiver.decodedIRData.address
     * and up to 32 bit raw data in IrReceiver.decodedIRData.decodedRawData
     */
    if (IrReceiver.decode()) {
        if (IrReceiver.decodedIRData.protocol == UNKNOWN) {
            IrReceiver.printIRResultRawFormatted(&Serial, true);
            IrReceiver.resume();
        } else {
            IrReceiver.resume();
            IrReceiver.printIRResultShort(&Serial);
            IrReceiver.printIRSendUsage(&Serial);
            delay(1000);
            Serial.println("Sending received command..");
            IrSender.sendNEC(IrReceiver.lastDecodedProtocol, IrReceiver.lastDecodedCommand, IrReceiver.repeatCount);
            delay(1000);
            Serial.print("Sent!");
            //Serial.println(IrReceiver.lastDecodedProtocol, IrReceiver.lastDecodedCommand, IrReceiver.repeatCount);
        }
        Serial.println();
    }
}
