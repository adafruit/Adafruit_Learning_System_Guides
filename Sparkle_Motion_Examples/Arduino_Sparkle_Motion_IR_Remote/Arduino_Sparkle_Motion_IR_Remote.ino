// SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
// SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
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
#include <Adafruit_NeoPixel.h>

#define NEOPIXEL_STRIP_PIN 21
#define NUM_PIXELS 8

#define IR_RECEIVE_PIN   32

Adafruit_NeoPixel NEOPIXEL_STRIP(NUM_PIXELS, NEOPIXEL_STRIP_PIN, NEO_GRB + NEO_KHZ800);

uint8_t upCmd = 0x5;
uint8_t downCmd = 0xD;
uint8_t rightCmd = 0xA;
uint8_t leftCmd = 0x8;

uint16_t pixelHue = 0;
uint8_t brightness = 25;

void setup() {
    Serial.begin(115200);
    while (!Serial)
        ;
    Serial.println("Adafruit Sparkle Motion IR Remote Control NeoPixels Demo");
    IrReceiver.begin(IR_RECEIVE_PIN);
    Serial.print("IRin on pin ");
    Serial.print(IR_RECEIVE_PIN);
    NEOPIXEL_STRIP.begin();
    NEOPIXEL_STRIP.setBrightness(25);
}

void loop() {
    /*
     * Check if received data is available and if yes, try to decode it.
     * When left or right buttons are pressed, change the pixelHue.
     * When up or down buttons are pressed, change the brightness.
     */
    if (IrReceiver.decode()) {
        if (IrReceiver.decodedIRData.protocol == UNKNOWN) {
            Serial.println("unknown");
            IrReceiver.printIRResultRawFormatted(&Serial, true);
            IrReceiver.resume();
        } else {
            IrReceiver.resume();
            //IrReceiver.printIRResultShort(&Serial);

            // Ignore repeat codes from holding down the button
            if (IrReceiver.decodedIRData.flags == 0){
              //Serial.printf("Command: %d\n",IrReceiver.decodedIRData.command);
              if (IrReceiver.decodedIRData.command == upCmd){
                Serial.println("UP btn");
                brightness = min(brightness + 25, 255);
              }else if (IrReceiver.decodedIRData.command == downCmd){
                Serial.println("DOWN btn");
                brightness = max(brightness - 25, 0);
              }else if (IrReceiver.decodedIRData.command == leftCmd){
                Serial.println("LEFT btn");
                pixelHue = (pixelHue - 8192) % 65536;
              }else if (IrReceiver.decodedIRData.command == rightCmd){
                Serial.println("RIGHT btn");
                pixelHue = (pixelHue + 8192) % 65536;
              }

              NEOPIXEL_STRIP.setBrightness(brightness);
              NEOPIXEL_STRIP.fill(NEOPIXEL_STRIP.gamma32(NEOPIXEL_STRIP.ColorHSV(pixelHue)));
              NEOPIXEL_STRIP.show();
              delay(100);
            }
        }
        Serial.println();
    }
}
