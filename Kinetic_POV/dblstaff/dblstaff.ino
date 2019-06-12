/*------------------------------------------------------------------------
  POV LED double staff sketch.  Uses the following Adafruit parts
  (X2 for two staffs):

  - Pro Trinket 5V https://www.adafruit.com/product/2000
  - 2200 mAh Lithium Ion Battery https://www.adafruit.com/product/1781
  - LiPoly Backpack https://www.adafruit.com/product/2124
  - Tactile On/Off Switch with Leads https://www.adafruit.com/product/1092
  - 144 LED/m DotStar strip (#2328 or #2329)
    (ONE METER is enough for ONE STAFF, TWO METERS for TWO staffs)
  - Infrared Sensor: https://www.adafruit.com/product/157
  - Mini Remote Control: https://www.adafruit.com/product/389
    (only one remote is required for multiple staffs)

  Needs Adafruit_DotStar library: github.com/adafruit/Adafruit_DotStar

  This is based on the LED poi code (also included in the repository),
  but ATtiny-specific code has been stripped out for brevity, since the
  staffs pretty much require Pro Trinket or better (lots more LEDs here).

  Adafruit invests time and resources providing this open source code,
  please support Adafruit and open-source hardware by purchasing
  products from Adafruit!

  Written by Phil Burgess / Paint Your Dragon for Adafruit Industries.
  MIT license, all text above must be included in any redistribution.
  See 'COPYING' file for additional notes.
  ------------------------------------------------------------------------*/

#include <Arduino.h>
#include <Adafruit_DotStar.h>
#include <avr/power.h>
#include <avr/sleep.h>
#include <SPI.h>

typedef uint16_t line_t;

// CONFIGURABLE STUFF ------------------------------------------------------

#include "graphics.h" // Graphics data is contained in this header file.
// It's generated using the 'convert.py' Python script.  Various image
// formats are supported, trading off color fidelity for PROGMEM space.
// Handles 1-, 4- and 8-bit-per-pixel palette-based images, plus 24-bit
// truecolor.  1- and 4-bit palettes can be altered in RAM while running
// to provide additional colors, but be mindful of peak & average current
// draw if you do that!  Power limiting is normally done in convert.py
// (keeps this code relatively small & fast).

// Ideally you use hardware SPI as it's much faster, though limited to
// specific pins.  If you really need to bitbang DotStar data & clock on
// different pins, optionally define those here:
//#define LED_DATA_PIN  0
//#define LED_CLOCK_PIN 1

// Empty and full thresholds (millivolts) used for battery level display:
#define BATT_MIN_MV 3350 // Some headroom over battery cutoff near 2.9V
#define BATT_MAX_MV 4000 // And little below fresh-charged battery near 4.1V

boolean autoCycle = true; // Set to true to cycle images by default
#define CYCLE_TIME 15     // Time, in seconds, between auto-cycle images

#define IR_PIN     3      // MUST be INT1 pin!

// Adafruit IR Remote Codes:
//   Button       Code         Button  Code
//   -----------  ------       ------  -----
//   VOL-:        0x0000       0/10+:  0x000C
//   Play/Pause:  0x0001       1:      0x0010
//   VOL+:        0x0002       2:      0x0011
//   SETUP:       0x0004       3:      0x0012
//   STOP/MODE:   0x0006       4:      0x0014
//   UP:          0x0005       5:      0x0015
//   DOWN:        0x000D       6:      0x0016
//   LEFT:        0x0008       7:      0x0018
//   RIGHT:       0x000A       8:      0x0019
//   ENTER/SAVE:  0x0009       9:      0x001A
//   Back:        0x000E

#define BTN_BRIGHT_UP    0x0002
#define BTN_BRIGHT_DOWN  0x0000
#define BTN_RESTART      0x0001
#define BTN_BATTERY      0x0004
#define BTN_FASTER       0x0005
#define BTN_SLOWER       0x000D
#define BTN_OFF          0x0006
#define BTN_PATTERN_PREV 0x0008
#define BTN_PATTERN_NEXT 0x000A
#define BTN_NONE         0xFFFF
#define BTN_AUTOPLAY     0x0009

// -------------------------------------------------------------------------

#if defined(LED_DATA_PIN) && defined(LED_CLOCK_PIN)
// Older DotStar LEDs use GBR order.  If colors are wrong, edit here.
Adafruit_DotStar strip = Adafruit_DotStar(NUM_LEDS,
  LED_DATA_PIN, LED_CLOCK_PIN, DOTSTAR_BGR);
#else
Adafruit_DotStar strip = Adafruit_DotStar(NUM_LEDS, DOTSTAR_BGR); 
#endif

void     imageInit(void),
         IRinterrupt(void),
         showBatteryLevel(void);
uint16_t readVoltage(void);

void setup() {
  strip.begin(); // Allocate DotStar buffer, init SPI
  strip.clear(); // Make sure strip is clear
  strip.show();  // before measuring battery

  showBatteryLevel();
  imageInit();   // Initialize pointers for default image

  attachInterrupt(1, IRinterrupt, CHANGE); // IR remote interrupt
}

void showBatteryLevel(void) {
  // Display battery level bargraph on startup.  It's just a vague estimate
  // based on cell voltage (drops with discharge) but doesn't handle curve.
  uint16_t mV  = readVoltage();
  uint8_t  lvl = (mV >= BATT_MAX_MV) ? NUM_LEDS : // Full (or nearly)
                 (mV <= BATT_MIN_MV) ?        1 : // Drained
                 1 + ((mV - BATT_MIN_MV) * NUM_LEDS + (NUM_LEDS / 2)) /
                 (BATT_MAX_MV - BATT_MIN_MV + 1); // # LEDs lit (1-NUM_LEDS)
  for(uint8_t i=0; i<lvl; i++) {                  // Each LED to batt level...
    uint8_t g = (i * 5 + 2) / NUM_LEDS;           // Red to green
    strip.setPixelColor(i, 4-g, g, 0);
    strip.show();                                 // Animate a bit
    delay(250 / NUM_LEDS);
  }
  delay(1500);                                    // Hold last state a moment
  strip.clear();                                  // Then clear strip
  strip.show();
}

// GLOBAL STATE STUFF ------------------------------------------------------

uint32_t lastImageTime = 0L, // Time of last image change
         lastLineTime  = 0L;
uint8_t  imageNumber   = 0,  // Current image being displayed
         imageType,          // Image type: PALETTE[1,4,8] or TRUECOLOR
        *imagePalette,       // -> palette data in PROGMEM
        *imagePixels,        // -> pixel data in PROGMEM
         palette[16][3];     // RAM-based color table for 1- or 4-bit images
line_t   imageLines,         // Number of lines in active image
         imageLine;          // Current line number in image
volatile uint16_t irCode = BTN_NONE; // Last valid IR code received

const uint8_t PROGMEM brightness[] = { 15, 31, 63, 127, 255 };
uint8_t bLevel = sizeof(brightness) - 1;

// Microseconds per line for various speed settings
const uint16_t PROGMEM lineTable[] = { // 375 * 2^(n/3)
  1000000L /  375, // 375 lines/sec = slowest
  1000000L /  472,
  1000000L /  595,
  1000000L /  750, // 750 lines/sec = mid
  1000000L /  945,
  1000000L / 1191,
  1000000L / 1500  // 1500 lines/sec = fastest
};
uint8_t  lineIntervalIndex = 3;
uint16_t lineInterval      = 1000000L / 750;

void imageInit() { // Initialize global image state for current imageNumber
  imageType    = pgm_read_byte(&images[imageNumber].type);
  imageLines   = pgm_read_word(&images[imageNumber].lines);
  imageLine    = 0;
  imagePalette = (uint8_t *)pgm_read_word(&images[imageNumber].palette);
  imagePixels  = (uint8_t *)pgm_read_word(&images[imageNumber].pixels);
  // 1- and 4-bit images have their color palette loaded into RAM both for
  // faster access and to allow dynamic color changing.  Not done w/8-bit
  // because that would require inordinate RAM (328P could handle it, but
  // I'd rather keep the RAM free for other features in the future).
  if(imageType == PALETTE1)      memcpy_P(palette, imagePalette,  2 * 3);
  else if(imageType == PALETTE4) memcpy_P(palette, imagePalette, 16 * 3);
  lastImageTime = millis(); // Save time of image init for next auto-cycle
}

void nextImage(void) {
  if(++imageNumber >= NUM_IMAGES) imageNumber = 0;
  imageInit();
}

void prevImage(void) {
  imageNumber = imageNumber ? imageNumber - 1 : NUM_IMAGES - 1;
  imageInit();
}

// MAIN LOOP ---------------------------------------------------------------

void loop() {
  uint32_t t = millis(); // Current time, milliseconds

  if(autoCycle) {
    if((t - lastImageTime) >= (CYCLE_TIME * 1000L)) nextImage();
    // CPU clocks vary slightly; multiple poi won't stay in perfect sync.
    // Keep this in mind when using auto-cycle mode, you may want to cull
    // the image selection to avoid unintentional regrettable combinations.
  }

  // Transfer one scanline from pixel data to LED strip:

  // If you're really pressed for graphics space and need just a few extra
  // scanlines, and know for a fact you won't be using certain image modes,
  // you can comment out the corresponding blocks below.  e.g. disabling
  // PALETTE8 and TRUECOLOR support can free up nearly 200 bytes of extra
  // image storage.

  switch(imageType) {

    case PALETTE1: { // 1-bit (2 color) palette-based image
      uint8_t  pixelNum = 0, byteNum, bitNum, pixels, idx,
              *ptr = (uint8_t *)&imagePixels[imageLine * NUM_LEDS / 8];
      for(byteNum = NUM_LEDS/8; byteNum--; ) { // Always padded to next byte
        pixels = pgm_read_byte(ptr++);  // 8 pixels of data (pixel 0 = LSB)
        for(bitNum = 8; bitNum--; pixels >>= 1) {
          idx = pixels & 1; // Color table index for pixel (0 or 1)
          strip.setPixelColor(pixelNum++,
            palette[idx][0], palette[idx][1], palette[idx][2]);
        }
      }
      break;
    }

    case PALETTE4: { // 4-bit (16 color) palette-based image
      uint8_t  pixelNum, p1, p2,
              *ptr = (uint8_t *)&imagePixels[imageLine * NUM_LEDS / 2];
      for(pixelNum = 0; pixelNum < NUM_LEDS; ) {
        p2  = pgm_read_byte(ptr++); // Data for two pixels...
        p1  = p2 >> 4;              // Shift down 4 bits for first pixel
        p2 &= 0x0F;                 // Mask out low 4 bits for second pixel
        strip.setPixelColor(pixelNum++,
          palette[p1][0], palette[p1][1], palette[p1][2]);
        strip.setPixelColor(pixelNum++,
          palette[p2][0], palette[p2][1], palette[p2][2]);
      }
      break;
    }

    case PALETTE8: { // 8-bit (256 color) PROGMEM-palette-based image
      uint16_t  o;
      uint8_t   pixelNum,
               *ptr = (uint8_t *)&imagePixels[imageLine * NUM_LEDS];
      for(pixelNum = 0; pixelNum < NUM_LEDS; pixelNum++) {
        o = pgm_read_byte(ptr++) * 3; // Offset into imagePalette
        strip.setPixelColor(pixelNum,
          pgm_read_byte(&imagePalette[o]),
          pgm_read_byte(&imagePalette[o + 1]),
          pgm_read_byte(&imagePalette[o + 2]));
      }
      break;
    }

    case TRUECOLOR: { // 24-bit ('truecolor') image (no palette)
      uint8_t  pixelNum, r, g, b,
              *ptr = (uint8_t *)&imagePixels[imageLine * NUM_LEDS * 3];
      for(pixelNum = 0; pixelNum < NUM_LEDS; pixelNum++) {
        r = pgm_read_byte(ptr++);
        g = pgm_read_byte(ptr++);
        b = pgm_read_byte(ptr++);
        strip.setPixelColor(pixelNum, r, g, b);
      }
      break;
    }
  }

  if(++imageLine >= imageLines) imageLine = 0; // Next scanline, wrap around

  while(((t = micros()) - lastLineTime) < lineInterval) {
    if(irCode != BTN_NONE) {
      if(!strip.getBrightness()) { // If strip is off...
        // Set brightness to last level
        strip.setBrightness(pgm_read_byte(&brightness[bLevel]));
        // and ignore button press (don't fall through)
        // effectively, first press is 'wake'
      } else {
        switch(irCode) {
         case BTN_BRIGHT_UP:
          if(bLevel < (sizeof(brightness) - 1))
            strip.setBrightness(pgm_read_byte(&brightness[++bLevel]));
          break;
         case BTN_BRIGHT_DOWN:
          if(bLevel)
            strip.setBrightness(pgm_read_byte(&brightness[--bLevel]));
          break;
         case BTN_FASTER:
          if(lineIntervalIndex < (sizeof(lineTable) / sizeof(lineTable[0]) - 1))
            lineInterval = pgm_read_word(&lineTable[++lineIntervalIndex]);
          break;
         case BTN_SLOWER:
          if(lineIntervalIndex)
            lineInterval = pgm_read_word(&lineTable[--lineIntervalIndex]);
          break;
         case BTN_RESTART:
          imageNumber = 0;
          imageInit();
          break;
         case BTN_BATTERY:
          strip.clear();
          strip.show();
          delay(250);
          strip.setBrightness(255);
          showBatteryLevel();
          strip.setBrightness(pgm_read_byte(&brightness[bLevel]));
          break;
         case BTN_OFF:
          strip.setBrightness(0);
          break;
         case BTN_PATTERN_PREV:
          prevImage();
          break;
         case BTN_PATTERN_NEXT:
          nextImage();
          break;
         case BTN_AUTOPLAY:
	  autoCycle = !autoCycle;
          break;
        }
      }
      irCode = BTN_NONE;
    }
  }

  strip.show(); // Refresh LEDs
  lastLineTime = t;
}


void IRinterrupt() {
  static uint32_t pulseStartTime = 0, pulseDuration = 0;
  static uint8_t  irValue, irBits, irBytes, irBuf[4];
  uint32_t t = micros();
  if(PIND & 0b00001000) { // Low-to-high (start of new pulse)
    pulseStartTime = t;
  } else {                // High-to-low (end of current pulse)
    uint32_t pulseDuration = t - pulseStartTime;
    if((pulseDuration > 4000) && (pulseDuration < 5000)) { // ~4.5 ms?
      irValue = irBits = irBytes = 0; // IR code start, reset counters
    } else if(pulseDuration < 2500) { // Data bit?
      irValue >>= 1;                  // Shift data in, LSB first
      if(pulseDuration >= 1125) irValue |= 0x80; // Longer pulse = 1
      if((++irBits == 8) && (irBytes < 4)) { // Full byte recv'd?
        irBuf[irBytes] = irValue;            // Store byte
        irValue = irBits = 0;                // and reset counters
        if((++irBytes == 4) && ((irBuf[2] ^ irBuf[3]) == 0xFF)) {
          uint16_t code = 0xFFFF;
          if((irBuf[0] ^ irBuf[1]) == 0xFF) {
            irCode = (irBuf[0] << 8) | irBuf[1];
          } else if((irBuf[0] == 0) && (irBuf[1] == 0xBF)) {
            irCode = irBuf[2];
          }
        }
      }
    }
  }
}

// Battery monitoring idea adapted from JeeLabs article:
// jeelabs.org/2012/05/04/measuring-vcc-via-the-bandgap/
// Code from Adafruit TimeSquare project, added Trinket support.
// In a pinch, the poi code can work on a 3V Trinket, but the battery
// monitor will not work correctly (due to the 3.3V regulator), so
// maybe just comment out any reference to this code in that case.
uint16_t readVoltage() {
  int      i, prev;
  uint8_t  count;
  uint16_t mV;

  // Select AVcc voltage reference + Bandgap (1.8V) input
  ADMUX  = _BV(REFS0) |
           _BV(MUX3)  | _BV(MUX2) | _BV(MUX1);
  ADCSRA = _BV(ADEN)  |                          // Enable ADC
           _BV(ADPS2) | _BV(ADPS1) | _BV(ADPS0); // 1/128 prescaler (125 KHz)
  // Datasheet notes that the first bandgap reading is usually garbage as
  // voltages are stabilizing.  It practice, it seems to take a bit longer
  // than that.  Tried various delays, but still inconsistent and kludgey.
  // Instead, repeated readings are taken until four concurrent readings
  // stabilize within 10 mV.
  for(prev=9999, count=0; count<4; ) {
    for(ADCSRA |= _BV(ADSC); ADCSRA & _BV(ADSC); ); // Start, await ADC conv.
    i  = ADC;                                       // Result
    mV = i ? (1100L * 1023 / i) : 0;                // Scale to millivolts
    if(abs((int)mV - prev) <= 10) count++;   // +1 stable reading
    else                          count = 0; // too much change, start over
    prev = mV;
  }
  ADCSRA = 0; // ADC off
  return mV;
}
