// SPDX-FileCopyrightText: 2025 John Park and Tod Kurt
//
// SPDX-License-Identifier: MIT

// Use a DMX controller to drive NeoPixel strips
// Arduino Uno or Metro 328 + Conceptinetics DMX Shield
// Recieves incoming DMX messages from controller, translates to NeoPixel

// MIDIHost2Host -- Connect two USB-MIDI host devices together
// 2019 @todbot / Tod E. Kurt
// 2025 @johnedgarpark / John E. Park
 // This sketch is meant to be installed on two Adafruit QT Py RP2040s.
// The connections between the two QT Py RP2040s are
// QTPyA Gnd ----- QTPyB Gnd
// QTPyA TX  ----- QTPyB RX
// QTPyA RX  ----- QTPyB TX
// except it's done w PIO over the stemma qt cable (remove red wire first)

  
//  When compiling:
// Install libraries: Adafruit_TinyUSB & MIDI
// Be sure to have updated all boards and libraries
// Select "Tools" -> "USB Stack" -> "TinyUSB"

// The following libraries are required:
// Adafruit_TinyUSB library by Adafruit
// https://github.com/adafruit/Adafruit_TinyUSB_Arduino
// MIDI Library by Forty Seven Effects
// https://github.com/FortySevenEffects/arduino_midi_library


#include <Arduino.h>
#include <Adafruit_TinyUSB.h>
#include <MIDI.h>
#include <Adafruit_NeoPixel.h>

// Adjust these for flashing the two different boards either "red" or "blue"
#define RED_BOARD  
// #define BLUE_BOARD



// Color definitions
uint32_t RED = 0xCC0000;
uint32_t DIM_RED = 0x3F0000;  // 25% brightness red
uint32_t GREEN = 0x00DD00;
uint32_t BLUE = 0x0000CC;
uint32_t DIM_BLUE = 0x00003F;  // 25% brightness blue
uint32_t YELLOW = 0xAAAA00;
char mfgstr[32] = "Lars Productions";
#ifdef RED_BOARD
  char prodstr[32] = "QTHost2 Red";
  uint32_t LED_COLOR = RED;  
  uint32_t LED_DIM_COLOR = DIM_RED;  
  SerialPIO pioserial(23, 22);
#else
  char prodstr[32] = "QTHost2 Blue";
  uint32_t LED_COLOR = BLUE;
  uint32_t LED_DIM_COLOR = DIM_BLUE;
  SerialPIO pioserial(22, 23);
#endif


// NeoPixel settings
#define NUM_PIXELS 1

// NeoPixel RGB LED
Adafruit_NeoPixel pixels = Adafruit_NeoPixel(NUM_PIXELS, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

bool led_on = false;
uint32_t led_time;
uint32_t led_on_time = 50; // how long LED should blink
uint32_t last_color = LED_DIM_COLOR; // Track last active color

// USB MIDI object
Adafruit_USBD_MIDI usb_midi;

// Create instance of Arduino MIDI library,
// and attach usb_midi as the transport.
// MIDI_CREATE_INSTANCE(Adafruit_USBD_MIDI, usb_midi, midiA);
MIDI_CREATE_INSTANCE(Adafruit_USBD_MIDI, usb_midi, midiA);

// Create instance of Arduino MIDI library,
// and attach HardwareSerial Serial1 (TrinketM0 pins 3 & 4 or TX/RX on a QT Py, this is automatic)
MIDI_CREATE_INSTANCE(HardwareSerial, pioserial, midiB);


void setup()
{


  #if defined(NEOPIXEL_POWER)
    // If this board has a power control pin, we must set it to output and high
    // in order to enable the NeoPixels. We put this in an #if defined so it can
    // be reused for other boards without compilation errors
    pinMode(NEOPIXEL_POWER, OUTPUT);
    digitalWrite(NEOPIXEL_POWER, HIGH);
  #endif
 pixels.begin();
 pixels.setBrightness(60);
 set_pixel(YELLOW);

 USBDevice.setManufacturerDescriptor(mfgstr);
 USBDevice.setProductDescriptor     (prodstr);
 
 // Initialize MIDI, and listen to all MIDI channels
 // This will also call usb_midi's and Serial1's begin()
 midiA.begin(MIDI_CHANNEL_OMNI);
 midiB.begin(MIDI_CHANNEL_OMNI);

 midiA.turnThruOff();
 midiB.turnThruOff();

//  Serial.begin(115200);

 // wait until device mounted
 while ( !USBDevice.mounted() ) delay(1);
 set_pixel(LED_COLOR);
}

void loop()
{
 // read any new MIDI messages
 if ( midiA.read() ) {
   midiB.send(midiA.getType(),
              midiA.getData1(),
              midiA.getData2(),
              midiA.getChannel());
   last_color = LED_DIM_COLOR;  // Update last color to red
   pixel_on(LED_COLOR);
   //  Serial.println("midiA");
 }
 
 if ( midiB.read() ) {
   midiA.send(midiB.getType(),
              midiB.getData1(),
              midiB.getData2(),
              midiB.getChannel());
   last_color = LED_DIM_COLOR;  // Update last color to blue
   pixel_on(LED_COLOR);
   //  Serial.println("midiB");
 }
 
 pixel_check();
}

void pixel_check() {
 if( led_on && (millis() - led_time) > led_on_time ) { 
   led_on = false; 
   set_pixel(last_color);  // Return to dimmed version of last active color
 }
}

void pixel_on(uint32_t color) { 
 set_pixel(color);
 led_on = true;
 led_time = millis();
}

void set_pixel(uint32_t color) {
 pixels.setPixelColor(0, color);
 pixels.show();
}