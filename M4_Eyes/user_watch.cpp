// SPDX-FileCopyrightText: 2019 teejaydub for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#if 0 // Change to 1 to enable this code (must enable ONE user*.cpp only!)
// CORRESPONDING LINE IN HeatSensor.cpp MUST ALSO BE ENABLED!

#include "globals.h"
#include "heatSensor.h"

// For heat sensing
HeatSensor heatSensor;

// This file provides a crude way to "drop in" user code to the eyes,
// allowing concurrent operations without having to maintain a bunch of
// special derivatives of the eye code (which is still undergoing a lot
// of development). Just replace the source code contents of THIS TAB ONLY,
// compile and upload to board. Shouldn't need to modify other eye code.

// User globals can go here, recommend declaring as static, e.g.:
// static int foo = 42;

// Called once near the end of the setup() function. If your code requires
// a lot of time to initialize, make periodic calls to yield() to keep the
// USB mass storage filesystem alive.
void user_setup(void) {
  showSplashScreen = false;
  moveEyesRandomly = false;
  heatSensor.setup();
}

// Called periodically during eye animation. This is invoked in the
// interval before starting drawing on the last eye (left eye on MONSTER
// M4SK, sole eye on HalloWing M0) so it won't exacerbate visible tearing
// in eye rendering. This is also SPI "quiet time" on the MONSTER M4SK so
// it's OK to do I2C or other communication across the bridge.
void user_loop(void) {
  // Estimate the focus position.
  heatSensor.find_focus();

  // Set values for the new X and Y.
  eyeTargetX = heatSensor.x;
  eyeTargetY = -heatSensor.y;
}

#endif // 0
