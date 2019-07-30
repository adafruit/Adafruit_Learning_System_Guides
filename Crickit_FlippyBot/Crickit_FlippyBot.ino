// Triangular leg robot.

// Bluetooth code is from Feather M0 Bluefruit controller example.
// Explainatory comments kept intact.

// Adafruit invests time and resources providing this open source code.
// Please support Adafruit and open source hardware by purchasing
// products from Adafruit!

// Written by Dave Astels for Adafruit Industries
// Copyright (c) 2018 Adafruit Industries
// Licensed under the MIT license.

// All text above must be included in any redistribution.

#include <stdarg.h>
#include <string.h>
#include <Arduino.h>
#include <SPI.h>
#include "Adafruit_BLE.h"
#include "Adafruit_BluefruitLE_SPI.h"
#include "Adafruit_BluefruitLE_UART.h"

#include "BluefruitConfig.h"

#include "Adafruit_Crickit.h"
#include "seesaw_motor.h"

#define FACTORYRESET_ENABLE         1
#define MINIMUM_FIRMWARE_VERSION    "0.6.6"
#define MODE_LED_BEHAVIOUR          "MODE"

// function prototypes over in packetparser.cpp
uint8_t readPacket(Adafruit_BLE *ble, uint16_t timeout);
float parsefloat(uint8_t *buffer);
void printHex(const uint8_t * data, const uint32_t numBytes);

// the packet buffer
extern uint8_t packetbuffer[];

//#define DEBUG 1


Adafruit_BluefruitLE_SPI ble(BLUEFRUIT_SPI_CS, BLUEFRUIT_SPI_IRQ, BLUEFRUIT_SPI_RST);


//------------------------------------------------------------------------------
// setup crickit & motors

Adafruit_Crickit crickit;
seesaw_Motor right_leg(&crickit);
seesaw_Motor left_leg(&crickit);

seesaw_Motor *legs[2] = {&right_leg, &left_leg};
const __FlashStringHelper *leg_names[] = {F("right"), F("left")};

const int RIGHT = 0;
const int LEFT = 1;

//------------------------------------------------------------------------------
// conditional output routines

void error(const __FlashStringHelper *err)
{
  digitalWrite(13, HIGH);
#ifdef DEBUG
  Serial.println(err);
#endif
  while (1);
}


void log(const __FlashStringHelper *msg)
{
#ifdef DEBUG
  Serial.println(msg);
#endif
}



void set_leg(int leg, float velocity)
{
  if (leg != RIGHT && leg != LEFT) {
    error(F("Bad leg specifier"));
  }
  if (velocity < -1.0 || velocity > 1.0) {
    error(F("Velocity out of -1.0//1.0 range"));
  }

#ifdef DEBUG
  Serial.print(F("Setting "));
  Serial.print(leg_names[leg]);
  Serial.print(F(" to "));
  Serial.println(velocity);
#endif

  legs[leg]->throttle(velocity);
}


void stop()
{
  set_leg(RIGHT, 0.0);
  set_leg(LEFT, 0.0);
}


void forward(float speed)
{
  set_leg(RIGHT, speed);
  set_leg(LEFT, speed);
}


void reverse(float speed)
{
  set_leg(RIGHT, speed * -1);
  set_leg(LEFT, speed * -1);
}


void rotate_clockwise(float speed)
{
  set_leg(RIGHT, speed * -1);
  set_leg(LEFT, speed);
}


void rotate_counterclockwise(float speed)
{
  set_leg(RIGHT, speed);
  set_leg(LEFT, speed * -1);
}


void initialize()
{
  stop();
}


//------------------------------------------------------------------------------
// Start things up

void setup()
{
  pinMode(13, OUTPUT);
  digitalWrite(13, LOW);

#ifdef DEBUG
  while (!Serial);  // required for Flora & Micro
  delay(500);
  Serial.begin(115200);
#endif

  log(F("FlippyBot"));
  log(F("-----------------------------------------"));

  // Initialise the module
  log(F("Initialising the Bluefruit LE module: "));

  if ( !ble.begin(VERBOSE_MODE) )
  {
    error(F("Couldn't find Bluefruit, make sure it's in CoMmanD mode & check wiring?"));
  }

  log( F("OK!") );

  if ( FACTORYRESET_ENABLE )
  {
    // Perform a factory reset to make sure everything is in a known state
    log(F("Performing a factory reset: "));
    if ( ! ble.factoryReset() ){
      error(F("Couldn't factory reset"));
    }
  }

   // Disable command echo from Bluefruit
  ble.echo(false);

  log(F("Requesting Bluefruit info:"));
  // Print Bluefruit information
  ble.info();

  log(F("Please use Adafruit Bluefruit LE app to connect in Controller mode"));
  log(F("Then activate/use the sensors, color picker, game controller, etc!\n"));

  ble.verbose(false);  // debug info is a little annoying after this point!

  // Wait for connection
  while (! ble.isConnected()) {
      delay(500);
  }

  log(F("******************************"));

  // LED Activity command is only supported from 0.6.6
  if ( ble.isVersionAtLeast(MINIMUM_FIRMWARE_VERSION) )
  {
    // Change Mode LED Activity
    log(F("Change LED activity to " MODE_LED_BEHAVIOUR));
    ble.sendCommandCheckOK("AT+HWModeLED=" MODE_LED_BEHAVIOUR);
  }

  // Set Bluefruit to DATA mode
  log( F("Switching to DATA mode!") );
  ble.setMode(BLUEFRUIT_MODE_DATA);

  log(F("******************************"));

  if (!crickit.begin()) {
    error(F("Error initializing CRICKIT!"));
  }
  log(F("Crickit started"));

  right_leg.attach(CRICKIT_MOTOR_A1, CRICKIT_MOTOR_A2);
  left_leg.attach(CRICKIT_MOTOR_B1, CRICKIT_MOTOR_B2);
}


// Fill these functions in with the movement scripts you want attached to
// the controller's 1-4 buttons

void demo1()
{
  forward(1.0);
  delay(5000);
  rotate_clockwise(1.0);
  delay(2000);
  forward(0.75);
  delay(4000);
  rotate_counterclockwise(1.0);
  delay(3000);
  stop();
}


void demo2()
{
}


void demo3()
{
}


void demo4()
{
}


//------------------------------------------------------------------------------
// Main loop

void loop()
{
  // Wait for new data to arrive
  uint8_t len = readPacket(&ble, BLE_READPACKET_TIMEOUT);
  if (len == 0) return;

  // Got a packet!
  // printHex(packetbuffer, len);

   // Buttons
  if (packetbuffer[1] == 'B') {
    uint8_t buttnum = packetbuffer[2] - '0';
    boolean pressed = packetbuffer[3] - '0';

#ifdef DEBUG
    Serial.print ("Button "); Serial.print(buttnum);
    if (pressed) {
      Serial.println(" pressed");
    } else {
      Serial.println(" released");
    }
#endif
    switch(buttnum) {
    case 1:
      if (pressed) {
        demo1();
      }
      break;
    case 2:
      if (pressed) {
        demo2();
      }
      break;
    case 3:
      if (pressed) {
        demo3();
      }
      break;
    case 4:
      if (pressed) {
        demo4();
      }
      break;
    case 5:
      if (pressed) {
        forward(1.0);
      } else {
        stop();
      }
      break;
    case 6:
      if (pressed) {
        reverse(1.0);
      } else {
        stop();
      }
      break;
    case 7:
      if (pressed) {
        rotate_counterclockwise(1.0);
      } else {
        stop();
      }
      break;
    case 8:
      if (pressed) {
        rotate_clockwise(1.0);
      } else {
        stop();
      }
      break;
    }
  }
}
