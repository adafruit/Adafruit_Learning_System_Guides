// Mindfulness Bracelet sketch for Adafruit/Arduino Gemma.  Briefly runs
// vibrating motor (connected through transistor) at regular intervals.
// This code is not beginner-friendly, it does a lot of esoteric low-level
// hardware shenanigans in order to conserve battery power.

const uint32_t           // These may be the only lines you need to edit...
  onTime   =  2 * 1000L, // Vibration motor run time, in milliseconds
  interval = 60 * 1000L; // Time between reminders, in milliseconds
                         // It gets progressively geekier from here...

// Additional power savings can optionally be realized by disabling the
// power-on LED, either by desoldering or by cutting the trace from 3Vo
// on the component side of the board.

// This sketch spends nearly all its time in a low-power sleep state...
#include <avr/power.h>
#include <avr/sleep.h>

// The chip's 'watchdog timer' (WDT) is used to wake up the CPU when needed.
// WDT runs on its own 128 KHz clock source independent of main CPU clock.
// Uncalibrated -- it's "128 KHz-ish" -- thus not reliable for extended
// timekeeping.  To compensate, immediately at startup the WDT is run for
// one maximum-duration cycle (about 8 seconds...ish) while keeping the CPU
// awake, the actual elapsed time is noted and used as a point of reference
// when calculating sleep times.  Still quite sloppy -- the WDT only has a
// max resolution down to 16 ms -- this may drift up to 30 seconds per hour,
// but is an improvement over the 'raw' WDT clock and is adequate for this
// casual, non-medical, non-Mars-landing application.  Alternatives would
// require keeping the CPU awake, draining the battery much quicker.

uint16_t          maxSleepInterval;  // Actual ms in '8-ish sec' WDT interval
volatile uint32_t sleepTime     = 1; // Total milliseconds remaining in sleep
volatile uint16_t sleepInterval = 1; // ms to subtract in current WDT cycle
volatile uint8_t  tablePos      = 0; // Index into WDT configuration table

void setup() {

  // Unused pins can be set to INPUT w/pullup -- most power-efficient state
  pinMode(0, INPUT_PULLUP);
  pinMode(2, INPUT_PULLUP);

  // LED shenanigans.  Rather that setting pin 1 to an output and using
  // digitalWrite() to turn the LED on or off, the internal pull-up resistor
  // (about 10K) is enabled or disabled, dimly lighting the LED with much
  // less current.
  pinMode(1, INPUT);               // LED off to start

  // AVR peripherals that are NEVER used by the sketch are disabled to save
  // tiny bits of power.  Some have side-effects, don't do this willy-nilly.
  // If using analogWrite() to for different motor levels, timer 0 and/or 1
  // must be enabled -- for power efficiency they could be turned off in the
  // ubersleep() function and re-enabled on wake.
  power_adc_disable();             // Knocks out analogRead()
  power_timer1_disable();          // May knock out analogWrite()
  power_usi_disable();             // Knocks out TinyWire library
  DIDR0 = _BV(AIN1D) | _BV(AIN0D); // Digital input disable on analog pins
  // Timer 0 isn't disabled yet...it's needed for one thing first...

  // The aforementioned watchdog timer calibration...
  uint32_t t = millis();                       // Save start time
  noInterrupts();                              // Timing-critical...
  MCUSR &= ~_BV(WDRF);                         // Watchdog reset flag
  WDTCR  =  _BV(WDCE) | _BV(WDE);              // WDT change enable
  WDTCR  =  _BV(WDIE) | _BV(WDP3) | _BV(WDP0); // 8192-ish ms interval
  interrupts();
  while(sleepTime);                            // Wait for WDT
  maxSleepInterval  = millis() - t;            // Actual ms elapsed
  maxSleepInterval += 64;                      // Egyptian constant
  power_timer0_disable();  // Knocks out millis(), delay(), analogWrite()
}

const uint32_t offTime = interval - onTime; // Duration motor is off, ms

void loop() {
  pinMode(1, INPUT);        // LED off
  ubersleep(offTime);       // Delay while off
}

// WDT timer operates only in specific intervals based on a prescaler.
// CPU wakes on each interval, prescaler is adjusted as needed to pick off
// the longest setting possible on each pass, until requested milliseconds
// have elapsed.
const uint8_t cfg[] PROGMEM = { // WDT config bits for different intervals
  _BV(WDIE) | _BV(WDP3) |                         _BV(WDP0), // ~8192 ms
  _BV(WDIE) | _BV(WDP3)                                    , // ~4096 ms
  _BV(WDIE) |             _BV(WDP2) | _BV(WDP1) | _BV(WDP0), // ~2048 ms
  _BV(WDIE) |             _BV(WDP2) | _BV(WDP1)            , // ~1024 ms
  _BV(WDIE) |             _BV(WDP2) |             _BV(WDP0), //  ~512 ms
  _BV(WDIE) |             _BV(WDP2)                        , //  ~256 ms
  _BV(WDIE) |                         _BV(WDP1) | _BV(WDP0), //  ~128 ms
  _BV(WDIE) |                         _BV(WDP1)            , //   ~64 ms
  _BV(WDIE) |                                     _BV(WDP0), //   ~32 ms
  _BV(WDIE)                                                  //   ~16 ms
}; // Remember, WDT clock is uncalibrated, times are "ish"

void ubersleep(uint32_t ms) {
  if(ms == 0) return;
  tablePos      = 0;                   // Reset WDT config stuff to
  sleepInterval = maxSleepInterval;    // longest interval to start
  configWDT(ms);                       // Set up for requested time
  set_sleep_mode(SLEEP_MODE_PWR_DOWN); // Deepest sleep mode
  sleep_enable();
  while(sleepTime && (tablePos < sizeof(cfg))) sleep_mode();
  noInterrupts();                      // WDT off (timing critical)...
  MCUSR &= ~_BV(WDRF);
  WDTCR  = 0;
  interrupts();
}

static void configWDT(uint32_t newTime) {
  sleepTime = newTime; // Total sleep time remaining (ms)
  // Find next longest WDT interval that fits within remaining time...
  while(sleepInterval > newTime) {
    sleepInterval /= 2;                          // Each is 1/2 previous
    if(++tablePos >= sizeof(cfg)) return;        // No shorter intervals
  }
  uint8_t bits = pgm_read_byte(&cfg[tablePos]);  // WDT config bits for time
  noInterrupts();                                // Timing-critical...
  MCUSR &= ~_BV(WDRF);
  WDTCR  =  _BV(WDCE) | _BV(WDE);                // WDT change enable
  WDTCR  =  bits;                                // Interrupt + prescale
  interrupts();
}

ISR(WDT_vect) { // Watchdog timeout interrupt
  configWDT(sleepTime - sleepInterval); // Subtract, setup next cycle...
}
