// SPDX-FileCopyrightText: 2021 Phil Burgess for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*
MOVE-AND-BLINK EYES for Adafruit EyeLights (LED Glasses + Driver).

I'd written a very cool squash-and-stretch effect for the eye movement,
but unfortunately the resolution is such that the pupils just look like
circles regardless. I'm keeping it in despite the added complexity,
because LED matrix densities WILL improve, and this way the code won't
require a re-write at such a later time.
*/

#include <Adafruit_IS31FL3741.h> // For LED driver

// CONFIGURABLES ------------------------

#define RADIUS 3.4 // Size of pupil (3X because of downsampling later)

// Some boards have just one I2C interface, but some have more...
TwoWire *i2c = &Wire; // e.g. change this to &Wire1 for QT Py RP2040

Adafruit_EyeLights_buffered glasses(true); // Buffered + 3X canvas
GFXcanvas16 *canvas; // Pointer to canvas object

uint32_t frames = 0;
uint32_t start_time;

#define GAMMA 2.6

float y_pos[13];
// Initialize eye position and move/blink animation timekeeping
float cur_pos[2] = { 9.0, 7.5 };  // Current position of eye in canvas space
float next_pos[2] = { 9.0, 7.5 }; // Next position "
bool in_motion = false;           // true = eyes moving, False = eyes paused
uint8_t blink_state = 0;          // 0, 1, 2 = unblinking, closing, opening
uint32_t move_start_time = 0;
uint32_t move_duration = 0;
uint32_t blink_start_time = 0;
uint32_t blink_duration = 0;

float x_offset[2] = { 5.0, 31.0 };

uint16_t eye_color = glasses.color565(255, 128, 0);
//uint8_t eye_color[3] = { 255, 128, 0 };      // Amber pupils
uint8_t ring_open_color[3] = { 75, 75, 75 }; // Color of LED rings when eyes open
uint8_t ring_blink_color[3] = { 50, 25, 0 }; // Color of LED ring "eyelid" when blinking

// Pre-compute color of LED ring in fully open (unblinking) state
uint32_t ring_open_color_packed;


// Crude error handler, prints message to Serial console, flashes LED
void err(char *str, uint8_t hz) {
  Serial.println(str);
  pinMode(LED_BUILTIN, OUTPUT);
  for (;;) digitalWrite(LED_BUILTIN, (millis() * hz / 500) & 1);
}

// Given an [R,G,B] color, apply gamma correction, return packed RGB integer.
uint32_t gammify(uint8_t color[3]) {
  uint32_t rgb[3];
  for (uint8_t i=0; i<3; i++) {
    rgb[i] = uint32_t(pow((float)color[i] / 255.0, GAMMA) * 255 + 0.5);
  }
  return (rgb[0] << 16) | (rgb[1] << 8) | rgb[2];
}

// Given two [R,G,B] colors and a blend ratio (0.0 to 1.0), interpolate between
// the two colors and return a gamma-corrected in-between color as a packed RGB
// integer. No bounds clamping is performed on blend value, be nice.
uint32_t interp(uint8_t color1[3], uint8_t color2[3], float blend) {
  float inv = 1.0 - blend; // Weighting of second color
  uint8_t rgb[3];
  for(uint8_t i=0; i<3; i++) {
    rgb[i] = (int)((float)color1[i] * blend + (float)color2[i] * inv);
  }
  return gammify(rgb);
}


void setup() { // Runs once at program start...

  // Initialize hardware
  Serial.begin(115200);
  while(!Serial);
Serial.println("HEY!"); yield();
  if (! glasses.begin(IS3741_ADDR_DEFAULT, i2c)) err("IS3741 not found", 2);

  canvas = glasses.getCanvas();
  if (!canvas) err("Can't allocate canvas", 5);

Serial.println("A");
  i2c->setClock(1000000);

  // Configure glasses for reduced brightness, enable output
  glasses.setLEDscaling(0xFF);
  glasses.setGlobalCurrent(20);
  glasses.enable(true);
Serial.println("B"); yield();

  // INITIALIZE TABLES & OTHER GLOBALS ----

  // Pre-compute the Y position of 1/2 of the LEDs in a ring, relative
  // to the 3X canvas resolution, so ring & matrix animation can be aligned.
  for (uint8_t i=0; i<13; i++) {
    float angle = (float)i / 24.0 * M_PI * 2.0;
    y_pos[i] = 10.0 - cos(angle) * 12.0;
  }

  ring_open_color_packed = gammify(ring_open_color);
Serial.println("C"); yield();

  start_time = millis();
}

// Rasterize an arbitrary ellipse into the offscreen 3X canvas, given
// foci point1 and point2 and with area determined by global RADIUS
// (when foci are same point; a circle). Foci and radius are all
// floating point values, which adds to the buttery impression. 'rect'
// is a bounding rect of which pixels are likely affected. Canvas is
// assumed cleared before arriving here.
void rasterize(float point1[2], float point2[2], int rect[4]) {
  float perimeter, d;
  float dx = point2[0] - point1[0];
  float dy = point2[1] - point1[1];
  float d2 = dx * dx + dy * dy; // Dist between foci, squared
  if (d2 <= 0.0) {
    // Foci are in same spot - it's a circle
    perimeter = 2.0 * RADIUS;
    d = 0.0;
  } else {
    // Foci are separated - it's an ellipse.
    d = sqrt(d2); // Distance between foci
    float c = d * 0.5; // Center-to-foci distance
    // This is an utterly brute-force way of ellipse-filling based on
    // the "two nails and a string" metaphor...we have the foci points
    // and just need the string length (triangle perimeter) to yield
    // an ellipse with area equal to a circle of 'radius'.
    // c^2 = a^2 - b^2  <- ellipse formula
    //   a = r^2 / b    <- substitute
    // c^2 = (r^2 / b)^2 - b^2
    // b = sqrt(((c^2) + sqrt((c^4) + 4 * r^4)) / 2)  <- solve for b
    float c2 = c * c;
    float b2 = (c2 + sqrt((c2 * c2) + 4 * (RADIUS * RADIUS * RADIUS * RADIUS))) * 0.5;
    // By my math, perimeter SHOULD be...
    // perimeter = d + 2 * sqrt(b2 + c2);
    // ...but for whatever reason, working approach here is really...
    perimeter = d + 2 * sqrt(b2);
  }

  // Like I'm sure there's a way to rasterize this by spans rather than
  // all these square roots on every pixel, but for now...
  for (int y=rect[1]; y<rect[3]; y++) { // For each row...
    float dy1 = (float)y - point1[1]; // Y distance from pixel to first point
    float dy2 = (float)y - point2[1]; // " to second
    dy1 *= dy1; // Y1^2
    dy2 *= dy2; // Y2^2
    for (int x=rect[0]; x<rect[2]; x++) { // For each column...
      float dx1 = (float)x - point1[0]; // X distance from pixel to first point
      float dx2 = (float)x - point2[0]; // " to second
      float d1 = sqrt(dx1 * dx1 + dy1); // 2D distance to first point
      float d2 = sqrt(dx2 * dx2 + dy2); // " to second
      if ((d1 + d2 + d) <= perimeter) {
        canvas->drawPixel(x, y, eye_color); // Point is inside ellipse
      }
    }
  }
}

void loop() { // Repeat forever...
 yield();
Serial.println("1"); yield();
  canvas->fillScreen(0);


  // The eye animation logic is a carry-over from like a billion
  // prior eye projects, so this might be comment-light.
  uint32_t now = micros(); // 'Snapshot' the time once per frame

  float upper, lower, ratio;

  // Blink logic
  uint32_t elapsed = now - blink_start_time; // Time since start of blink event
  if (elapsed > blink_duration) {  // All done with event?
    blink_start_time = now;        // A new one starts right now
    elapsed = 0;
    blink_state++;                 // Cycle closing/opening/paused
    if (blink_state == 1) {        // Starting new blink...
      blink_duration = random(60000, 120000);
    } else if (blink_state == 2) { // Switching closing to opening...
      blink_duration *= 2;         // Opens at half the speed
    } else {                       // Switching to pause in blink
      blink_state = 0;
      blink_duration = random(500000, 4000000);
    }
  }
  if (blink_state) {            // If currently in a blink...
    float ratio = (float)elapsed / (float)blink_duration; // 0.0-1.0 as it closes
    if (blink_state == 2) ratio = 1.0 - ratio;            // 1.0-0.0 as it opens
    upper = ratio * 15.0 - 4.0; // Upper eyelid pos. in 3X space
    lower = 23.0 - ratio * 8.0; // Lower eyelid pos. in 3X space
  }
Serial.println("2"); yield();

  // Eye movement logic. Two points, 'p1' and 'p2', are the foci of an
  // ellipse. p1 moves from current to next position a little faster
  // than p2, creating a "squash and stretch" effect (frame rate and
  // resolution permitting). When motion is stopped, the two points
  // are at the same position.
  float p1[2], p2[2];
  elapsed = now - move_start_time;             // Time since start of move event
  if (in_motion) {                             // Currently moving?
    if (elapsed > move_duration) {             // If end of motion reached,
      in_motion = false;                       // Stop motion and
      memcpy(&p1, &next_pos, sizeof next_pos); // set everything to new position
      memcpy(&p2, &next_pos, sizeof next_pos);
      memcpy(&cur_pos, &next_pos, sizeof next_pos);
      move_duration = random(500000, 1500000); // Wait this long
    } else { // Still moving
      // Determine p1, p2 position in time
      float delta[2];
      delta[0] = next_pos[0] - cur_pos[0];
      delta[1] = next_pos[1] - cur_pos[1];
      ratio = (float)elapsed / (float)move_duration;
      if (ratio < 0.7) { // First 70% of move time
        // p1 is in motion
        // Easing function: 3*e^2-2*e^3 0.0 to 1.0
        float e = ratio / 0.7; // 0.0 to 1.0
        e = 3 * e * e - 2 * e * e * e;
        p1[0] = cur_pos[0] + delta[0] * e;
        p1[1] = cur_pos[1] + delta[1] * e;
      } else { // Last 30% of move time
        memcpy(&p1, &next_pos, sizeof next_pos); // p1 has reached end position
      }
      if (ratio > 0.2) { // Last 80% of move time
        // p2 is in motion
        float e = (ratio - 0.2) / 0.8; // 0.0 to 1.0
        e = 3 * e * e - 2 * e * e * e; // Easing func.
        p2[0] = cur_pos[0] + delta[0] * e;
        p2[1] = cur_pos[1] + delta[1] * e;
      } else { // First 20% of move time
        memcpy(&p2, &cur_pos, sizeof cur_pos); // p2 waits at start position
      }
    }
  } else { // Eye is stopped
    memcpy(&p1, &cur_pos, sizeof cur_pos); // Both foci at current eye position
    memcpy(&p2, &cur_pos, sizeof cur_pos);
    if (elapsed > move_duration) { // Pause time expired?
      in_motion = true;            // Start up new motion!
      move_start_time = now;
      move_duration = random(150000, 250000);
      float angle = (float)random(1000) / 1000.0 * M_PI * 2.0;
      float dist = (float)random(750) / 100.0;
      next_pos[0] = 9.0 + cos(angle) * dist;
      next_pos[1] = 7.5 + sin(angle) * dist * 0.8;
    }
  }
Serial.println("3"); yield();

  // Draw the raster part of each eye...
  for (uint8_t e=0; e<2; e++) {
    // Each eye's foci are offset slightly, to fixate toward center
#if 0
    float p1a[2] = { p1[0] + x_offset[e], p1[1] };
    float p2a[2] = { p2[0] + x_offset[e], p2[1] };
#else
    float p1a[2], p2a[2];
    p1a[0] = p1[0] + x_offset[e];
    p2a[0] = p2[0] + x_offset[e];
    p1a[1] = p2a[1] = p1[1];
#endif
    // Compute bounding rectangle (in 3X space) of ellipse
    // (min X, min Y, max X, max Y). Like the ellipse rasterizer,
    // this isn't optimal, but will suffice.
    int bounds[4];
    bounds[0] = max(int(min(p1a[0], p2a[0]) - RADIUS), 0);
    bounds[1] = max(int(min(p1a[1], p2a[1]) - RADIUS), 0);
//    bounds[1] = max(bounds[1], (int)upper);
    bounds[2] = min(int(max(p1a[0], p2a[0]) + RADIUS + 1), 18);
    bounds[3] = min(int(max(p1a[1], p2a[1]) + RADIUS + 1), 15);
//    bounds[2] = min(bounds[3], (int)lower);
bounds[0] = 0;
bounds[1] = 0;
bounds[2] = 18 * 3;
bounds[3] = 5 * 3;

#if 0
      bounds = (
          max(int(min(p1a[0], p2a[0]) - radius), 0),
          max(int(min(p1a[1], p2a[1]) - radius), 0, int(upper)),
          min(int(max(p1a[0], p2a[0]) + radius + 1), 18),
          min(int(max(p1a[1], p2a[1]) + radius + 1), 15, int(lower) + 1),
      )
#endif
    rasterize(p1a, p2a, bounds); // Render ellipse into buffer
  }

Serial.println("4"); yield();

  // If the eye is currently blinking, and if the top edge of the
  // eyelid overlaps the bitmap, draw a scanline across the bitmap
  // and update the bounds rect so the whole width of the bitmap
  // is scaled.
  if (blink_state and upper >= 0.0) {
    canvas->fillRect(0, 0, canvas->width(), (int)upper + 1, 0x0004);
  }

Serial.println("5"); yield();

  glasses.scale();
Serial.println("6"); yield();

  // Matrix and rings share a few pixels. To make the rings take
  // precedence, they're drawn later. So blink state is revisited now...
  if (blink_state) { // In mid-blink?
    for (uint8_t i=0; i<13; i++) { // Half an LED ring, top-to-bottom...
      float a = min(max(y_pos[i] - upper + 1.0, 0.0), 3.0);
      float b = min(max(lower - y_pos[i] + 1.0, 0.0), 3.0);
      ratio = a * b / 9.0; // Proximity of LED to eyelid edges
      uint32_t packed = interp(ring_open_color, ring_blink_color, ratio);
      glasses.left_ring.setPixelColor(i, packed);
      glasses.right_ring.setPixelColor(i, packed);
      if ((i > 0) && (i < 12)) {
        uint8_t j = 24 - i; // Mirror half-ring to other side
        glasses.left_ring.setPixelColor(j, packed);
        glasses.right_ring.setPixelColor(j, packed);
      }
    }
  } else {
    glasses.left_ring.fill(ring_open_color_packed);
    glasses.right_ring.fill(ring_open_color_packed);
  }

Serial.println("7"); yield();


  glasses.show();
Serial.println("8"); yield();

  frames += 1;
  elapsed = millis() - start_time;
  Serial.println(frames * 1000 / elapsed);
}


#if 0
# Two eye objects. The first starts at column 1 of the matrix with its
# pupil offset by +2 (in 3X space), second at column 11 with -2 offset.
# The offsets make the pupils fixate slightly (converge on a point), so
# the two pupils aren't always aligned the same on the pixel grid, which
# would be conspicuously pixel-y.
#endif // 0
