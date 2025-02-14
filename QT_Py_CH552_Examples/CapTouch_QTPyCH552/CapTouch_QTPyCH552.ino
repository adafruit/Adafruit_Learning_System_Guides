// SPDX-FileCopyrightText: 2024 ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <TouchKey.h>

uint8_t count = 0;
uint8_t state = 0;

void setup() {
  while (!USBSerial()); // wait for serial port to connect. Needed for native USB port only
  delay(100);
  USBSerial_println("QT Py CH552 Cap Touch Test");
  USBSerial_println("Uses pin A0 (P1.1)");
  TouchKey_begin((1 << 1)); //Enable channel P1.1/A0
}

void loop() {
  // put your main code here, to run repeatedly:
  TouchKey_Process();
  uint8_t touchResult = TouchKey_Get();
  if (touchResult) {
    if (state == 0) {
    count += 1;
    state = 1;
    USBSerial_print("TIN1.1 touched ");
    USBSerial_print(count);
    USBSerial_println(" times");
    }
  } else {
    state = 0;
  }
  delay(1000);

}
