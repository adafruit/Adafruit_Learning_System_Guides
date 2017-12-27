//--------------------------------------------------------------------------
// Animated 'sand' for Adafruit Feather.  Uses the following parts:
//   - Feather 32u4 Basic Proto (adafruit.com/product/2771)
//   - Charlieplex FeatherWing (adafruit.com/product/2965 - any color!)
//   - LIS3DH accelerometer (2809)
//   - 350 mAh LiPoly battery (2750)
//   - SPDT Slide Switch (805)
//
// This is NOT good "learn from" code for the IS31FL3731; it is "squeeze
// every last byte from the microcontroller" code.  If you're starting out,
// download the Adafruit_IS31FL3731 and Adafruit_GFX libraries, which
// provide functions for drawing pixels, lines, etc.
//--------------------------------------------------------------------------

#include <Wire.h>            // For I2C communication
#include <Adafruit_LIS3DH.h> // For accelerometer

#define DISP_ADDR  0x74 // Charlieplex FeatherWing I2C address
#define ACCEL_ADDR 0x18 // Accelerometer I2C address
#define N_GRAINS     20 // Number of grains of sand
#define WIDTH        15 // Display width in pixels
#define HEIGHT        7 // Display height in pixels
#define MAX_FPS      45 // Maximum redraw rate, frames/second

// The 'sand' grains exist in an integer coordinate space that's 256X
// the scale of the pixel grid, allowing them to move and interact at
// less than whole-pixel increments.
#define MAX_X (WIDTH  * 256 - 1) // Maximum X coordinate in grain space
#define MAX_Y (HEIGHT * 256 - 1) // Maximum Y coordinate
struct Grain {
  int16_t  x,  y; // Position
  int16_t vx, vy; // Velocity
} grain[N_GRAINS];

Adafruit_LIS3DH accel      = Adafruit_LIS3DH();
uint32_t        prevTime   = 0;      // Used for frames-per-second throttle
uint8_t         backbuffer = 0,      // Index for double-buffered animation
                img[WIDTH * HEIGHT]; // Internal 'map' of pixels

const uint8_t PROGMEM remap[] = {    // In order to redraw the screen super
   0, 90, 75, 60, 45, 30, 15,  0,    // fast, this sketch bypasses the
       0,  0,  0,  0,  0,  0,  0, 0, // Adafruit_IS31FL3731 library and
   0, 91, 76, 61, 46, 31, 16,   1,   // writes to the LED driver directly.
      14, 29, 44, 59, 74, 89,104, 0, // But this means we need to do our
   0, 92, 77, 62, 47, 32, 17,  2,    // own coordinate management, and the
      13, 28, 43, 58, 73, 88,103, 0, // layout of pixels on the Charlieplex
   0, 93, 78, 63, 48, 33, 18,  3,    // Featherwing is strange! This table
      12, 27, 42, 57, 72, 87,102, 0, // remaps LED register indices in
   0, 94, 79, 64, 49, 34, 19,  4,    // sequence to the corresponding pixel
      11, 26, 41, 56, 71, 86,101, 0, // indices in the img[] array.
   0, 95, 80, 65, 50, 35, 20,  5,
      10, 25, 40, 55, 70, 85,100, 0,
   0, 96, 81, 66, 51, 36, 21,  6,
       9, 24, 39, 54, 69, 84, 99, 0,
   0, 97, 82, 67, 52, 37, 22,  7,
       8, 23, 38, 53, 68, 83, 98
};

// IS31FL3731-RELATED FUNCTIONS --------------------------------------------

// Begin I2C transmission and write register address (data then follows)
uint8_t writeRegister(uint8_t n) {
  Wire.beginTransmission(DISP_ADDR);
  Wire.write(n); // No endTransmission() - left open for add'l writes
  return 2;      // Always returns 2; count of I2C address + register byte n
}

// Select one of eight IS31FL3731 pages, or the Function Registers
void pageSelect(uint8_t n) {
  writeRegister(0xFD); // Command Register
  Wire.write(n);       // Page number (or 0xB = Function Registers)
  Wire.endTransmission();
}

// SETUP - RUNS ONCE AT PROGRAM START --------------------------------------

void setup(void) {
  uint8_t i, j, bytes;

  if(!accel.begin(ACCEL_ADDR)) {  // Init accelerometer.  If it fails...
    pinMode(LED_BUILTIN, OUTPUT);    // Using onboard LED
    for(i=1;;i++) {                  // Loop forever...
      digitalWrite(LED_BUILTIN, i & 1); // LED on/off blink to alert user
      delay(250);                       // 1/4 second
    }
  }
  accel.setRange(LIS3DH_RANGE_4_G); // Select accelerometer +/- 4G range

  Wire.setClock(400000); // Run I2C at 400 KHz for faster screen updates

  // Initialize IS31FL3731 Charlieplex LED driver "manually"...
  pageSelect(0x0B);                        // Access the Function Registers
  writeRegister(0);                        // Starting from first...
  for(i=0; i<13; i++) Wire.write(10 == i); // Clear all except Shutdown
  Wire.endTransmission();
  for(j=0; j<2; j++) {                     // For each page used (0 & 1)...
    pageSelect(j);                         // Access the Frame Registers
    for(bytes=i=0; i<180; i++) {           // For each register...
      if(!bytes) bytes = writeRegister(i); // Buf empty? Start xfer @ reg i
      Wire.write(0xFF * (i < 18));         // 0-17 = enable, 18+ = blink+PWM
      if(++bytes >= 32) bytes = Wire.endTransmission();
    }
    if(bytes) Wire.endTransmission();      // Write any data left in buffer
  }

  memset(img, 0, sizeof(img)); // Clear the img[] array
  for(i=0; i<N_GRAINS; i++) {  // For each sand grain...
    do {
      grain[i].x = random(WIDTH  * 256); // Assign random position within
      grain[i].y = random(HEIGHT * 256); // the 'grain' coordinate space
      // Check if corresponding pixel position is already occupied...
      for(j=0; (j<i) && (((grain[i].x / 256) != (grain[j].x / 256)) ||
                         ((grain[i].y / 256) != (grain[j].y / 256))); j++);
    } while(j < i); // Keep retrying until a clear spot is found
    img[(grain[i].y / 256) * WIDTH + (grain[i].x / 256)] = 255; // Mark it
    grain[i].vx = grain[i].vy = 0; // Initial velocity is zero
  }
}

// MAIN LOOP - RUNS ONCE PER FRAME OF ANIMATION ----------------------------

void loop() {
  // Limit the animation frame rate to MAX_FPS.  Because the subsequent sand
  // calculations are non-deterministic (don't always take the same amount
  // of time, depending on their current states), this helps ensure that
  // things like gravity appear constant in the simulation.
  uint32_t t;
  while(((t = micros()) - prevTime) < (1000000L / MAX_FPS));
  prevTime = t;

  // Display frame rendered on prior pass.  It's done immediately after the
  // FPS sync (rather than after rendering) for consistent animation timing.
  pageSelect(0x0B);       // Function registers
  writeRegister(0x01);    // Picture Display reg
  Wire.write(backbuffer); // Page # to display
  Wire.endTransmission();
  backbuffer = 1 - backbuffer; // Swap front/back buffer index

  // Read accelerometer...
  accel.read();
  int16_t ax = -accel.y / 256,      // Transform accelerometer axes
          ay =  accel.x / 256,      // to grain coordinate space
          az = abs(accel.z) / 2048; // Random motion factor
  az = (az >= 3) ? 1 : 4 - az;      // Clip & invert
  ax -= az;                         // Subtract motion factor from X, Y
  ay -= az;
  int16_t az2 = az * 2 + 1;         // Range of random motion to add back in

  // ...and apply 2D accel vector to grain velocities...
  int32_t v2; // Velocity squared
  float   v;  // Absolute velocity
  for(int i=0; i<N_GRAINS; i++) {
    grain[i].vx += ax + random(az2); // A little randomness makes
    grain[i].vy += ay + random(az2); // tall stacks topple better!
    // Terminal velocity (in any direction) is 256 units -- equal to
    // 1 pixel -- which keeps moving grains from passing through each other
    // and other such mayhem.  Though it takes some extra math, velocity is
    // clipped as a 2D vector (not separately-limited X & Y) so that
    // diagonal movement isn't faster
    v2 = (int32_t)grain[i].vx*grain[i].vx+(int32_t)grain[i].vy*grain[i].vy;
    if(v2 > 65536) { // If v^2 > 65536, then v > 256
      v = sqrt((float)v2); // Velocity vector magnitude
      grain[i].vx = (int)(256.0*(float)grain[i].vx/v); // Maintain heading
      grain[i].vy = (int)(256.0*(float)grain[i].vy/v); // Limit magnitude
    }
  }

  // ...then update position of each grain, one at a time, checking for
  // collisions and having them react.  This really seems like it shouldn't
  // work, as only one grain is considered at a time while the rest are
  // regarded as stationary.  Yet this naive algorithm, taking many not-
  // technically-quite-correct steps, and repeated quickly enough,
  // visually integrates into something that somewhat resembles physics.
  // (I'd initially tried implementing this as a bunch of concurrent and
  // "realistic" elastic collisions among circular grains, but the
  // calculations and volument of code quickly got out of hand for both
  // the tiny 8-bit AVR microcontroller and my tiny dinosaur brain.)

  uint8_t        i, bytes, oldidx, newidx, delta;
  int16_t        newx, newy;
  const uint8_t *ptr = remap;

  for(i=0; i<N_GRAINS; i++) {
    newx = grain[i].x + grain[i].vx; // New position in grain space
    newy = grain[i].y + grain[i].vy;
    if(newx > MAX_X) {               // If grain would go out of bounds
      newx         = MAX_X;          // keep it inside, and
      grain[i].vx /= -2;             // give a slight bounce off the wall
    } else if(newx < 0) {
      newx         = 0;
      grain[i].vx /= -2;
    }
    if(newy > MAX_Y) {
      newy         = MAX_Y;
      grain[i].vy /= -2;
    } else if(newy < 0) {
      newy         = 0;
      grain[i].vy /= -2;
    }

    oldidx = (grain[i].y/256) * WIDTH + (grain[i].x/256); // Prior pixel #
    newidx = (newy      /256) * WIDTH + (newx      /256); // New pixel #
    if((oldidx != newidx) && // If grain is moving to a new pixel...
        img[newidx]) {       // but if that pixel is already occupied...
      delta = abs(newidx - oldidx); // What direction when blocked?
      if(delta == 1) {            // 1 pixel left or right)
        newx         = grain[i].x;  // Cancel X motion
        grain[i].vx /= -2;          // and bounce X velocity (Y is OK)
        newidx       = oldidx;      // No pixel change
      } else if(delta == WIDTH) { // 1 pixel up or down
        newy         = grain[i].y;  // Cancel Y motion
        grain[i].vy /= -2;          // and bounce Y velocity (X is OK)
        newidx       = oldidx;      // No pixel change
      } else { // Diagonal intersection is more tricky...
        // Try skidding along just one axis of motion if possible (start w/
        // faster axis).  Because we've already established that diagonal
        // (both-axis) motion is occurring, moving on either axis alone WILL
        // change the pixel index, no need to check that again.
        if((abs(grain[i].vx) - abs(grain[i].vy)) >= 0) { // X axis is faster
          newidx = (grain[i].y / 256) * WIDTH + (newx / 256);
          if(!img[newidx]) { // That pixel's free!  Take it!  But...
            newy         = grain[i].y; // Cancel Y motion
            grain[i].vy /= -2;         // and bounce Y velocity
          } else { // X pixel is taken, so try Y...
            newidx = (newy / 256) * WIDTH + (grain[i].x / 256);
            if(!img[newidx]) { // Pixel is free, take it, but first...
              newx         = grain[i].x; // Cancel X motion
              grain[i].vx /= -2;         // and bounce X velocity
            } else { // Both spots are occupied
              newx         = grain[i].x; // Cancel X & Y motion
              newy         = grain[i].y;
              grain[i].vx /= -2;         // Bounce X & Y velocity
              grain[i].vy /= -2;
              newidx       = oldidx;     // Not moving
            }
          }
        } else { // Y axis is faster, start there
          newidx = (newy / 256) * WIDTH + (grain[i].x / 256);
          if(!img[newidx]) { // Pixel's free!  Take it!  But...
            newx         = grain[i].x; // Cancel X motion
            grain[i].vy /= -2;         // and bounce X velocity
          } else { // Y pixel is taken, so try X...
            newidx = (grain[i].y / 256) * WIDTH + (newx / 256);
            if(!img[newidx]) { // Pixel is free, take it, but first...
              newy         = grain[i].y; // Cancel Y motion
              grain[i].vy /= -2;         // and bounce Y velocity
            } else { // Both spots are occupied
              newx         = grain[i].x; // Cancel X & Y motion
              newy         = grain[i].y;
              grain[i].vx /= -2;         // Bounce X & Y velocity
              grain[i].vy /= -2;
              newidx       = oldidx;     // Not moving
            }
          }
        }
      }
    }
    grain[i].x  = newx; // Update grain position
    grain[i].y  = newy;
    img[oldidx] = 0;    // Clear old spot (might be same as new, that's OK)
    img[newidx] = 255;  // Set new spot
  }

  // Update pixel data in LED driver
  pageSelect(backbuffer); // Select background buffer
  for(i=bytes=0; i<sizeof(remap); i++) {
    if(!bytes) bytes = writeRegister(0x24 + i);
    Wire.write(img[pgm_read_byte(ptr++)] / 3); // Write each byte to matrix
    if(++bytes >= 32) bytes = Wire.endTransmission();
  }
  if(bytes) Wire.endTransmission();
}

