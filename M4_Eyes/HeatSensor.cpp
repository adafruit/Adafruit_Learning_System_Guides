// SPDX-FileCopyrightText: 2019 teejaydub for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#if 0 // Change to 1 to enable this code (referenced by user_watch.cpp)
// CORRESPONDING LINE IN user_watch.cpp MUST ALSO BE ENABLED!

/* Read the IR sensor and try to figure out where the heat is located. 
*/
#include "HeatSensor.h"

#include <Wire.h>
#include <Adafruit_AMG88xx.h>

Adafruit_AMG88xx amg;

float pixels[AMG88xx_PIXEL_ARRAY_SIZE];

void HeatSensor::setup()
{
    x = 0;
    y = 0;
    magnitude = 0;

    bool status;
    
    // default settings
    status = amg.begin();
    if (!status) {
        Serial.println("Could not find a valid AMG88xx sensor, check wiring!");
        while (1);
    }

    yield();
    delay(100); // let sensor boot up
}

// Find the approximate X and Y values of the peak temperature in the pixel array,
// along with the magnitude of the brightest spot.
void HeatSensor::find_focus()
{
    amg.readPixels(pixels);
    yield();

    x = 0, y = 0, magnitude = 0;
    float minVal = 100, maxVal = 0;
    int i = 0;
    for (float yPos = 3.5; yPos > -4; yPos -= 1.0) {
        for (float xPos = 3.5; xPos > -4; xPos -= 1.0) {
            float p = pixels[i];
            x += xPos * p;
            y += yPos * p;
            minVal = min(minVal, p);
            maxVal = max(maxVal, p);
            i++;
        }
    }
    x = - x / AMG88xx_PIXEL_ARRAY_SIZE / 5.0;
    y = y / AMG88xx_PIXEL_ARRAY_SIZE / 5.0;
    x = max(-1.0, min(1.0, x));
    y = max(-1.0, min(1.0, y));
    magnitude = max(0, min(50, maxVal - 20));

    // Report.
#define SERIAL_OUT  3
#if SERIAL_OUT == 1
    // Print raw values
    Serial.print("[");
    for(int i=1; i<=AMG88xx_PIXEL_ARRAY_SIZE; i++){
      Serial.print(pixels[i-1]);
      Serial.print(", ");
      if( i%8 == 0 ) Serial.println();
    }
    Serial.println("]");
    Serial.println();
#endif
#if SERIAL_OUT == 2
    // Print character-graphic array
    const char charPixels[] = " .-*o0#";
    Serial.println("========");
    for (int i = 1; i <= AMG88xx_PIXEL_ARRAY_SIZE; i++) {
      int val = min(5, round(max(0, pixels[i-1] - 20) / 2));
      Serial.print(charPixels[val]);
      if (i % 8 == 0) 
        Serial.println();
    }
    Serial.println();
#endif
#if SERIAL_OUT == 3 || SERIAL_OUT == 2
    // Print coordinates and brightness
    Serial.print(x);
    Serial.print(' ');
    Serial.print(y);
    Serial.print(' ');
    Serial.println(magnitude);
#endif
}

/*
void loop() {
    // Read all the pixels

    // Find the focal point.
    float x, y, magnitude;
    find_focus(x, y, magnitude);

    // Set diagnostic LEDs.
    analogWrite(CENTER_LED, round(max(0, magnitude / 30) * 255));
    analogWrite(RIGHT_LED, round(min(1.0, max(0.0, -x / 3)) * 255));
    analogWrite(LEFT_LED, round(min(1.0, max(0.0, x / 3)) * 255));
    analogWrite(UP_LED, round(min(1.0, max(0.0, y / 3)) * 255));
    analogWrite(DOWN_LED, round(min(1.0, max(0.0, -y / 3)) * 255));

    delay(200);
}
*/
#endif
