// SPDX-FileCopyrightText: 2024 John Park for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Use a DMX controller to drive NeoPixel strips
// Arduino Uno or Metro 328 + Conceptinetics DMX Shield
// Recieves incoming DMX messages from controller, translates to NeoPixel


#include "Conceptinetics/Conceptinetics.h"
#include <Adafruit_NeoPixel.h>

// User adjust these for the number of strips, pins, pixels per strip, and color formats:
#define NUM_STRIPS 3
const int pin_for_strip[] = {A0, A1, A2};
const int leds_per_strip[] = {30, 20, 30};
const neoPixelType format_per_strip[] = {NEO_GRB + NEO_KHZ800, NEO_BGR + NEO_KHZ800, NEO_GRB + NEO_KHZ800 };

#define CH_PER_STRIP 16  // only 4 used per strip, but 16 is nicer on UI of controllers that have 16 channel/page
#define DMX_CHANNELS   (CH_PER_STRIP * NUM_STRIPS) 

const int ledPin = 13;

Adafruit_NeoPixel *strips[NUM_STRIPS];

DMX_Slave dmx_slave ( DMX_CHANNELS ); // Configure a DMX receiving controller
uint16_t channelValues[DMX_CHANNELS];  // Array to store DMX values


void setup() {      
  // Set led pin as output pin
    pinMode ( ledPin, OUTPUT );
    digitalWrite(ledPin, HIGH);

  // set up strips
  for(int i=0; i< NUM_STRIPS; i++) {  
    int pin = pin_for_strip[i];
    int num_leds  =  leds_per_strip[i];
    int format = format_per_strip[i];
    Adafruit_NeoPixel *strip = new Adafruit_NeoPixel(num_leds, pin, format);
    strips[i] = strip;
    strips[i]->begin();
  }       
    // light up all the strips RGB to test
  for(int i=0; i< NUM_STRIPS; i++) { 
    strips[i]->fill(0xff0000);
    strips[i]->show();
    delay(1000);
    strips[i]->fill(0x00ff00);
    strips[i]->show();
    delay(1000);
    strips[i]->fill(0x0000ff);
    strips[i]->show();
  }
  delay(1000);

  // Enable DMX receiving interface and start receiving DMX data
  dmx_slave.enable ();  
  dmx_slave.setStartAddress (1);
}


void loop() 
{
  // Fetch all DMX channel values into the array
  for (int i = 0; i < DMX_CHANNELS; i++) {
      channelValues[i] = dmx_slave.getChannelValue(i + 1);  // Get values starting from channel 1
  }

  for(int i=0; i<NUM_STRIPS; i++){
    //remap some channels for specific value ranges
    uint16_t strip_hue1 = map(channelValues[0 + (i * CH_PER_STRIP)], 0, 255, 0, 65535);
    uint16_t strip_hue2 = map(channelValues[4 + (i * CH_PER_STRIP)], 0, 255, 0, 65535);
    uint16_t strip_pix1 = map(channelValues[3 + (i * CH_PER_STRIP)], 0, 255, 0, leds_per_strip[i] - 1);
    uint16_t strip_pix2 = map(channelValues[7 + (i * CH_PER_STRIP)], 0, 255, 0, leds_per_strip[i] - 1);

    strips[i]->fill(0x000000);
    strips[i]->setPixelColor(strip_pix1, strips[i]->ColorHSV(strip_hue1, channelValues[1+(i*CH_PER_STRIP)], channelValues[2+(i*CH_PER_STRIP)]));  //first pixel
    strips[i]->setPixelColor(strip_pix2, strips[i]->ColorHSV(strip_hue2, channelValues[5+(i*CH_PER_STRIP)], channelValues[6+(i*CH_PER_STRIP)]));  //last pixel
    // all the pixels in between
    for (int j = strip_pix1; j <= strip_pix2; j++) {  
      float fraction = float(j - strip_pix1) / float(strip_pix2 - strip_pix1); // Calculate the fraction of the interpolation (0 to 1)
      // Interpolate HSV components (Hue, Saturation, Value)
      uint16_t interpolated_hue = int(lerp(strip_hue1, strip_hue2, fraction)) % 65536;  // Wrap around Hue
      uint16_t interpolated_saturation = lerp(channelValues[1+(i*CH_PER_STRIP)], channelValues[5+(i*CH_PER_STRIP)], fraction);
      uint16_t interpolated_value = lerp(channelValues[2+(i*CH_PER_STRIP)], channelValues[6+(i*CH_PER_STRIP)], fraction);

    // Set the interpolated color to the pixel
      strips[i]->setPixelColor(j, strips[i]->ColorHSV(interpolated_hue, interpolated_saturation, interpolated_value));
    }
  }

  for(int i=0; i<NUM_STRIPS; i++){
    strips[i]->show();
  }

  delay(100);
}

// Linear interpolation function
float lerp(float start, float end, float t) {
  return start + (end - start) * t;
}
