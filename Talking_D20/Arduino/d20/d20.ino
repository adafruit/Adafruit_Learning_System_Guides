// Talking D20 sketch.  Uses the following Adafruit parts:
//
// - Pro Trinket 3V or 5V (adafruit.com/product/2010 or 2000)
// - 150 mAh LiPoly battery (1317)
// - LiPoly backpack (2124)
// - MMA8451 accelerometer (2019)
// - 2.5W class D mono amp (2130)
// - Audio FX Mini sound board (2342 or 2341)
//
// Needs Adafruit_MMA8451, Adafruit_Sensor and Adafruit_Soundboard libs:
// github.com/adafruit
// 3D-printable enclosure can be downloaded from Thingiverse:
// (add link here)

#include <Wire.h>
#include <Adafruit_MMA8451.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_Soundboard.h>
#include <limits.h>
#include <avr/power.h>
#include <avr/sleep.h>

// A few pins are configurable; selections here were to make wiring diagram
// simpler.  Other pins MUST go to designated spots, e.g. accelerometer pins
// I2, SDA and SCL to Pro Trinket pins 3, A4 and A5, TX/RX to Audio FX, etc.
#define AMP_SHUTDOWN A3 // "SD" on amplifier board
#define AUDIO_ACT     4 // "Act" on Audio FX
#define AUDIO_RESET   8 // "Rst" on Audio FX
#define LED          13 // Pro Trinket onboard LED

// Need access to some MMA8451 registers not defined in .h file:
#define MMA8451_REG_FF_MT_CFG   0x15
#define MMA8451_REG_FF_MT_SRC   0x16
#define MMA8451_REG_FF_MT_THS   0x17
#define MMA8451_REG_FF_MT_COUNT 0x18
#define MMA8451_REG_CTRL_REG3   0x2C
#define MMA8451_I2C_ADDR        0x1D // If pin A -> GND, use 0x1C instead

Adafruit_MMA8451    mma = Adafruit_MMA8451();
Adafruit_Soundboard sfx = Adafruit_Soundboard(&Serial, NULL, AUDIO_RESET);

char filename[12] = "        OGG"; // Tail end of filename NEVER changes

// PROGMEM string arrays are wretched, and sfx.playTrack() expects a
// goofball fixed-length space-padded filename...we take care of both by
// declaring all the filenames inside one big contiguous PROGMEM string
// (notice there are no commas here, it's all concatenated), and copying
// an 8-byte section as needed into filename[].  Some waste, but we're
// not hurting for space.  If you change or add any filenames, they MUST
// be padded with spaces to 8 characters, else there will be...trouble.  
static const char PROGMEM bigStringTable[] =   // play() index
  "01      " "02      " "03      " "04      "  //  0- 3
  "05      " "06      " "07      " "08      "  //  4- 7
  "09      " "10      " "11      " "12      "  //  8-11
  "13      " "14      " "15      " "16      "  // 12-15
  "17      " "18      " "19      " "20      "  // 16-19
  "ANNC1   " "ANNC2   " "ANNC3   "             // 20-22
  "BAD1    " "BAD2    " "BAD3    "             // 23-25
  "GOOD1   " "GOOD2   " "GOOD3   "             // 26-28
  "STARTUP " "03ALT   " "BATT1   " "BATT2   "; // 29-32

// INITIALIZATION ----------------------------------------------------------

// If there's an error during startup, LED flashes to indicate status
void fail(uint16_t ms) {
  for(uint8_t x=0;;) {
    digitalWrite(LED, ++x & 1);
    delay(ms);
  }
}

void dummyISR(void) { } // Empty ISR function to make attachInterrupt happy

void setup(void) {
  pinMode(LED, OUTPUT);
  digitalWrite(LED, HIGH);         // LED on at startup
  Serial.begin(9600);              // Start serial connection
  uint8_t sfxInit = sfx.reset();   // Contact Audio FX board
  if(!sfxInit)     fail(250);      // Audio FX error?  Slow blink
  if(!mma.begin()) fail(100);      // Init accelerometer, fast blink = error
  mma.setRange(MMA8451_RANGE_2_G); // Set accelerometer sensitivity (2G)
  digitalWrite(LED, LOW);          // LED off = good init!
  play(29);                        // Startup greeting
  audioOff();                      // Turn off amplifier & Audio FX
  randomSeed(analogRead(0));       // Seed random() from floating input

  // Configure high-to-low interrupt detect on Arduino pin 3.
  // Accelerometer will be set up to generate freefall interrupt.
  pinMode(3, INPUT_PULLUP);
  attachInterrupt(1, dummyISR, FALLING);
  // 'FALLING' above refers to the interrupt signal logic level change --
  // high to low -- the fact that we're using this to sense physical
  // 'falling' is a coincidence; don't be misled by the syntax!

  wait(); // Power down everything and wait for interrupt
}

// MAIN LOOP ---------------------------------------------------------------
// Active when an interrupt occurs and chip is awakened...

uint8_t batt = 0; // Low battery announcement counter

void loop() {
  // audioOn() needs a moment to start up before anything plays,
  // stabilize() takes time anyway, so exploit that rather than delay()ing.
  audioOn();
  if(stabilize(250, 3000)) {
    uint8_t f = getFace();
  
    if(f == 2) {              // If '3' face
      if(!random(10)) {       // 1-in-10 chance of...
        f = 30;               // Alternate 'face 3' track
      }                       // LOL
    }
  
    play(20 + random(3));     // One of 3 random announcements
  
    play(f);                  // Face #
  
    if(f != 30) {             // If not the alt face...
      if(f <= 3) {            // 0-3 (1-4) = bad
        play(23 + random(3)); // Random jab
      } else if(f >= 16) {    // 16-19 (17-20) = good
        play(26 + random(3)); // Random praise
      }
    }
  
    // Estimate voltage from battery, report if low.
    // This is "ish" and may need work.
    if((readVoltage() < 3000) && !(batt++ & 1)) { // Annc on every 2nd roll
      delay(500);
      play(31 + random(2));
    }
  }

  audioOff();
  (void)readReg(0x16); // Clear interrupt
  wait();              // Return to power-down state
}

// AUDIO STUFF -------------------------------------------------------------

// Activating the Audio FX board and amplifier only when needed saves
// a TON of battery life.

void audioOn(void) {
  pinMode(AMP_SHUTDOWN, INPUT_PULLUP);
  pinMode(AUDIO_RESET , INPUT_PULLUP);
}

void audioOff(void) {
  digitalWrite(AMP_SHUTDOWN, LOW);
  pinMode(     AMP_SHUTDOWN, OUTPUT);
  digitalWrite(AUDIO_RESET , LOW); // Hold low = XRESET (low power)
  pinMode(     AUDIO_RESET , OUTPUT);
}

void play(uint16_t i) {
  memcpy_P(filename, &bigStringTable[i * 8], 8);

  sfx.playTrack(filename);
  delay(250); // Need this -- some delay before ACT LED is valid
  while(digitalRead(AUDIO_ACT) == LOW);  // Wait for sound to finish
}

// ACCELEROMETER STUFF -----------------------------------------------------

// Waits for accelerometer output to stabilize, indicating movement stopped
boolean stabilize(uint32_t ms, uint32_t timeout) {
  uint32_t startTime, prevTime, currentTime;
  int32_t  prevX, prevY, prevZ;
  int32_t  dX, dY, dZ;

  // Get initial orientation and time
  mma.read();
  prevX    = mma.x;
  prevY    = mma.y;
  prevZ    = mma.z;
  prevTime = startTime = millis();

  // Then make repeated readings until orientation settles down.
  // A normal roll should only take a second or two...if things do not
  // stabilize before timeout, probably being moved or carried.
  while(((currentTime = millis()) - startTime) < timeout) {
    if((currentTime - prevTime) >= ms) return true; // Stable!
    mma.read();
    dX = mma.x - prevX; // X/Y/Z delta from last stable position
    dY = mma.y - prevY;
    dZ = mma.z - prevZ;
    // Compare distance.  sqrt() can be avoided by squaring distance
    // to be compared; about 100 units on X+Y+Z axes ((100^2)*3 = 30K)
    if((dX * dX + dY * dY + dZ * dZ) >= 30000) { // Big change?
      prevX    = mma.x;    // Save new position
      prevY    = mma.y;
      prevZ    = mma.z;
      prevTime = millis(); // Reset timer
    }
  }

  return false; // Didn't stabilize, probably false trigger
}

// Face gravity vectors (accelerometer installed FACE DOWN)
static const int16_t PROGMEM gtable[20][3] = {
  {  1475, -1950,  3215 }, //  1
  { -2420,  3295,  -775 }, //  2
  {  3715, -1175   -795 }, //  3
  { -3830, -1125,  -920 }, //  4
  { -2440,   875,  3105 }, //  5
  {   -50, -2395, -3265 }, //  6
  {  2290,   770,  3210 }, //  7
  {  1380,  2105, -3225 }, //  8
  {    50, -3995,  -845 }, //  9
  {  2300,  3310,  -695 }, // 10
  { -2430, -3190,   610 }, // 11
  {   -25,  4045,   835 }, // 12
  { -1515, -2030,  3160 }, // 13
  { -2425,  -665, -3250 }, // 14
  {   -65,  2470,  3215 }, // 15
  {  2260,  -805, -3200 }, // 16
  {  3740,  1200,   775 }, // 17
  { -3820,  1280,   715 }, // 18
  {  2235, -3250,   785 }, // 19
  { -1605,  2080, -3235 }  // 20
};

// Find nearest face to accelerometer reading.
uint8_t getFace(void) {
  int32_t  dX, dY, dZ, d, dMin = LONG_MAX;
  int16_t  fX, fY, fZ;
  uint8_t  i, iMin = 0;
  uint16_t addr = 0;

  mma.read();
  for(i=0; i<20; i++) { // For each face...
    fX = pgm_read_word(&gtable[i][0]); // Read face X/Y/Z
    fY = pgm_read_word(&gtable[i][1]); // from PROGMEM
    fZ = pgm_read_word(&gtable[i][2]);
    dX = mma.x - fX; // Delta between accelerometer & face
    dY = mma.y - fY;
    dZ = mma.z - fZ;
    d  = dX * dX + dY * dY + dZ * dZ; // Distance^2
    // Check if this face is the closest match so far.  Because
    // we're comparing RELATIVE distances, sqrt() can be avoided.
    if(d < dMin) { // New closest match?
      dMin = d;    // Save closest distance^2
      iMin = i;    // Save index of closest match
    }
  }

  return iMin; // Index of closest matching face
}

// A couple of private functions from accelerometer library need
// to be duplicated here:

void writeReg(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(MMA8451_I2C_ADDR);
  Wire.write(reg);
  Wire.write(value);
  Wire.endTransmission();
}

uint8_t readReg(uint8_t reg) {
  Wire.beginTransmission(MMA8451_I2C_ADDR);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(MMA8451_I2C_ADDR, 1);
  if(!Wire.available()) return -1;
  return Wire.read();
}

// POWER-SAVING STUFF ------------------------------------------------------

// Audio FX in XRESET state saves ~13 mA
// Amplifier shutdown saves ~5 mA
// MCU deep sleep w/peripherals off saves ~9 mA
// Circuit in sleep state draws about 8.6 mA w/3V Pro Trinket, 10.6 mA w/5V
// The accelerometer is not currently put into a reduced-power state;
// docs are a bit confusing about this.  Potential power saving there looks
// minimal, like 0.2 mA, so I'm not too worried about this.
// Full-on, circuit playing audio peaks around 220 mA.

void wait(void) {
  // Configure the accelerometer to issue an interrupt when free-fall
  // is detected (which we'll interpret as initiating a roll).  Free-fall
  // detection is the same feature as used in some laptops to park spinning
  // disks before impact.  Cool, huh?  It's REALLY good at this...can
  // distinguish between a shake and a drop, we don't need to process a
  // bunch of accelerometer readings...in fact the MCU is put to sleep
  // while waiting.  Being a somewhat esoteric function, free-fall detect
  // isn't provided in the normal Adafruit_MMA8451 library...we need to set
  // up registers manually.  This sequence mostly comes from a Freescale
  // application note, just tweaking thresholds slightly:
  writeReg(MMA8451_REG_CTRL_REG1  , 0x20); // Standby
  writeReg(MMA8451_REG_FF_MT_CFG  , 0xB8); // X+Y+Z + latch
  writeReg(MMA8451_REG_FF_MT_THS  , 0x02); // < 0.2G
  writeReg(MMA8451_REG_FF_MT_COUNT, 0x05); // 5 count debounce
  writeReg(MMA8451_REG_CTRL_REG3  , 0x08); // Freefall wake, active low
  writeReg(MMA8451_REG_CTRL_REG4  , 0x04); // Enable interrupt
  writeReg(MMA8451_REG_CTRL_REG5  , 0x00); // Route to I2 pin
  uint8_t a = readReg(MMA8451_REG_CTRL_REG1) | 0x01;
  writeReg(MMA8451_REG_CTRL_REG1, a);      // Enable

  DIDR0 = 0x3F; DIDR1 = 0x03;          // Disable digital input on analog
  power_all_disable();                 // Disable ALL AVR peripherals
  set_sleep_mode(SLEEP_MODE_PWR_DOWN); // Deepest sleep mode
  sleep_enable();
  interrupts();
  sleep_mode();                        // Power-down MCU

  // Code resumes here on interrupt.  Re-enable peripherals used by sketch:
  power_twi_enable();    // Used by Wire lib (accelerometer)
  Wire.begin();          // Need to re-init I2C
  power_usart0_enable(); // Used by Serial (to Audio FX)
  power_timer0_enable(); // Used by delay(), millis(), etc.
}

// Battery monitoring idea adapted from JeeLabs article:
// jeelabs.org/2012/05/04/measuring-vcc-via-the-bandgap/
// Code from Adafruit TimeSquare project.
static uint16_t readVoltage() {
  int      i, prev;
  uint8_t  count;
  uint16_t mV;

  power_adc_enable();
  ADMUX  = _BV(REFS0) |                        // AVcc voltage reference
           _BV(MUX3)  | _BV(MUX2) | _BV(MUX1); // Bandgap (1.8V) input
  ADCSRA = _BV(ADEN)  |             // Enable ADC
           _BV(ADPS2) | _BV(ADPS1); // 1/64 prescaler (8 MHz -> 125 KHz)
  // Datasheet notes that the first bandgap reading is usually garbage as
  // voltages are stabilizing.  It practice, it seems to take a bit longer
  // than that (perhaps due to sleep).  Tried various delays, but this was
  // still inconsistent and kludgey.  Instead, repeated readings are taken
  // until four concurrent readings stabilize within 10 mV.
  for(prev=9999, count=0; count<4; ) {
    for(ADCSRA |= _BV(ADSC); ADCSRA & _BV(ADSC); ); // Start, await ADC conv.
    i  = ADC;                                       // Result
    mV = i ? (1100L * 1023 / i) : 0;                // Scale to millivolts
    if(abs((int)mV - prev) <= 10) count++;   // +1 stable reading
    else                          count = 0; // too much change, start over
    prev = mV;
  }
  ADCSRA = 0; // ADC off
  power_adc_disable();
  return mV;
}

