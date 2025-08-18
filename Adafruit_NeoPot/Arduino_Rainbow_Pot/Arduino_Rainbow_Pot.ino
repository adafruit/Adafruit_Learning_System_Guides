// SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_NeoPixel.h>
int sensorPin = A0;   // select the input pin for the potentiometer
int neoPixelPin = 4;      // select the pin for the LED
int sensorValue = 0;  // variable to store the value coming from the sensor

int readings[10];
size_t count = 0;

Adafruit_NeoPixel strip = Adafruit_NeoPixel(1, neoPixelPin, NEO_GRB + NEO_KHZ800);

// Insert an int value at index 0 of an int array, shifting all other elements up.
// If the array already contains 'maxCount' elements, the last one is dropped.
// 'count' is the number of valid elements currently stored in the array.
void insert(int arr[], size_t maxCount, int value, size_t &count){
    // Determine how many elements we need to shift (cannot exceed the array bounds)
    size_t shiftCount = (count < maxCount) ? count : maxCount - 1;

    // Shift elements up by one position
    for (size_t i = shiftCount; i > 0; --i) {
        arr[i] = arr[i - 1];
    }

    // Insert the new value at the beginning
    arr[0] = value;

    // Update the element count
    if (count < maxCount) {
        ++count;          // we added a new element
    } // else count stays the same – the last element was overwritten
}

// Input an array of 10 or fewer int's, and a count of how many have values
// Returns average of the values in the array.
int average(int arr[], size_t count){
  int sum = 0;
  for(int i = 0; i < 10; i++){
    sum = sum + arr[i];
  }
  return sum / count;
}

// Input a value 0 to 255 to get a color value.
// The colours are a transition r - g - b - back to r.
uint32_t Wheel(byte WheelPos) {
  WheelPos = 255 - WheelPos;
  if(WheelPos < 85) {
    return strip.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  }
  if(WheelPos < 170) {
    WheelPos -= 85;
    return strip.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
  WheelPos -= 170;
  return strip.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
}

void setup() {
  Serial.begin(115200);
  strip.begin();
}

void loop() {
  sensorValue = analogRead(sensorPin);
  insert(readings, 10, sensorValue, count);
  strip.setPixelColor(0, Wheel(average(readings, count) / 4));
  strip.show();
}
