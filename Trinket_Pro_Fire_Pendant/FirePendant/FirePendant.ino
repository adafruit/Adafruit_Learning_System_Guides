//--------------------------------------------------------------------------
// Animated flame for Adafruit Pro Trinket.  Uses the following parts:
//   - Pro Trinket microcontroller (adafruit.com/product/2010 or 2000)
//     (#2010 = 3V/12MHz for longest battery life, but 5V/16MHz works OK)
//   - Charlieplex LED Matrix Driver (2946)
//   - Charlieplex LED Matrix (2947, 2948, 2972, 2973 or 2974)
//   - 350 mAh LiPoly battery (2750)
//   - LiPoly backpack (2124)
//   - SPDT Slide Switch (805)
//
// This is NOT good "learn from" code for the IS31FL3731; it is "squeeze
// every last byte from the Pro Trinket" code.  If you're starting out,
// download the Adafruit_IS31FL3731 and Adafruit_GFX libraries, which
// provide functions for drawing pixels, lines, etc.  This sketch also
// uses some ATmega-specific tricks and will not run as-is on other chips.
//--------------------------------------------------------------------------

#include <Wire.h>           // For I2C communication
#include "data.h"           // Flame animation data
#include <avr/power.h>      // Peripheral control and
#include <avr/sleep.h>      // sleep to minimize current draw

#define I2C_ADDR 0x74       // I2C address of Charlieplex matrix

uint8_t        page = 0;    // Front/back buffer control
const uint8_t *ptr  = anim; // Current pointer into animation data
uint8_t        img[9 * 16]; // Buffer for rendering image

// UTILITY FUNCTIONS -------------------------------------------------------

// The full IS31FL3731 library is NOT used by this code. Instead, 'raw'
// writes are made to the matrix driver.  This is to maximize the space
// available for animation data.  Use the Adafruit_IS31FL3731 and
// Adafruit_GFX libraries if you need to do actual graphics stuff.

// Begin I2C transmission and write register address (data then follows)
void writeRegister(uint8_t n) {
  Wire.beginTransmission(I2C_ADDR);
  Wire.write(n);
  // Transmission is left open for additional writes
}

// Select one of eight IS31FL3731 pages, or Function Registers
void pageSelect(uint8_t n) {
  writeRegister(0xFD); // Command Register
  Wire.write(n);       // Page number (or 0xB = Function Registers)
  Wire.endTransmission();
}

// SETUP FUNCTION - RUNS ONCE AT STARTUP -----------------------------------

void setup() {
  uint8_t i, p, byteCounter;

  power_all_disable(); // Stop peripherals: ADC, timers, etc. to save power
  power_twi_enable();  // But switch I2C back on; need it for display
  DIDR0 = 0x0F;        // Digital input disable on A0-A3

  // The Arduino Wire library runs I2C at 100 KHz by default.
  // IS31FL3731 can run at 400 KHz.  To ensure fast animation,
  // override the I2C speed settings after init...
  Wire.begin();                            // Initialize I2C
  TWSR = 0;                                // I2C prescaler = 1
  TWBR = (F_CPU / 400000 - 16) / 2;        // 400 KHz I2C
  // The TWSR/TWBR lines are AVR-specific and won't work on other MCUs.

  pageSelect(0x0B);                        // Access the Function Registers
  writeRegister(0);                        // Starting from first...
  for(i=0; i<13; i++) Wire.write(10 == i); // Clear all except Shutdown
  Wire.endTransmission();
  for(p=0; p<2; p++) {                     // For each page used (0 & 1)...
    pageSelect(p);                         // Access the Frame Registers
    writeRegister(0);                      // Start from 1st LED control reg
    for(i=0; i<18; i++) Wire.write(0xFF);  // Enable all LEDs (18*8=144)
    for(byteCounter = i+1; i<0xB4; i++) {  // For blink & PWM registers...
      Wire.write(0);                       // Clear all
      if(++byteCounter >= 32) {            // Every 32 bytes...
        byteCounter = 1;                   // End I2C transmission and
        Wire.endTransmission();            // start a new one because
        writeRegister(i);                  // Wire buf is only 32 bytes.
      }
    }
    Wire.endTransmission();
  }

  // Enable the watchdog timer, set to a ~32 ms interval (about 31 Hz)
  // This provides a sufficiently steady time reference for animation,
  // allows timer/counter peripherals to remain off (for power saving)
  // and can power-down the chip after processing each frame.
  set_sleep_mode(SLEEP_MODE_PWR_DOWN); // Deepest sleep mode (WDT wakes)
  noInterrupts();
  MCUSR  &= ~_BV(WDRF);
  WDTCSR  =  _BV(WDCE) | _BV(WDE);     // WDT change enable
  WDTCSR  =  _BV(WDIE) | _BV(WDP0);    // Interrupt enable, ~32 ms
  interrupts();
  // Peripheral and sleep savings only amount to about 10 mA, but this
  // may provide nearly an extra hour of run time before battery depletes.
}

// LOOP FUNCTION - RUNS EVERY FRAME ----------------------------------------

void loop() {
  uint8_t  a, x1, y1, x2, y2, x, y;

  power_twi_enable();
  // Datasheet recommends that I2C should be re-initialized after enable,
  // but Wire.begin() is slow.  Seems to work OK without.

  // Display frame rendered on prior pass.  This is done at function start
  // (rather than after rendering) to ensire more uniform animation timing.
  pageSelect(0x0B);    // Function registers
  writeRegister(0x01); // Picture Display reg
  Wire.write(page);    // Page #
  Wire.endTransmission();

  page ^= 1; // Flip front/back buffer index

  // Then render NEXT frame.  Start by getting bounding rect for new frame:
  a = pgm_read_byte(ptr++);     // New frame X1/Y1
  if(a >= 0x90) {               // EOD marker? (valid X1 never exceeds 8)
    ptr = anim;                 // Reset animation data pointer to start
    a   = pgm_read_byte(ptr++); // and take first value
  }
  x1 = a >> 4;                  // X1 = high 4 bits
  y1 = a & 0x0F;                // Y1 = low 4 bits
  a  = pgm_read_byte(ptr++);    // New frame X2/Y2
  x2 = a >> 4;                  // X2 = high 4 bits
  y2 = a & 0x0F;                // Y2 = low 4 bits

  // Read rectangle of data from anim[] into portion of img[] buffer
  for(x=x1; x<=x2; x++) { // Column-major
    for(y=y1; y<=y2; y++) img[(x << 4) + y] = pgm_read_byte(ptr++);
  }

  // Write img[] to matrix (not actually displayed until next pass)
  pageSelect(page);    // Select background buffer
  writeRegister(0x24); // First byte of PWM data
  uint8_t i = 0, byteCounter = 1;
  for(uint8_t x=0; x<9; x++) {
    for(uint8_t y=0; y<16; y++) {
      Wire.write(img[i++]);      // Write each byte to matrix
      if(++byteCounter >= 32) {  // Every 32 bytes...
        Wire.endTransmission();  // end transmission and
        writeRegister(0x24 + i); // start a new one (Wire lib limits)
      }
    }
  }
  Wire.endTransmission();

  power_twi_disable(); // I2C off (see comment at top of function)
  sleep_enable();
  interrupts();
  sleep_mode();        // Power-down MCU.
  // Code will resume here on wake; loop() returns and is called again
}

ISR(WDT_vect) { } // Watchdog timer interrupt (does nothing, but required)

