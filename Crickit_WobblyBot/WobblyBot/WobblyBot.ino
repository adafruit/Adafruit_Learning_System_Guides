// Continuous servo based walking/waddling/etc robot.

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
#include "seesaw_servo.h"
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
// setup crickit

Adafruit_Crickit crickit;
seesaw_Servo legs[] = {seesaw_Servo(&crickit),
                       seesaw_Servo(&crickit),
                       seesaw_Servo(&crickit),
                       seesaw_Servo(&crickit)};

const int front_right = 0;
const int front_left = 1;
const int rear_right = 2;
const int rear_left = 3;

seesaw_Motor tail(&crickit);
float tail_power = 0.5;

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

//------------------------------------------------------------------------------
// Motor Control

// Left and right motors turn in the opposite direction
const float motor_directions[4] = {+1.0, -1.0, +1.0, -1.0};

// pins to connect each servo to
const int servo_pins[4] = {CRICKIT_SERVO1, CRICKIT_SERVO2, CRICKIT_SERVO3, CRICKIT_SERVO4};

// PWM ranges for each motor, tune these so that setting the angle to 90 stops the motor
int pwm_ranges[4][2] = {{500, 2400}, {500, 2400}, {500, 2400}, {500, 2400}};

const __FlashStringHelper *leg_names[] = {F("Front right"), F("Front left"), F("Rear right"), F("Rear left")};


int speed_to_angle(float speed)
{
  return (int)(speed * 90.0 + 90.0);
}


void set_leg(int leg, float speed)
{
  int angle = speed_to_angle(speed * motor_directions[leg]);
#ifdef DEBUG
  Serial.print(F("Setting "));
  Serial.print(leg_names[leg]);
  Serial.print(F(" to "));
  Serial.println(angle);
#endif
  legs[leg].write(angle);
}


// Stop the listed motors
// -1 required as the last argument

void stop(int leg, ...)
{
  va_list args;
  va_start(args, leg);
  log(F("Stop"));
  while (leg != -1) {
    set_leg(leg, 0.0);
    leg = va_arg(args, int);
  }

  va_end(args);
}


void stop_all()
{
  stop(front_right, front_left, rear_right, rear_left, -1);
}


void forward(float speed, ...)
{
  va_list args;
  va_start(args, speed);
  int leg = va_arg(args, int);
  log(F("Forward"));
  while (leg != -1) {
    set_leg(leg, speed * motor_directions[leg]);
    leg = va_arg(args, int);
  }

  va_end(args);
}


void forward_all(float speed)
{
  forward(speed, front_right, front_left, rear_right, rear_left, -1);
}


void reverse(float speed, ...)
{
  va_list args;
  va_start(args, speed);
  int leg = va_arg(args, int);
  log(F("Reverse"));
  while (leg != -1) {
    set_leg(leg, speed * -1 * motor_directions[leg]);
    leg = va_arg(args, int);
  }

  va_end(args);
}


void reverse_all(float speed)
{
  reverse(speed, front_right, front_left, rear_right, rear_left, -1);
}


void rotate_clockwise(float speed)
{
  forward(speed, front_left, rear_left, -1);
  reverse(speed, front_right, rear_right, -1);
}


void rotate_counterclockwise(float speed)
{
  forward(speed, front_right, rear_right, -1);
  reverse(speed, front_left, rear_left, -1);
}


void initialize()
{
  stop(front_right, front_left, rear_right, rear_left, -1);
}


void wag(float speed)
{
#ifdef DEBUG
  Serial.print(F("Wag "));
  Serial.println(speed);
#endif
  tail.throttle(speed);
  delay(75);
  tail.throttle(0.0);
  delay(50);
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

  log(F("WobblyBot"));
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

  for (int leg = 0; leg < 4; leg++) {
    legs[leg].attach(servo_pins[leg], pwm_ranges[leg][0], pwm_ranges[leg][1]);
  }

  tail.attach(CRICKIT_MOTOR_A1, CRICKIT_MOTOR_A2);
}


// Fill these functions in with the movement scripts you want attached to
// the controller's 1-4 buttons

void demo1()
{
  forward_all(0.5);
  delay(5000);
  rotate_clockwise(0.5);
  delay(2000);
  forward_all(0.75);
  delay(4000);
  rotate_counterclockwise(0.5);
  delay(3000);
  stop_all();
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
  wag(tail_power);
  tail_power *= -1.0;

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
        rotate_counterclockwise(0.5);
      } else {
        stop_all();
      }
      break;
    case 6:
      if (pressed) {
        rotate_clockwise(0.5);
      } else {
        stop_all();
      }
      break;
    case 7:
      if (pressed) {
        reverse_all(0.5);
      } else {
        stop_all();
      }
      break;
    case 8:
      if (pressed) {
        forward_all(0.5);
      } else {
        stop_all();
      }
      break;
    }
  }
}
