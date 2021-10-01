/*
GOOGLY EYES for Adafruit EyeLight LED glasses + driver. Pendulum physics
simulation using accelerometer and math. This uses only the rings, not the
matrix portion. Adapted from Bill Earl's STEAM-Punk Goggles project:
https://learn.adafruit.com/steam-punk-goggles
*/

#include <Adafruit_IS31FL3741.h> // For LED driver
#include <Adafruit_LIS3DH.h>     // For accelerometer
#include <Adafruit_Sensor.h>     // For m/s^2 accel units

Adafruit_LIS3DH             accel;
Adafruit_EyeLights_buffered glasses; // Buffered for smooth animation

// A small class for our pendulum simulation.
class Pendulum {
public:
  // Constructor. Pass pointer to EyeLights ring, and a 3-byte color array.
  Pendulum(Adafruit_EyeLights_Ring_buffered *r, uint8_t *c) {
    ring  = r;
    color = c;
    // Initial pendulum position, plus axle friction, are randomized
    // so rings don't spin in perfect lockstep.
    angle = random(1000);
    momentum = 0.0;
    friction = 0.94 + random(300) * 0.0001; // Inverse friction, really
  }

  // Given a pixel index (0-23) and a scaling factor (0.0-1.0),
  // interpolate between LED "off" color (at 0.0) and this item's fully-
  // lit color (at 1.0) and set pixel to the result.
  void interp(uint8_t pixel, float scale) {
    // Convert separate red, green, blue to "packed" 24-bit RGB value
    ring->setPixelColor(pixel,
        (int(color[0] * scale) << 16) |
        (int(color[1] * scale) <<  8) |
         int(color[2] * scale));
  }

  // Given an accelerometer reading, run one cycle of the pendulum
  // physics simulation and render the corresponding LED ring.
  void iterate(sensors_event_t &event) {
    // Minus here is because LED pixel indices run clockwise vs. trigwise.
    // 0.006 is just an empirically-derived scaling fudge factor that looks
    // good; smaller values for more sluggish rings, higher = more twitch.
    momentum =  momentum * friction - 0.006 *
      (cos(angle) * event.acceleration.z +
       sin(angle) * event.acceleration.x);
    angle += momentum;

    // Scale pendulum angle into pixel space
    float midpoint = fmodf(angle * 12.0 / M_PI, 24.0);

    // Go around the whole ring, setting each pixel based on proximity
    // (this is also to erase the prior position)...
    for (uint8_t i=0; i<24; i++) {
        float dist = fabs(midpoint - (float)i); // Pixel to pendulum distance...
        if (dist > 12.0)                   // If it crosses the "seam" at top,
            dist = 24.0 - dist;            //   take the shorter path.
        if (dist > 5.0)                    // Not close to pendulum,
            ring->setPixelColor(i, 0);     //   erase pixel.
        else if (dist < 2.0)               // Close to pendulum,
            interp(i, 1.0);                //   solid color
        else                               // Anything in-between,
            interp(i, (5.0 - dist) / 3.0); //   interpolate
    }
  }
private:
  Adafruit_EyeLights_Ring_buffered *ring; // -> glasses ring
  uint8_t *color;    // -> array of 3 uint8_t's [R,G,B]
  float    angle;    // Current position around ring
  float    momentum; // Current 'oomph'
  float    friction; // A scaling constant to dampen motion
};

Pendulum pendulums[] = {
    Pendulum(&glasses.left_ring, (uint8_t[3]){0, 20, 50}),  // Cerulean blue,
    Pendulum(&glasses.right_ring, (uint8_t[3]){0, 20, 50}), // 50 is plenty bright!
};
#define N_PENDULUMS (sizeof pendulums / sizeof pendulums[0])

// Crude error handler, prints message to Serial console, flashes LED
void err(char *str, uint8_t hz) {
  Serial.println(str);
  pinMode(LED_BUILTIN, OUTPUT);
  for (;;) digitalWrite(LED_BUILTIN, (millis() * hz / 500) & 1);
}

void setup() { // Runs once at program start...

  // Initialize hardware
  Serial.begin(115200);
  if (! accel.begin())   err("LIS3DH not found", 5);
  if (! glasses.begin()) err("IS3741 not found", 2);

  // Configure glasses for max brightness, enable output
  glasses.setLEDscaling(0xFF);
  glasses.setGlobalCurrent(0xFF);
  glasses.enable(true);
}

void loop() { // Repeat forever...
  sensors_event_t event;
  accel.getEvent(&event); // Read accelerometer once
  for (uint8_t i=0; i<N_PENDULUMS; i++) { // For each pendulum...
    pendulums[i].iterate(event);          // Do math with accel data
  }
  glasses.show();
}
