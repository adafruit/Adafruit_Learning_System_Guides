// SPDX-FileCopyrightText: 2024 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*************************************************** 
  This is an example for the SHT4x Humidity & Temp Trinkey
 ****************************************************/

#include <Adafruit_SHT4x.h>
#include <Adafruit_NeoPixel.h>
#include <Adafruit_FreeTouch.h>


Adafruit_SHT4x sht4 = Adafruit_SHT4x();
Adafruit_NeoPixel pixel(1, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);
Adafruit_FreeTouch touch = Adafruit_FreeTouch(1, OVERSAMPLE_4, RESISTOR_50K, FREQ_MODE_NONE);

void setup() {
  Serial.begin(115200);
  
  pixel.begin(); // Initialize pins for output
  pixel.setBrightness(10);
  pixel.show();  // Turn off ASAP

  uint8_t i=0;
  while (!Serial) {
    // swirl the neopix while we wait
    pixel.setPixelColor(0, Wheel(i++));
    pixel.show();
    delay(10);     // will pause until serial console opens
  }
  pixel.setPixelColor(0, 0);
  pixel.show();

  if (! touch.begin())  
    Serial.println("Failed to begin QTouch on pin 1");
  
  Serial.println("# Adafruit SHT4x Trinkey Factory Test");
  if (! sht4.begin()) {
    Serial.println("# Couldn't find SHT4x");
    while (1) delay(1);
  }
  Serial.print("# Found SHT4x sensor. ");
  Serial.print("Serial number 0x");
  Serial.println(sht4.readSerial(), HEX);

  sht4.setPrecision(SHT4X_HIGH_PRECISION);  
  sht4.setHeater(SHT4X_NO_HEATER);
  Serial.println("# Serial number, Temperature in *C, Relative Humidity %, Touch");
}


void loop() {
  sensors_event_t humidity, temp;
  
  uint32_t timestamp = millis();
  sht4.getEvent(&humidity, &temp);// populate temp and humidity objects with fresh data
  timestamp = millis() - timestamp;

  Serial.print(sht4.readSerial());
  Serial.print(", ");
  Serial.print(temp.temperature);
  Serial.print(", ");
  Serial.print(humidity.relative_humidity);
  Serial.print(", ");
  Serial.println(touch.measure());
  
  // blink!
  pixel.setPixelColor(0, 0x0000FF);
  pixel.show();
  delay(25);
  pixel.setPixelColor(0, 0x0);
  pixel.show();

  // 1 second between readings
  delay(1000);  
}


// Input a value 0 to 255 to get a color value.
// The colours are a transition r - g - b - back to r.
uint32_t Wheel(byte WheelPos) {
  WheelPos = 255 - WheelPos;
  if(WheelPos < 85) {
    return pixel.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  }
  if(WheelPos < 170) {
    WheelPos -= 85;
    return pixel.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
  WheelPos -= 170;
  return pixel.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
}
