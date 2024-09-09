// SPDX-FileCopyrightText: 2023 Carter Nelson for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_TestBed.h>
extern Adafruit_TestBed TB;

#define DEFAULT_I2C_PORT &Wire

// Some boards have TWO I2C ports, how nifty. We should scan both
#if defined(ARDUINO_ARCH_RP2040) \
    || defined(ARDUINO_ADAFRUIT_QTPY_ESP32S2) \
    || defined(ARDUINO_ADAFRUIT_QTPY_ESP32S3_NOPSRAM) \
    || defined(ARDUINO_ADAFRUIT_QTPY_ESP32S3) \
    || defined(ARDUINO_ADAFRUIT_QTPY_ESP32_PICO) \
    || defined(ARDUINO_SAM_DUE) \
    || defined(ARDUINO_ARCH_RENESAS_UNO)
  #define SECONDARY_I2C_PORT &Wire1
#endif

void setup() {
  Serial.begin(115200);

  // Wait for Serial port to open
  while (!Serial) {
    delay(10);
  }
  delay(500);
  Serial.println("Adafruit I2C Scanner");

#if defined(ARDUINO_ADAFRUIT_QTPY_ESP32S2) || \
    defined(ARDUINO_ADAFRUIT_QTPY_ESP32S3_NOPSRAM) || \
    defined(ARDUINO_ADAFRUIT_QTPY_ESP32S3) || \
    defined(ARDUINO_ADAFRUIT_QTPY_ESP32_PICO)
  // ESP32 is kinda odd in that secondary ports must be manually
  // assigned their pins with setPins()!
  Wire1.setPins(SDA1, SCL1);
#endif

#if defined(ARDUINO_ADAFRUIT_FEATHER_ESP32S2)
  // turn on the I2C power by setting pin to opposite of 'rest state'
  pinMode(PIN_I2C_POWER, INPUT);
  delay(1);
  bool polarity = digitalRead(PIN_I2C_POWER);
  pinMode(PIN_I2C_POWER, OUTPUT);
  digitalWrite(PIN_I2C_POWER, !polarity);
#endif

#if defined(ARDUINO_ADAFRUIT_FEATHER_ESP32S2_TFT)
  pinMode(TFT_I2C_POWER, OUTPUT);
  digitalWrite(TFT_I2C_POWER, HIGH);
#endif

#if defined(ARDUINO_ADAFRUIT_FEATHER_ESP32S2_REVTFT)
  pinMode(TFT_I2C_POWER, OUTPUT);
  digitalWrite(TFT_I2C_POWER, HIGH);
#endif

#if defined(ADAFRUIT_FEATHER_ESP32_V2)
  // Turn on the I2C power by pulling pin HIGH.
  pinMode(NEOPIXEL_I2C_POWER, OUTPUT);
  digitalWrite(NEOPIXEL_I2C_POWER, HIGH);
#endif
}

void loop() {
  Serial.println("");
  Serial.println("");

  Serial.print("Default port (Wire) ");
  TB.theWire = DEFAULT_I2C_PORT;
  TB.printI2CBusScan();

#if defined(SECONDARY_I2C_PORT)
  Serial.print("Secondary port (Wire1) ");
  TB.theWire = SECONDARY_I2C_PORT;
  TB.printI2CBusScan();
#endif

  delay(3000); // wait 3 seconds
}
