// SPDX-FileCopyrightText: 2018 Mikey Sklar for Adafruit Industries
//
// SPDX-License-Identifier: GPL-3.0-or-later

/* 
Name: Blinking Eyes  - based on code by Brad Blumenthal, MAKE Magazine  
License: GPLv3
Modified for 8 MHz ATTiny85 and low light photocell
October 2013 for Adafruit Learning System
*/

#define SENSITIVITY 550        // photocell sensitivity (changeable)
#define CELL_PIN    1          // CdS Photocell voltage divider on
                               //   Trinket GPIO #2 (A1), Gemma D1/A1
uint8_t eyes_open;
volatile uint8_t  blink_count; 
volatile uint8_t  blink_flag;
volatile uint8_t  tick_flag;
volatile uint8_t  getting_brighter = 0;
const uint8_t    min_bright=16;
const uint8_t    max_bright=128;
volatile uint8_t brightness;
uint8_t          lfsr;            // Linear Feedback Shift Register 
const uint8_t    min_blink = 64u; // don't blink more than once every 3 secs or so

void setup() {
  pinMode(0, OUTPUT);                                       // Eyes set as output
  pinMode(2, INPUT);                                        // Photocell as input
  analogWrite(0, max_bright);  analogWrite(1, max_bright);  // Light eyes
  eyes_open = 1;
  blink_flag = 0;
  lfsr = random(100);                                       // initialize "blinking"
  blink_count = max(blink_count, min_blink);
  lfsr = (lfsr >> 1) ^ (-(lfsr & 1u) & 0xF0u);              // pseudorandom blinking
  
  // Timer1 set to CK/1024  ~10 (8) hZ at 8 MHz clock rate for blinking action
  TCCR1 |= _BV(CS13) | _BV(CS11) | _BV(CS10);  
  TIMSK |= _BV(TOIE1);  // Enable Timer/Counter1 Overflow Interrupt
}

void loop() {
    uint16_t photocell;
    photocell = analogRead(CELL_PIN);
    if(photocell > SENSITIVITY) {  // if too light, shut down eyes until it gets darker on photocell
       tick_flag=0;
       analogWrite(0,0);  // Turn off eyes if too light out
      }
    if (tick_flag) {  // if too bright or we've counted enough ticks (clocks for blink)
      tick_flag = 0;
      if (blink_flag) {
        blink_flag = 0;
        if (eyes_open) {
          eyes_open = 0;
          analogWrite(0,0);  // Turn off eyes by stopping PWM
          blink_count = (lfsr & 0x01) + 1; // off for 1-2 ticks
          }
        else {
          eyes_open = 1;
          analogWrite(0,brightness);  // Turn eyes on 
          blink_count = max(blink_count, min_blink);
          lfsr = (lfsr >> 1) ^ (-(lfsr & 1u) & 0xF0u);  // regenerate pseudorandom blink
          }
      }
      else { // One "tick,"  but we didn't blink...  work on brightness control
        if (getting_brighter) {
          brightness += 2;  // increase brightness
          analogWrite(0, brightness);  
          if (brightness >= max_bright) getting_brighter = 0;
        } else {
          brightness -= 2;  // decrease brightness
          analogWrite(0, brightness); 
          if (brightness <= min_bright) getting_brighter = 1;
        }
      }
    }
}

ISR (TIMER1_OVF_vect) {           // Every 64 times a second, check blink
  noInterrupts();
  tick_flag = 1;
  blink_count--;
  if (!blink_count) {
    blink_flag = 1;
  }
  interrupts();
}
