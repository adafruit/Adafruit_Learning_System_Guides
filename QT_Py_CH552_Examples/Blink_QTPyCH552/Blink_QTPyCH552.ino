// SPDX-FileCopyrightText: 2024 ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#define NEOPIXEL_PIN 10
#define A0 11
#define A1 14
#define A2 15
#define MOSI A2
#define MISO 16
#define SCK 17
#define RX 30
#define TX 31
#define A3 32
#define SCL 33
#define SDA 34

int led = MISO;

void setup() {
  pinMode(led, OUTPUT);
}

void loop() {
  digitalWrite(led, HIGH);   // turn the LED on (HIGH is the voltage level)
  delay(1000);               // wait for a second
  digitalWrite(led, LOW);    // turn the LED off by making the voltage LOW
  delay(1000);               // wait for a second
}
