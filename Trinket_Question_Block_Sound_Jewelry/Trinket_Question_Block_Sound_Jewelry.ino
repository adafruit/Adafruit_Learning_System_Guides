/* -----------------------------------------------------------------------
   Super Mario Bros-inspired coin sound for Adafruit Trinket & Gemma.

   Requires piezo speaker between pins 0 & 1, vibration sensor or
   momentary button between pin 2 & GND.  Tap for "bling!" noise.
   Optional LED+resistor on pin 4 for light during play.

   Runs equally well on a 16 MHz or 8 MHz Trinket, or on Gemma.  Use what
   you've got, no need to get all HOMG MOAR MEGAHURTZ!!1! about it.  :)

   This is NOT good beginner code to learn from...there's very little
   resemblance to a "normal" Arduino sketch as we poke around with ATtiny
   peripheral registers directly; will NOT run on other Arduino boards.
   Commented like mad regardless, might discover fun new stuff.

   Written by Phillip Burgess for Adafruit Industries.  Public domain.
   ----------------------------------------------------------------------- */

#include <avr/power.h>
#include <avr/sleep.h>

// These variables are declared 'volatile' because their values may change
// inside interrupts, independent of the mainline code.  This keeps the
// optimizer from removing lines it would otherwise regard as unnecessary.
// 'quietness' is basically the inverse of volume -- the code was a little
// smaller expressing it this way. 0 = max volume, 127 = quietest.
// 'count' is incremented while generating a square wave.  Used for timing,
// and bit 0 indicates whether this is the 'high' or 'low' part of the wave.
volatile uint8_t  quietness;
volatile uint16_t count;

// ONE-TIME INITIALIZATION -----------------------------------------------

void setup() {
#if (F_CPU == 16000000L)
  clock_prescale_set(clock_div_1);
#endif

  // ATtiny85 has a special high-speed 64 MHz PLL mode than can be used
  // as an input to Timer/Counter 1.  The ATmega chips don't have this!
  // Requires a little song and dance to set this up...
  PLLCSR |= _BV(PLLE);           // Enable 64 MHz PLL
  delayMicroseconds(100);        // Allow time to stabilize
  while(!(PLLCSR & _BV(PLOCK))); // Wait for it...wait for it...
  PLLCSR |= _BV(PCKE);           // Timer1 source = PLL!

  // Enable Timer/Counter 1 PWM, OC1A & !OC1A output pins, 1:1 prescale.
  GTCCR = TIMSK = 0; // Timer interrupts OFF
  OCR1C = 255;       // 64M/256 = 250 KHz
  OCR1A = 127;       // 50% duty at start = off
  TCCR1 = _BV(PWM1A) | _BV(COM1A0) | _BV(CS10);

  // Normally the Arduino core library uses Timer/Counter 1 for functions
  // like delay(), millis(), etc.  Having changed the cycle time above,
  // and turning off the overflow interrupt, these functions won't work
  // after this.  Keeping track of time is our own responsibility now.

  // The Timer/Counter 1 PWM output doesn't time the output square wave;
  // the frequency (250 KHz) is much too fast for that.  Rather, the
  // speaker itself physically acts as a filter, with the average duty
  // cycle determining the cone position; center=off, 0,255=extremes.
  // A separate timer (using the actual sound frequency) then toggles the
  // duty cycle to adjust amplitude, providing volume control...

  // Configure Timer/Counter 0 for PWM (no interrupt enabled yet).
  TCCR0A = _BV(WGM01) | _BV(WGM00); // PWM mode

  // An external interrupt (INT0, pin 2 pulled to GND) wakes the chip
  // from sleep mode to play the sound.
  MCUCR &= ~(_BV(ISC01) | _BV(ISC00)); // Low level (GND) trigger
}

// -----------------------------------------------------------------------

void loop() {

  // To maximize power savings, pins are set to inputs with pull-up
  // resistors enabled (except for pins 1&4, because LEDs).
  DDRB = B00000000; PORTB = B00101101;

  // The chip is then put into a very low-power sleep mode...
  power_all_disable();                 // All peripherals off
  GIMSK |=  _BV(INT0);                 // Enable external interrupt
  set_sleep_mode(SLEEP_MODE_PWR_DOWN); // Deepest sleep
  sleep_mode();                        // Stop, will resume here on wake
  // Code resumes when pin 2 is pulled to GND (e.g. button press).
  GIMSK &= ~_BV(INT0);                 // Disable external interrupt

  // Only the two timer/counters are re-enabled on wake.  All other
  // peripheras remain off for power saving.  This means no ADC, I2C, etc.
  power_timer0_enable();
  power_timer1_enable();

  DDRB  = B00010011; // Output on pins 0,1 (piezo speaker), 4 (LED)
  PORTB = B00010000; // LED on

  // Play first note.  B5 = 987.77 Hz (round up to 988)
  pitch(988); // Sets up Timer/Counter 1 for this frequency
  // The pitch() function configures the timer for 2X the frequency, an
  // interrupt then alternates between the 'high' and 'low' parts of the
  // square wave.  988 Hz = 1976 interrupts/sec.  'count' keeps track.
  // First note is 0.083 sec.  1976 * 0.083 = 164 interrupt counts.
  // Combined length of notes is 0.92 sec, or 1818 interrupt counts at
  // this frequency.  The amplitude (volume) fades linearly through the
  // duration of both notes.  So this calculates the portion of that drop
  // through the first note...
  while(count < 164) quietness = 128L * count / 1818;
  // This uses fixed-point (integer) math, because floating-point is slow
  // on the AVR and uses lots of program space.  A large integer multiply
  // (32-bit intermediate result) precedes an integer division, result is
  // effectively equal to floating-point multiply of 128.0 * 0.0 to 1.0.

  pitch(1319); // Init second note.  E6 = 1318.51 Hz, round up to 1319.
  // 1319 Hz tone = 2638 Hz interrupt.  To maintain the duration and make
  // the volume-scaling math continue from the prior level, counts need to
  // be adjusted to take this timing change into account.  The total
  // length at this rate would be 2638 * 0.92 = 2427 counts, and first
  // note duration would have been 2638 * 0.083 = 219 counts...
  count = 219;
  // Rather than counting up to the duration, just keep playing until the
  // effective volume is zero.
  do {
    quietness = 128L * count / 2427;
  } while(quietness < 127);

  // Finished playing both notes.  Disable the timer interrupt...
  TIMSK = 0;

  // Before finishing, the piezo speaker is eased in a controlled manner
  // from the volume-neutral position (127) to its off position (0) in
  // order to avoid an audible 'pop' when the code goes to sleep.
  for(uint8_t i=127; i--; ) {
    OCR1A = i;                                     // Speaker position
    for(volatile uint16_t x = F_CPU/32000; --x; ); // Easy, not too fast
  }
}

// -----------------------------------------------------------------------

// These tables list available timer/counter prescaler values and their
// configuration bit settings.  Normally I'd PROGMEM these, but for these
// short tables the code actually compiles a little smaller this way!
const uint16_t prescale[] = { 1, 8, 64, 256, 1024 };
const uint8_t  tccr[] = {
  _BV(WGM02)                         | _BV(CS00),
  _BV(WGM02)             | _BV(CS01),
  _BV(WGM02)             | _BV(CS01) | _BV(CS00),
  _BV(WGM02) | _BV(CS02),
  _BV(WGM02) | _BV(CS02)             | _BV(CS00),
};

// Configure Timer/Counter 0 for the requested frequency
void pitch(uint16_t freq) {

  uint8_t  i;
  uint16_t f2 = freq << 1; // 2X frequency
  uint32_t o;

  // Find CPU prescale that can accommodate requested frequency
  for(i=0; i < (sizeof(prescale) / sizeof(prescale[0])) &&
    (o = (((F_CPU / (uint32_t)prescale[i]) + freq) /
          (uint32_t)f2) - 1) >= 256L; i++);

  TCCR0B = tccr[i];     // Prescale config bits
  OCR0A  = (uint8_t)o;  // PWM interval for 2X freq
  count  = 0;           // Reset waveform counter
  TIMSK  = _BV(OCIE0A); // Enable compare match interrupt
}

// TIMER0_OVF vector is already claimed by the Arduino core library,
// can't use that.  So the compare vector is used instead...
ISR(TIMER0_COMPA_vect) {
  // Bit 0 of count indicates high or low side of square wave.
  // OCR1A sets average speaker pos, quietness adjusts amplitude.
  OCR1A = (count++ & 1) ? 255 - quietness : quietness;
}