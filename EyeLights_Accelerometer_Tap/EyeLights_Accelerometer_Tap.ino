/*
ACCELEROMETER INPUT DEMO: while the LED Glasses Driver has a perfectly
good clicky button for input, this code shows how one might instead use
the onboard accelerometer for interactions*.

Worn normally, the LED rings are simply lit a solid color.
TAP the eyeglass frames to cycle among a list of available colors.
LOOK DOWN to light the LED rings bright white -- for navigating steps
or finding the right key. LOOK BACK UP to return to solid color.
This uses only the rings, not the matrix portion.

* Like, if you have big ol' monster hands, that little button can be
  hard to click, y'know?
*/

#include <Adafruit_IS31FL3741.h> // For LED driver
#include <Adafruit_LIS3DH.h>     // For accelerometer
#include <Adafruit_Sensor.h>     // For m/s^2 accel units

Adafruit_LIS3DH             accel;
Adafruit_EyeLights_buffered glasses; // Buffered for smooth animation

// Here's a list of colors that we cycle through when tapped, specified
// as {R,G,B} values from 0-255. These are intentionally a bit dim --
// both to save battery and to make the "ground light" mode more dramatic.
// Rather than primary color red/green/blue sequence which is just so
// over-done at this point, let's use some HALLOWEEN colors!
uint8_t colors[][3] = {
  {27, 9, 0},  // Orange
  {12, 0, 24}, // Purple
  {5, 31, 0},  // Green
};
#define NUM_COLORS (sizeof colors / sizeof colors[0]) // List length
uint8_t looking_down_color[] = {255, 255, 255};       // Max white

uint8_t  color_index = 0;   // Begin at first color in list
uint8_t *target_color;      // Pointer to color we're aiming for
float    interpolated_color[] = {0.0, 0.0, 0.0}; // Current color along the way
float    filtered_y;        // De-noised accelerometer reading
bool     looking_down;      // Set true when glasses are oriented downward
sensors_event_t event;      // For accelerometer conversion
uint32_t last_tap_time = 0; // For accelerometer tap de-noising

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

  // Configure accelerometer and get initial state
  accel.setClick(1, 100); // Set threshold for single tap
  accel.getEvent(&event); // Current accel in m/s^2
  // Check accelerometer to see if we've started in the looking-down state,
  // set the target color (what we're aiming for) appropriately. Only the
  // Y axis is needed for this.
  filtered_y = event.acceleration.y;
  looking_down = (filtered_y > 5.0);
  // If initially looking down, aim for the look-down color,
  // else aim for the first item in the color list.
  target_color = looking_down ? looking_down_color : colors[color_index];

  // Configure glasses for max brightness, enable output
  glasses.setLEDscaling(0xFF);
  glasses.setGlobalCurrent(0xFF);
  glasses.enable(true);
}

void loop() { // Repeat forever...

  // interpolated_color blends from the prior to the next ("target")
  // LED ring colors, with a pleasant ease-out effect.
  for(uint8_t i=0; i<3; i++) { // R, G, B
    interpolated_color[i] = interpolated_color[i] * 0.97 + target_color[i] * 0.03;
  }
  // Convert separate red, green, blue to "packed" 24-bit RGB value
  uint32_t rgb = ((int)interpolated_color[0] << 16) |
                 ((int)interpolated_color[1] << 8) |
                  (int)interpolated_color[2];
  // Fill both rings with packed color, then refresh the LEDs.
  glasses.left_ring.fill(rgb);
  glasses.right_ring.fill(rgb);
  glasses.show();

  // The look-down detection only needs the accelerometer's Y axis.
  // This works with the Glasses Driver mounted on either temple,
  // with the glasses arms "open" (as when worn).
  accel.getEvent(&event);
  // Smooth the accelerometer reading the same way RGB colors are
  // interpolated. This avoids false triggers from jostling around.
  filtered_y = filtered_y * 0.97 + event.acceleration.y * 0.03;

  // The threshold between "looking down" and "looking up" depends
  // on which of those states we're currently in. This is an example
  // of hysteresis in software...a change of direction requires a
  // little extra push before it takes, which avoids oscillating if
  // there was just a single threshold both ways.
  if (looking_down) {       // Currently in the looking-down state...
    (void)accel.getClick(); // Discard any taps while looking down
    if (filtered_y < 3.5) { // Have we crossed the look-up threshold?
      target_color = colors[color_index]; // Back to list color
      looking_down = false;               // We're looking up now!
    }
  } else {                  // Currently in the looking-up state...
    if (filtered_y > 5.0) { // Crossed the look-down threshold?
      target_color = looking_down_color; // Aim for white
      looking_down = true;               // We're looking down now!
    } else if (accel.getClick()) {
      // No look up/down change, but the accelerometer registered
      // a tap. Compare this against the last time we sensed one,
      // and only do things if it's been more than half a second.
      // This avoids spurious double-taps that can occur no matter
      // how carefully the tap threshold was set.
      uint32_t now = millis();
      uint32_t elapsed = now - last_tap_time;
      if (elapsed > 500) {
        // A good tap was detected. Cycle to the next color in
        // the list and note the time of this tap.
        color_index = (color_index + 1) % NUM_COLORS;
        target_color = colors[color_index];
        last_tap_time = now;
      }
    }
  }
}
