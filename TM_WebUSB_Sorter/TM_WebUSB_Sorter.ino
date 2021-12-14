// SPDX-FileCopyrightText: 2020 Limor Fried/ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/* This sketch demonstrates WebUSB as web serial with browser with WebUSB support (e.g Chrome).
 * For use with the Teachable Machine Tiny Sorter (and others!) project
 * See https://learn.adafruit.com/using-webusb-with-arduino-and-tinyusb for
 * software installation instructions and then
 * https://learn.adafruit.com/machine-learning-with-marshmallows-and-tiny-sorter
 * for usage tutorial
 * 
 * Targetted to work with Circuit Playground Express but will work with any
 * board that has TinyUSB support - don't forget to select TinyUSB in the Tools menu!
 */

#include <Servo.h>
#include <Adafruit_NeoPixel.h>
#include "Adafruit_TinyUSB.h"

// Which pin on the CPX/board is the Servo connected to?
#define SERVO_PIN A1
Servo myservo;

// Use internal neopixel ring
#define NEOPIX_PIN 8
#define NUMPIXELS  10
Adafruit_NeoPixel pixels = Adafruit_NeoPixel(NUMPIXELS, NEOPIX_PIN, NEO_GRB + NEO_KHZ800);

// USB WebUSB object
Adafruit_USBD_WebUSB usb_web;

// Landing Page: scheme (0: http, 1: https), url
WEBUSB_URL_DEF(landingPage, 1 /*https*/, "learn.adafruit.com/machine-learning-with-marshmallows-and-tiny-sorter");

// the setup function runs once when you press reset or power the board
void setup()
{
  usb_web.begin();
  usb_web.setLandingPage(&landingPage);
  usb_web.setLineStateCallback(line_state_callback);

  Serial.begin(115200);

  // This initializes the NeoPixel with RED
  pixels.begin();
  pixels.setBrightness(20);
  pixels.fill(0x0F0F0F); // dim white
  pixels.show();

  // wait until device mounted
  while( !USBDevice.mounted() ) delay(1);
  pixels.fill(0x0F0F00); // dim yellow
  pixels.show();
  
  Serial.println("TinyUSB WebUSB RGB example");
  usb_web.print("Sketch begins.\r\n");
  usb_web.flush();
  pinMode(LED_BUILTIN, OUTPUT);

  myservo.attach(SERVO_PIN);
  myservo.write(60);  
}


void loop()
{
  if ( usb_web.available()) {
    digitalWrite(LED_BUILTIN, HIGH);
    Serial.print("-> ");
    char val = usb_web.read();
    digitalWrite(LED_BUILTIN, LOW);
    Serial.print("Read value: "); Serial.println(val, DEC);

    if (val == 1) {    // Target bin #1
       pixels.fill(0xFFFF00);
       pixels.show();
       Serial.println("CEREAL!");

       myservo.write(0);        // push cereal to one side
       delay(2000);             // wait
       for (int pos = 0; pos <= 75; pos++) {  // return servo
          myservo.write(pos);
          delay(5);
       }
       delay(1000);          // another wait before we continue

    } else if (val == 2) {    // Target bin #2
       pixels.fill(0xFF000FF);
       pixels.show();
       Serial.println("MALLOW!");

       myservo.write(180);      // push mallows to other side
       delay(2000);             // wait
       for (int pos = 180; pos >= 75; pos--) {  // return servo
          myservo.write(pos);
          delay(5);
       }
       delay(1000);          // another wait before we continue
    }
    pixels.fill(0);
    pixels.show();

    while (usb_web.available()) {
      usb_web.read();
      delay(10);
    }
  } else {
    // no webserial data, tick tock the servo
    for (int pos = 60; pos <= 90; pos++) { // slowly goes from 60 degrees to 90 degrees
      myservo.write(pos);
      delay(3);
    }
    for (int pos = 90; pos >= 60; pos--) { // goes back to 60
      myservo.write(pos);
      delay(3);
    }
  }
}

void line_state_callback(bool connected)
{
  // connected = green, disconnected = red
  pixels.fill(connected ? 0x00ff00 : 0xff0000);
  pixels.show();
}
