#if 1 // Change to 0 to disable this code (must enable ONE user*.cpp only!)

#include "globals.h"

// This file provides a crude way to "drop in" user code to the eyes,
// allowing concurrent operations without having to maintain a bunch of
// special derivatives of the eye code (which is still undergoing a lot
// of development). Just replace the source code contents of THIS TAB ONLY,
// compile and upload to board. Shouldn't need to modify other eye code.

// User globals can go here, recommend declaring as static, e.g.:
// static int foo = 42;

const int sampleWindow = 400; // Sample window width in mS (50 mS = 20Hz)

unsigned long end_millis= 0;  // Start of sample window

unsigned int left_max = 0;
unsigned int left_min = 1024;

unsigned int right_max = 0;
unsigned int right_min = 1024;

unsigned int sample_count = 0;
unsigned int sample;
unsigned int peakToPeak;
double volts;



// Called once near the end of the setup() function. If your code requires
// a lot of time to initialize, make periodic calls to yield() to keep the
// USB mass storage filesystem alive.
void user_setup(void) {
  end_millis = millis() + sampleWindow;
}

// Called periodically during eye animation. This is invoked in the
// interval before starting drawing on the last eye (left eye on MONSTER
// M4SK, sole eye on HalloWing M0) so it won't exacerbate visible tearing
// in eye rendering. This is also SPI "quiet time" on the MONSTER M4SK so
// it's OK to do I2C or other communication across the bridge.
// This function BLOCKS, it does NOT multitask with the eye animation code,
// and performance here will have a direct impact on overall refresh rates,
// so keep it simple. Avoid loops (e.g. if animating something like a servo
// or NeoPixels in response to some trigger) and instead rely on state
// machines or similar. Additionally, calls to this function are NOT time-
// constant -- eye rendering time can vary frame to frame, so animation or
// other over-time operations won't look very good using simple +/-
// increments, it's better to use millis() or micros() and work
// algebraically with elapsed times instead.
void user_loop(void) {
/*
  Suppose we have a global bool "animating" (meaning something is in
  motion) and global uint32_t's "startTime" (the initial time at which
  something triggered movement) and "transitionTime" (the total time
  over which movement should occur, expressed in microseconds).
  Maybe it's servos, maybe NeoPixels, or something different altogether.
  This function might resemble something like (pseudocode):

  if(!animating) {
    Not in motion, check sensor for trigger...
    if(read some sensor) {
      Motion is triggered! Record startTime, set transition
      to 1.5 seconds and set animating flag:
      startTime      = micros();
      transitionTime = 1500000;
      animating      = true;
      No motion actually takes place yet, that will begin on
      the next pass through this function.
    }
  } else {
    Currently in motion, ignore trigger and move things instead...
    uint32_t elapsed = millis() - startTime;
    if(elapsed < transitionTime) {
      Part way through motion...how far along?
      float ratio = (float)elapsed / (float)transitionTime;
      Do something here based on ratio, 0.0 = start, 1.0 = end
    } else {
      End of motion reached.
      Take whatever steps here to move into final position (1.0),
      and then clear the "animating" flag:
      animating = false;
    }
  }
*/


  if (millis() >= end_millis) {
    // process the current sampling
    if (left_max > left_min && right_max > right_min) {

      // process left
      peakToPeak = left_max - left_min;  // max - min = peak-peak amplitude
      volts = (peakToPeak * 5.0) / 1024;  // convert to volts
      Serial.print("Left: ");
      Serial.println(volts);
      if (volts > 1.0) {
        Serial.println("I hear you on the left");
      }
      // process right
      peakToPeak = right_max - right_min;  // max - min = peak-peak amplitude
      volts = (peakToPeak * 5.0) / 1024;  // convert to volts
      Serial.print("Right ");
      Serial.println(volts);
      if (volts > 1.0) {
        Serial.println("I hear you on the right");
      }
    } else {
      Serial.print("Not enough sampling: ");
      Serial.println(sample_count);
    }
    // and reset for the next sampling
    right_max = left_max = 0;
    right_min = left_min = 1024;
    end_millis = millis() + sampleWindow;
    sample_count = 0;
  } else {
    for (int i = 5; i > 0; i--) {
      sample_count++;
      // sample left
      sample = analogRead(2);
      if (sample < 1024) { // toss out spurious readings
        if (sample > left_max) {
          left_max = sample;  // save just the max levels
        } else if (sample < left_min) {
          left_min = sample;  // save just the min levels
        }
      }
      // sample right
      sample = analogRead(3);
      if (sample < 1024) { // toss out spurious readings
        if (sample > right_max) {
          right_max = sample;  // save just the max levels
        } else if (sample < right_min) {
          right_min = sample;  // save just the min levels
        }
      }
    }
  }
}

#endif // 0
