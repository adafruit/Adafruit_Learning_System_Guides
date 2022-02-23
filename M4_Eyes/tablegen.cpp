// SPDX-FileCopyrightText: 2019 Phillip Burgess for Adafruit Industries
//
// SPDX-License-Identifier: MIT

//34567890123456789012345678901234567890123456789012345678901234567890123456

#include "globals.h"

// Code in this file calculates various tables used in eye rendering.

// Because 3D math is probably asking too much of our microcontroller,
// the round eyeball shape is faked using a 2D displacement map, a la
// Photoshop's displacement filter or old demoscene & screensaver tricks.
// This is not really an accurate representation of 3D rotation,
// but works well enough for fooling the casual observer.

void calcDisplacement() {
  // To save RAM, the displacement map is calculated for ONE QUARTER of
  // the screen, then mirrored horizontally/vertically down the middle
  // when rendering. Additionally, only a single axis displacement need
  // be calculated, since eye shape is X/Y symmetrical one can just swap
  // axes to look up displacement on the opposing axis.
  if(displace = (uint8_t *)malloc((DISPLAY_SIZE/2) * (DISPLAY_SIZE/2))) {
    float    eyeRadius2 = (float)(eyeRadius * eyeRadius);
    uint8_t  x, y;
    float    dx, dy, d2, d, h, a, pa;
    uint8_t *ptr = displace;
    // Displacement is calculated for the first quadrant in traditional
    // "+Y is up" Cartesian coordinate space; any mirroring or rotation
    // is handled in eye rendering code.
    for(y=0; y<(DISPLAY_SIZE/2); y++) {
      yield(); // Periodic yield() makes sure mass storage filesystem stays alive
      dy  = (float)y + 0.5;
      dy *= dy; // Now dy^2
      for(x=0; x<(DISPLAY_SIZE/2); x++) {
        // Get distance to origin point. Pixel centers are at +0.5, this is
        // normal, desirable and by design -- screen center at (120.0,120.0)
        // falls between pixels and allows numerically-correct mirroring.
        dx = (float)x + 0.5;
        d2 = dx * dx + dy;                 // Distance to origin, squared
        if(d2 <= eyeRadius2) {             // Pixel is within eye area
          d      = sqrt(d2);               // Distance to origin
          h      = sqrt(eyeRadius2 - d2);  // Height of eye hemisphere at d
          a      = atan2(d, h);            // Angle from center: 0 to pi/2
          //pa     = a * eyeRadius;        // Convert to pixels (no)
          pa = a / M_PI_2 * mapRadius;     // Convert to pixels
          dx    /= d;                      // Normalize dx part of 2D vector
          *ptr++ = (uint8_t)(dx * pa) - x; // Round to pixel space (no +0.5)
        } else {                           // Outside eye area
          *ptr++ = 255;                    // Mark as out-of-eye-bounds
        }
      }
    }
  }
}

void calcMap(void) {
  int pixels = mapRadius * mapRadius;
  if(polarAngle = (uint8_t *)malloc(pixels * 2)) { // Single alloc for both tables
    polarDist = (int8_t *)&polarAngle[pixels];     // Offset to second table

    // CALCULATE POLAR ANGLE & DISTANCE

    float mapRadius2  = mapRadius * mapRadius;  // Radius squared
    float iRad        = screen2map(irisRadius); // Iris size in in polar map pixels
    float irisRadius2 = iRad * iRad;            // Iris size squared

    uint8_t *anglePtr = polarAngle;
    int8_t  *distPtr  = polarDist;

    // Like the displacement map, only the first quadrant is calculated,
    // and the other three quadrants are mirrored/rotated from this.
    int   x, y;
    float dx, dy, dy2, d2, d, angle, xp;
    for(y=0; y<mapRadius; y++) {
      yield(); // Periodic yield() makes sure mass storage filesystem stays alive
      dy  = (float)y + 0.5;        // Y distance to map center
      dy2 = dy * dy;
      for(x=0; x<mapRadius; x++) {
        dx = (float)x + 0.5;       // X distance to map center
        d2 = dx * dx + dy2;        // Distance to center of map, squared
        if(d2 > mapRadius2) {      // If it exceeds 1/2 map size, squared,
          *anglePtr++ = 0;         // then mark as out-of-eye-bounds
          *distPtr++  = -128;
        } else {                   // else pixel is within eye area...
          angle  = atan2(dy, dx);  // -pi to +pi (0 to +pi/2 in 1st quadrant)
          angle  = M_PI_2 - angle; // Clockwise, 0 at top
          angle *= 512.0 / M_PI;   // 0 to <256 in 1st quadrant
          *anglePtr++ = (uint8_t)angle;
          d = sqrt(d2);
          if(d2 > irisRadius2) {
            // Point is in sclera
            d = (mapRadius - d) / (mapRadius - iRad);
            d *= 127.0;
            *distPtr++ = (int8_t)d; // 0 to 127
          } else {
            // Point is in iris (-dist to indicate such)
            d = (iRad - d) / iRad;
            d *= -127.0;
            *distPtr++ = (int8_t)d - 1; // -1 to -127
          }
        }
      }
    }

    // If slit pupil is enabled, override iris area of polarDist map.
    if(slitPupilRadius > 0) {
      // Iterate over each pixel in the iris section of the polar map...
      for(y=0; y < mapRadius; y++) {
        yield(); // Periodic yield() makes sure mass storage filesystem stays alive
        dy  = y + 0.5;            // Distance to center, Y component
        dy2 = dy * dy;
        for(x=0; x < mapRadius; x++) {
          dx = x + 0.5;           // Distance to center point, X component
          d2 = dx * dx + dy2;     // Distance to center, squared
          if(d2 <= irisRadius2) { // If inside iris...
            yield();
            xp = x + 0.5;
            // This is a bit ugly in that it iteratively calculates the
            // polarDist value...trial and error. It should be possible to
            // algebraically simplify this and find the single polarDist
            // point for a given pixel, but I've not worked that out yet.
            // This is only needed once at startup, not a complete disaster.
            for(int i=126; i>=0; i--) {
              float ratio = i / 128.0; // 0.0 (open) to just-under-1.0 (slit) (>= 1.0 will cause trouble)
              // Interpolate a point between top of iris and top of slit pupil, based on ratio
              float y1 = iRad - (iRad - slitPupilRadius) * ratio;
              // (x1 is 0 and thus dropped from equation below)
              // And another point between right of iris and center of eye, inverse ratio
              float x2 = iRad * (1.0 - ratio);
              // (y2 is also zero, same deal)
              // Find X coordinate of center of circle that crosses above two points
              // and has Y at 0.0
              float xc = (x2 * x2 - y1 * y1) / (2 * x2);
              dx = x2 - xc;       // Distance from center of circle to right edge
              float r2 = dx * dx; // center-to-right distance squared
              dx = xp - xc;       // X component of...
              d2 = dx * dx + dy2; // Distance from pixel to left 'xc' point
              if(d2 <= r2) {      // If point is within circle...
                polarDist[y * mapRadius + x] = (int8_t)(-1 - i); // Set to distance 'i'
                break;
              }
            }
          }
        }
      }
    }
  }
}

// Scale a measurement in screen pixels to polar map pixels
float screen2map(int in) {
  return atan2(in, sqrt(eyeRadius * eyeRadius - in * in)) / M_PI_2 * mapRadius;
}

// Inverse of above
float map2screen(int in) {
  return sin((float)in / (float)mapRadius) * M_PI_2 * eyeRadius;
}
