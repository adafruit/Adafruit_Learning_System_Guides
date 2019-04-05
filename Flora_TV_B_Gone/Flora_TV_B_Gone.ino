/*
Flora TV-B-Gone

Code updated for Flora's 32u4 microcontroller by Phillip Burgess for Adafruit Industries

Complete instructions: http://learn.adafruit.com/flora-tv-b-gone/

The hardware for this project uses an Adafruit Flora (Arduino-compatible 32u4):
 Connect the base of an NPN bipolar transistor to pin 3, marked "SCL" on Flora (RLED).
 Connect the collector pin of the transistor to ground (Marked "GND" on Flora).
 Connect the transistor's emitter to the positive lead of an IR LED, and connect the LED's negative leg to ground through a 100-ohm resistor.
 Connect a pushbutton between pin D9 (TRIGGER) and ground.
 Pin 5 (REGIONSWITCH) is floating for North America, or wired to ground for Europe.

-------------
based on Ken Shirriff's port of TV-B-Gone to Arduino, version 1.2, Oct 23 2010
http://www.arcfn.com/2009/12/tv-b-gone-for-arduino.html

The original code is:
TV-B-Gone Firmware version 1.2
 for use with ATtiny85v and v1.2 hardware
 (c) Mitch Altman + Limor Fried 2009
 Last edits, August 16 2009


 I added universality for EU or NA,
 and Sleep mode to Ken's Arduino port
      -- Mitch Altman  18-Oct-2010
 Thanks to ka1kjz for the code for adding Sleep
      <http://www.ka1kjz.com/561/adding-sleep-to-tv-b-gone-code/>

 With some code from:
 Kevin Timmerman & Damien Good 7-Dec-07

 Distributed under Creative Commons 2.5 -- Attib & Share Alike

 */

#include "main.h"
#include <avr/sleep.h>
#include <avr/pgmspace.h>

void xmitCodeElement(uint16_t ontime, uint16_t offtime, uint8_t PWM_code );
void quickflashLEDx( uint8_t x );
void delay_ten_us(uint16_t us);
void quickflashLED( void );
uint8_t read_bits(uint8_t count);

/*
This project transmits a bunch of TV POWER codes, one right after the other,
 with a pause in between each.  (To have a visible indication that it is
 transmitting, it also pulses a visible LED once each time a POWER code is
 transmitted.)  That is all TV-B-Gone does.  The tricky part of TV-B-Gone
 was collecting all of the POWER codes, and getting rid of the duplicates and
 near-duplicates (because if there is a duplicate, then one POWER code will
 turn a TV off, and the duplicate will turn it on again (which we certainly
 do not want).  I have compiled the most popular codes with the
 duplicates eliminated, both for North America (which is the same as Asia, as
 far as POWER codes are concerned -- even though much of Asia USES PAL video)
 and for Europe (which works for Australia, New Zealand, the Middle East, and
 other parts of the world that use PAL video).

 Before creating a TV-B-Gone Kit, I originally started this project by hacking
 the MiniPOV kit.  This presents a limitation, based on the size of
 the Atmel ATtiny2313 internal flash memory, which is 2KB.  With 2KB we can only
 fit about 7 POWER codes into the firmware's database of POWER codes.  However,
 the more codes the better! Which is why we chose the ATtiny85 for the
 TV-B-Gone Kit.

 This version of the firmware has the most popular 100+ POWER codes for
 North America and 100+ POWER codes for Europe. You can select which region
 to use by soldering a 10K pulldown resistor.
 */


/*
This project is a good example of how to use the AVR chip timers.
 */

extern const *NApowerCodes[];
extern const *EUpowerCodes[];
extern const struct IrCode code_na000Code PROGMEM;
extern uint8_t num_NAcodes, num_EUcodes;

/* This function is the 'workhorse' of transmitting IR codes.
 Given the on and off times, it turns on the PWM output on and off
 to generate one 'pair' from a long code. Each code has ~50 pairs! */
void xmitCodeElement(uint16_t ontime, uint16_t offtime, uint8_t PWM_code )
{
#ifdef __AVR_ATmega32U4__
  TCNT0 = 0;
#else
  TCNT2 = 0;
#endif
  if(PWM_code) {
    pinMode(IRLED, OUTPUT);
    // Fast PWM, setting top limit, divide by 8
    // Output to pin 3
#ifdef __AVR_ATmega32U4__
  #if (IRLED == 11)
    TCCR0A = _BV(COM0A1) | _BV(COM0A0) | _BV(WGM01) | _BV(WGM00);
  #elif (IRLED == 3)
    TCCR0A = _BV(COM0B1) | _BV(COM0B0) | _BV(WGM01) | _BV(WGM00);
  #else
    #error "IR LED must be on Leonardo digital pin 3 or 11."
  #endif
    TCCR0B = _BV(WGM02) | _BV(CS01);
#else
    TCCR2A = _BV(COM2A0) | _BV(COM2B1) | _BV(WGM21) | _BV(WGM20);
    TCCR2B = _BV(WGM22) | _BV(CS21);
#endif
  }
  else {
    // However some codes dont use PWM in which case we just turn the IR
    // LED on for the period of time.
    digitalWrite(IRLED, HIGH);
  }

  // Now we wait, allowing the PWM hardware to pulse out the carrier
  // frequency for the specified 'on' time
  delay_ten_us(ontime);

  // Now we have to turn it off so disable the PWM output
#ifdef __AVR_ATmega32U4__
  TCCR0A = 0;
  TCCR0B = 0;
#else
  TCCR2A = 0;
  TCCR2B = 0;
#endif
  // And make sure that the IR LED is off too (since the PWM may have
  // been stopped while the LED is on!)
  digitalWrite(IRLED, LOW);

  // Now we wait for the specified 'off' time
  delay_ten_us(offtime);
}

/* This is kind of a strange but very useful helper function
 Because we are using compression, we index to the timer table
 not with a full 8-bit byte (which is wasteful) but 2 or 3 bits.
 Once code_ptr is set up to point to the right part of memory,
 this function will let us read 'count' bits at a time which
 it does by reading a byte into 'bits_r' and then buffering it. */

uint8_t bitsleft_r = 0;
uint8_t bits_r=0;
PGM_P code_ptr;

// we cant read more than 8 bits at a time so dont try!
uint8_t read_bits(uint8_t count)
{
  uint8_t i;
  uint8_t tmp=0;

  // we need to read back count bytes
  for (i=0; i<count; i++) {
    // check if the 8-bit buffer we have has run out
    if (bitsleft_r == 0) {
      // in which case we read a new byte in
      bits_r = pgm_read_byte(code_ptr++);
      // and reset the buffer size (8 bites in a byte)
      bitsleft_r = 8;
    }
    // remove one bit
    bitsleft_r--;
    // and shift it off of the end of 'bits_r'
    tmp |= (((bits_r >> (bitsleft_r)) & 1) << (count-1-i));
  }
  // return the selected bits in the LSB part of tmp
  return tmp;
}


/*
The C compiler creates code that will transfer all constants into RAM when
 the microcontroller resets.  Since this firmware has a table (powerCodes)
 that is too large to transfer into RAM, the C compiler needs to be told to
 keep it in program memory space.  This is accomplished by the macro PROGMEM
 (this is used in the definition for powerCodes).  Since the C compiler assumes
 that constants are in RAM, rather than in program memory, when accessing
 powerCodes, we need to use the pgm_read_word() and pgm_read_byte macros, and
 we need to use powerCodes as an address.  This is done with PGM_P, defined
 below.
 For example, when we start a new powerCode, we first point to it with the
 following statement:
 PGM_P thecode_p = pgm_read_word(powerCodes+i);
 The next read from the powerCode is a byte that indicates the carrier
 frequency, read as follows:
 const uint8_t freq = pgm_read_byte(code_ptr++);
 After that is a byte that tells us how many 'onTime/offTime' pairs we have:
 const uint8_t numpairs = pgm_read_byte(code_ptr++);
 The next byte tells us the compression method. Since we are going to use a
 timing table to keep track of how to pulse the LED, and the tables are
 pretty short (usually only 4-8 entries), we can index into the table with only
 2 to 4 bits. Once we know the bit-packing-size we can decode the pairs
 const uint8_t bitcompression = pgm_read_byte(code_ptr++);
 Subsequent reads from the powerCode are n bits (same as the packing size)
 that index into another table in ROM that actually stores the on/off times
 const PGM_P time_ptr = (PGM_P)pgm_read_word(code_ptr);
 */

uint16_t ontime, offtime;
uint8_t i,num_codes, Loop;
uint8_t region;
uint8_t startOver;

#define FALSE 0
#define TRUE 1

void setup()   {
  Serial.begin(9600);
  if (DEBUG) {
    while (!Serial);
    delay(100);
    Serial.println("TV B Gone");
  }

#ifdef __AVR_ATmega32U4__
  // Timer0 is used on Arduino Leonardo (there is no Timer2).
  // This means delay(), millis() etc. are not available,
  // but they're currently not being used by this code.
  TIMSK0 = 0; // Disable Timer0 interrupt
  TCCR0A = 0;
  TCCR0B = 0;
#else
  TCCR2A = 0;
  TCCR2B = 0;
#endif

  digitalWrite(LED, LOW);
  digitalWrite(IRLED, LOW);
  digitalWrite(DBG, LOW);     // debug
  pinMode(LED, OUTPUT);
  pinMode(IRLED, OUTPUT);
  pinMode(DBG, OUTPUT);       // debug
  pinMode(REGIONSWITCH, INPUT_PULLUP);
  pinMode(TRIGGER, INPUT_PULLUP);

  delay_ten_us(5000);            // Let everything settle for a bit

  // determine region
  if (digitalRead(REGIONSWITCH)) {
    region = NA;
    if (DEBUG) Serial.println(F("NA"));
  }
  else {
    region = EU;
    if (DEBUG) Serial.println(F("EU"));
  }

  // Indicate how big our database is
  if (DEBUG) {
    Serial.print(F("\n\rNA Codesize: "));
    Serial.println(num_NAcodes, DEC);
    Serial.print(F("\n\rEU Codesize: "));
    Serial.println(num_EUcodes, DEC);

    //uint16_t addr = &code_na000Code;
    //Serial.print("Code NA000: $");
    //Serial.println(addr, HEX);

  }


  // Tell the user what region we're in  - 3 flashes is NA, 6 is EU
  delay_ten_us(65500); // wait maxtime
  delay_ten_us(65500); // wait maxtime
  delay_ten_us(65500); // wait maxtime
  delay_ten_us(65500); // wait maxtime
  quickflashLEDx(3);
  if (region == EU) {
    quickflashLEDx(3);
  }
}

void sendAllCodes() {
Start_transmission:
  // startOver will become TRUE if the user pushes the Trigger button while transmitting the sequence of all codes
  startOver = FALSE;

  // determine region from REGIONSWITCH: 1 = NA, 0 = EU
  if (digitalRead(REGIONSWITCH)) {
    region = NA;
    num_codes = num_NAcodes;
  }  else {
    region = EU;
    num_codes = num_EUcodes;
  }

  // for every POWER code in our collection
  for (i=0 ; i < num_codes; i++) {
    uint16_t data_ptr;

    // print out the code # we are about to transmit
    if (DEBUG) {
      Serial.print("\nCode #: ");
      Serial.println(i);
    }

    // point to next POWER code, from the right database
    if (region == NA) {
      data_ptr = NApowerCodes[i];
    }
    else {
      data_ptr = EUpowerCodes[i];
    }

    // print out the address in ROM memory we're reading
    if (DEBUG) {
      Serial.print("Addr: $");
      Serial.println((uint16_t)data_ptr, HEX);
    }
    
    // Read the carrier frequency from the first byte of code structure
    const uint8_t freq = pgm_read_byte(data_ptr++);
    // set OCR for Timer1 to output this POWER code's carrier frequency
#ifdef __AVR_ATmega32U4__
    OCR0A = freq;
    OCR0B = freq / 3; // 33% duty cycle
#else
    OCR2A = freq;
    OCR2B = freq / 3; // 33% duty cycle
#endif

    // Print out the frequency of the carrier and the PWM settings
    if (DEBUG) {
      Serial.print("OCR1: ");  Serial.println(freq);
      uint16_t x = (freq+1) * 8;
      Serial.print("Freq: "); Serial.println(F_CPU/x);
    }

    // Get the number of pairs, the second byte from the code struct
    const uint8_t numpairs = pgm_read_byte(data_ptr++);
    if (DEBUG) {
      Serial.print(F("On/off pairs: "));
      Serial.println(numpairs);
    }

    // Get the number of bits we use to index into the timer table
    // This is the third byte of the structure
    const uint8_t bitcompression = pgm_read_byte(data_ptr++);
    if (DEBUG) {
      Serial.print(F("\n\rCompression: "));
      Serial.println(bitcompression, DEC);
    }
    
    // Get pointer (address in memory) to pulse-times table
    // The address is 16-bits (2 byte, 1 word)
    PGM_P time_ptr = (PGM_P)pgm_read_word(data_ptr);
    data_ptr+=2;
    code_ptr = (PGM_P)pgm_read_word(data_ptr);

    // Transmit all codeElements for this POWER code
    // (a codeElement is an onTime and an offTime)
    // transmitting onTime means pulsing the IR emitters at the carrier
    // frequency for the length of time specified in onTime
    // transmitting offTime means no output from the IR emitters for the
    // length of time specified in offTime

#if 0
    // print out all of the pulse pairs
    for (uint8_t k=0; k<numpairs; k++) {
      uint8_t ti;
      ti = (read_bits(bitcompression)) * 4;
      // read the onTime and offTime from the program memory
      ontime = pgm_read_word(time_ptr+ti);
      offtime = pgm_read_word(time_ptr+ti+2);
      if (DEBUG) {
        Serial.print("ti = "); Serial.print(ti>>2);
        Serial.print("\tPair = "); Serial.print(ontime);
        Serial.print(","); Serial.println(offtime);
      }
    }
    continue;
#endif

    // For EACH pair in this code....
    cli();
    for (uint8_t k=0; k<numpairs; k++) {
      uint16_t ti;

      // Read the next 'n' bits as indicated by the compression variable
      // The multiply by 4 because there are 2 timing numbers per pair
      // and each timing number is one word long, so 4 bytes total!
      ti = (read_bits(bitcompression)) * 4;

      // read the onTime and offTime from the program memory
      ontime = pgm_read_word(time_ptr+ti);  // read word 1 - ontime
      offtime = pgm_read_word(time_ptr+ti+2);  // read word 2 - offtime
      // transmit this codeElement (ontime and offtime)
      xmitCodeElement(ontime, offtime, (freq!=0));
    }
    sei();

    //Flush remaining bits, so that next code starts
    //with a fresh set of 8 bits.
    bitsleft_r=0;

    // delay 205 milliseconds before transmitting next POWER code
    delay_ten_us(20500);

    // visible indication that a code has been output.
    quickflashLED();

    // if user is pushing Trigger button, stop transmission
    if (digitalRead(TRIGGER) == 0) {
      startOver = TRUE;
      break;
    }
  }

  if (startOver) goto Start_transmission;
  while (Loop == 1);

  // flash the visible LED on PB0  8 times to indicate that we're done
  delay_ten_us(65500); // wait maxtime
  delay_ten_us(65500); // wait maxtime
  quickflashLEDx(8);

}

void loop() {
  sleepNow();
  // if the user pushes the Trigger button and lets go, then start transmission of all POWER codes
  if (digitalRead(TRIGGER) == 0) {
    delay_ten_us(3000);  // delay 30ms
    if (digitalRead(TRIGGER) == 1) {
      sendAllCodes();
    }
  }
}


/****************************** LED AND DELAY FUNCTIONS ********/


// This function delays the specified number of 10 microseconds
// it is 'hardcoded' and is calibrated by adjusting DELAY_CNT
// in main.h Unless you are changing the crystal from 8mhz, dont
// mess with this.
void delay_ten_us(uint16_t us) {
  uint8_t timer;
  while (us != 0) {
    // for 8MHz we want to delay 80 cycles per 10 microseconds
    // this code is tweaked to give about that amount.
    for (timer=0; timer <= DELAY_CNT; timer++) {
      NOP;
      NOP;
    }
    NOP;
    us--;
  }
}


// This function quickly pulses the visible LED (connected to PB0, pin 5)
// This will indicate to the user that a code is being transmitted
void quickflashLED( void ) {
  digitalWrite(LED, HIGH);
  delay_ten_us(3000);   // 30 millisec delay
  digitalWrite(LED, LOW);
}

// This function just flashes the visible LED a couple times, used to
// tell the user what region is selected
void quickflashLEDx( uint8_t x ) {
  quickflashLED();
  while(--x) {
    delay_ten_us(15000);     // 150 millisec delay between flahes
    quickflashLED();
  }
}




/****************************** SLEEP and WAKE FUNCTIONS ********/
// from kaqkjz:
// http://www.ka1kjz.com/561/adding-sleep-to-tv-b-gone-code/

void sleepNow()
{
  set_sleep_mode(TRIGGER);                    // sleep mode is set here

  sleep_enable();                             // enables the sleep bit in the mcucr register

  attachInterrupt(0, wakeUpNow, LOW);         // use interrupt 0 (pin 2) and run function
  // wakeUpNow when pin 2 gets LOW

  sleep_mode();                               // here the device is actually put to sleep!!
  // THE PROGRAM CONTINUES FROM HERE ON WAKE

  sleep_disable();                            // first thing after waking, disable sleep

  detachInterrupt(0);                         // disables int 0 as the wakeupnow code will
                                              // not be executed during normal runtime
}

void wakeUpNow()
{
  // any needed wakeup code can be placed here
}
