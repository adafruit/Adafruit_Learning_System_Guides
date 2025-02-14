// SPDX-FileCopyrightText: 2024 ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*
  ReadAnalogVoltage

  Reads an analog input on pin P1.1, converts it to voltage, and prints the result to the Serial Monitor.
  Graphical representation is available using Serial Plotter (Tools > Serial Plotter menu).
  Attach the center pin of a potentiometer to pin P1.1, and the outside pins to +5V and ground.

  This example code is in the public domain.

  http://www.arduino.cc/en/Tutorial/ReadAnalogVoltage
*/

#include <Serial.h>

#define A0 11
#define A1 14
#define A2 15 // also MISO!
#define A3 32

#define ANALOG_IN  A3
#define VREF       3.3

// the setup routine runs once when you press reset:
void setup() {
  // No need to init USBSerial

  // By default 8051 enable every pin's pull up resistor. Disable pull-up to get full input range.
  pinMode(ANALOG_IN, INPUT);
}

// the loop routine runs over and over again forever:
void loop() {
  // read the input on analog pin 0, P1.1:
  int sensorValue = analogRead(ANALOG_IN);
  // Convert the analog reading (which goes from 0 - 255) to VREF:
  float voltage = sensorValue * (VREF / 255.0);
  // print out the value you read:
  USBSerial_println(voltage);
  // or with precision:
  //USBSerial_println(voltage,1);

  delay(10);
}
