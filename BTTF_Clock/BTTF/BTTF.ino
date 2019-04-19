// Time Circuit sketch for Adafruit 4-Digit 7-Segment Display w/I2C Backpack.
// Modeled after Doc Brown's DeLorean time circuit from the "Back to the
// Future" movies.  Uses three (3) each of the following displays:
//   Red   : http://www.adafruit.com/products/878
//   Green : http://www.adafruit.com/products/880
//   Yellow: http://www.adafruit.com/products/879
// A blue version is also available, but not used here.  Also uses two (2)
// each 3mm discrete LEDs:
//   Green : http://www.adafruit.com/products/779
//   Red   : http://www.adafruit.com/products/777
// Two yellow LEDs are used, but these aren't available in the shop -- they
// can be purchased through Digi-Key, etc.  The same sources will likely
// carry a 74HC138 3-to-8 line decoder w/inverting outputs (or, with some
// changes to the code, a more common 74HC32 quad 2-input OR gate could
// also be used, if you already have one on hand -- see comments later).
// The resulting item is not 100% screen accurate.  The film prop used
// 2-digit displays for day, hour and minute, the discrete LEDs for the
// top (red) display were yellow, while the 3-character month displays were
// back-painted glass fakes.  This demo was put together for fun, not
// pedantry, and generally gets the idea across.  Everyone recognizes it!

// These 4-digit displays can be assigned any of eight I2C addresses via
// solder jumpers on the back.  But the full time circuit requires *nine*
// displays.  A dirty hack exploits the fact that we only need one-way
// (write only) access to the displays.  The I2C data line is connected to
// all devices as normal...then the I2C clock drives the enable line of a
// 74HC138, while the select lines choose among multiple ersatz I2C buses
// (potentially up to 8, though we're only using 3 here).  Only that bus
// then responds to the incoming data.  The 74HC138 was chosen for its
// inverting outputs -- the idle state is high, consistent with I2C.

// So, each bus contains three 4-digit displays, and within each bus they're
// assigned address 0 (for MM.DD), 1 (YYYY) and 2 (HH:MM).  This simplifies
// the code, as display addresses are the same across all dates.  A ChronoDot
// (RTC_DS1307) clock chip is also used...bidirectional communication works
// because this connects to the regular I2C clock & data lines, not one of
// the 74HC138 outputs.  Altogether there's 10 devices attached to the I2C
// data line.  I'm not sure what the recommended fanout is for the ATmega...
// but if this runs into trouble, can always add a second 74HC138 for data,
// using the same bus select bits.

#include <Wire.h>
#include <Adafruit_LEDBackpack.h>
#include <Adafruit_GFX.h>
#include <RTClib.h>

Adafruit_7segment matrix[3] = {
  Adafruit_7segment(), Adafruit_7segment(), Adafruit_7segment() };
RTC_DS1307 clock;
// RTClib isn't pre-Y2K (or post-Y2.1K) compliant, so an ugly trick is used
// to represent "fantasy" dates.  Because our clock displays don't show
// seconds, that field in the DateTime class is borrowed to indicate a
// century #.  Honest-to-goodness DateTimes will have a seconds() value of
// 0 to 59.  If seconds >= 100, this field (-100) is the two-digit century.
DateTime dest(55, 11,  5, 22,  4, 100 + 19), // Nov 5, 1955 10:04 PM
         last(85, 10, 26,  1, 24, 100 + 19); // Oct 26, 1985 1:24 AM

void setup() {
  uint8_t m, b;

  clock.begin();

  // NOTE: all pin numbers used here are for the Teensy microcontroller
  // board, NOT a stock Arduino.  You may need to adapt this code to
  // your particular situation. (e.g. if making a prop that also uses
  // the Wave Shield to add sounds, you'd want to use an Arduino Uno and
  // then steer clear of all the SPI pins (10-13)).

  // Enable select lines for I2C multiplexing (only 2 are used here)
  pinMode( 9, OUTPUT);
  pinMode(10, OUTPUT);

  // Enable AM/PM LED outputs, set all LOW (off)
  for(b=11; b<=16; b++) {
    pinMode(b, OUTPUT);
    digitalWrite(b, LOW);
  }

  // Initialize all three displays on all three buses
  for(b=0; b<3; b++) {
    selectBus(b);
    for(m=0; m<3; m++) matrix[m].begin(0x70 + m);
  }
}

boolean dots = false; // For flashing colon on HH:MM times

void loop() {
  displayDate(0, dest);        // Destination time
  displayDate(1, clock.now()); // Present time
  displayDate(2, last);        // Last time departed

  dots = !dots;                // Blink blink blink
  delay(500);
}

// This function enables one of the 3 (but potentially up to 8) I2C buses
// by setting the select lines on the 74HC138 (only 2 lines are used in the
// circuit, the third is tied to ground).  A 74HC32 quad OR gate could also
// be used, but each bus will require its own select line (set corresponding
// output HIGH to disable, LOW to enable).  I wanted to use the least pins
// so that others remain free for the addition of a possible keypad later.
// (Could also free up pins using a port expander or shift register for
// the AM/PM LEDs.)
void selectBus(uint8_t b) {
  digitalWrite(10, (b & 1) ? HIGH : LOW);
  digitalWrite( 9, (b & 2) ? HIGH : LOW);
  // Can add third bit here if more buses are needed
}

// Show contents of DateTime object on the three displays across one bus
void displayDate(uint8_t b, DateTime d) {
  int x;

  selectBus(b);

  // Write MM.DD (zero padded) to display #0
  x = d.month();
  matrix[0].writeDigitNum(0, x / 10);
  matrix[0].writeDigitNum(1, x % 10, true);
  x = d.day();
  matrix[0].writeDigitNum(3, x / 10);
  matrix[0].writeDigitNum(4, x % 10);

  // Write year to display #1 (4-digit, zero-padded)
  // Great Scott!  RTClib isn't pre-Y2K compliant, so 'second'
  // is borrowed as a flag to indicate fantasy dates.
  if((x = d.second()) >= 100) x = d.year() - 2000 + x * 100;
  else                        x = d.year();
  matrix[1].writeDigitNum(0, (x / 1000) % 10);
  matrix[1].writeDigitNum(1, (x /  100) % 10);
  matrix[1].writeDigitNum(3, (x /   10) % 10);
  matrix[1].writeDigitNum(4,  x         % 10);

  // Write time to display #2 (HH:MM, zero-padded + AM/PM indicator)
  x = d.hour();
  if(x < 12) { // AM
    digitalWrite(b * 2 + 11, HIGH); // Upper LED on
    digitalWrite(b * 2 + 12, LOW);  // Lower LED off
  } else {     // PM
    digitalWrite(b * 2 + 11, LOW);  // Upper LED off
    digitalWrite(b * 2 + 12, HIGH); // Lower LED on
  }
  if(x > 12) x -= 12; // Convert 24-hour to 12-hour time
  matrix[2].writeDigitNum(0, x / 10);
  matrix[2].writeDigitNum(1, x % 10);
  x = d.minute();
  matrix[2].writeDigitNum(3, x / 10);
  matrix[2].writeDigitNum(4, x % 10);
  matrix[2].drawColon(dots);

  // Refresh all three displays on current bus
  for(x=0; x<3; x++) matrix[x].writeDisplay();
}
