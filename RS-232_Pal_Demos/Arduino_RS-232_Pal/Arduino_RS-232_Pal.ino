// SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <SoftwareSerial.h>

// update this for your RS-232 device baud rate
#define baud 38400
// define RX and TX pins for the software serial port
#define RS232_RX_PIN 2
#define RS232_TX_PIN 3

SoftwareSerial rs232Serial(RS232_RX_PIN, RS232_TX_PIN);

void setup() {
  Serial.begin(115200);
  while ( !Serial ) delay(10);

  rs232Serial.begin(baud);

  Serial.println("Enter commands to send to the RS-232 device.");
  Serial.println();
}

void loop() {

  if (Serial.available() > 0) {
    String userInput = Serial.readStringUntil('\n');
    userInput.trim();  // remove any trailing newlines or spaces
    if (userInput.length() > 0) {
      // send the command with a telnet newline (CR + LF)
      rs232Serial.print(userInput + "\r\n");
      Serial.print("Sent: ");
      Serial.println(userInput);
    }
  }

  // check for incoming data from RS-232 device
  while (rs232Serial.available() > 0) {
    char response = rs232Serial.read();
    // print the incoming data
    Serial.print(response);
  }

  delay(50);
}
