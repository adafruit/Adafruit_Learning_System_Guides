// SPDX-FileCopyrightText: 2025 lady ada for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Stepper.h>

// change this to the number of steps on your motor
#define STEPS 200

// create an instance of the stepper class, specifying
// the number of steps of the motor and the pins it's
// attached to
Stepper stepper(STEPS, 4, 5, 6, 7);


void setup()
{
  Serial.begin(9600);
  Serial.println("Stepper test!");
  // set the speed of the motor to 30 RPMs
  stepper.setSpeed(60);
}

void loop()
{
  Serial.println("Forward");
  stepper.step(STEPS);
  Serial.println("Backward");
  stepper.step(-STEPS);
}
