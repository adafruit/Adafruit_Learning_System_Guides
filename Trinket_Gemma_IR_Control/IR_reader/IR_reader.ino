// SPDX-FileCopyrightText: 2018 Mikey Sklar for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/* Trinket/Gemma compatible Raw IR decoder sketch
This sketch/program uses an Adafruit Trinket or Gemma
ATTiny85 based mini microcontroller and a PNA4602 to
decode IR received. This can be used to make a IR receiver
(by looking for a particular code) or transmitter 
(by pulsing an IR LED at ~38KHz for the durations pulse_index

Based on Adafruit tutorial http://learn.adafruit.com/ir-sensor/using-an-ir-sensor

and ATTiny program by TinyPCRemote Nathan Chantrell http://nathan.chantrell.net
under Creative Commons Attribution-ShareAlike 3.0 Unported (CC BY-SA 3.0) license

SendSoftwareSerial Lirary modification by Nick Gammon from NewSoftwareSerial code
GNU Lesser General Public License as published by the Free Software Foundation version 2.1 
at http://gammon.com.au/Arduino/SendOnlySoftwareSerial.zip
*/
#include <SoftwareSerial.h>       // use if you do not wish to use the lightweight library 
 
SoftwareSerial Serial(0,1);      // Receive, Transmit (Receive not used)
 
// We need to use the 'raw' pin reading methods because timing is very important here 
// and the digitalRead() procedure is slower!
#define IRpin_PIN PINB // ATTiny85 had Port B pins
#define IRpin 2
 
#define MAXPULSE    12000  // the maximum pulse we'll listen for - 5 milliseconds 
#define NUMPULSES   34    // max IR pulse pairs to sample
#define RESOLUTION  2     // time between IR measurements
#define STORED_BUTTON_CODES 4 // remote control codes stored
 
// we will store up to 100 pulse pairs (this is -a lot-)
uint16_t pulses[NUMPULSES]; // high and low pulses
uint16_t pulse_index = 0;  // index for pulses we're storing
uint32_t irCode = 0;

void setup(void) {
  Serial.begin(9600);
  Serial.println();
  Serial.println("Ready to decode IR!");
  pinMode(IRpin, INPUT);   // Listen to IR receiver on Trinket/Gemma pin D2
}
 
void loop(void) {
  // Wait for an IR Code
  uint16_t numpulse=listenForIR(); 
  
  // Process the pulses to get a single number representing code
  for (int i = 0; i < NUMPULSES; i++) {   
      Serial.print(pulses[i]);
      Serial.print(", ");         
  }
    Serial.println("\n");
}

uint16_t listenForIR() {  // IR receive code
  pulse_index = 0;
  while (1) {
   unsigned int highpulse, lowpulse;  // temporary storage timing
   highpulse = lowpulse = 0; // start out with no pulse length 
  
   while (IRpin_PIN & _BV(IRpin)) { // got a high pulse
      highpulse++; 
      delayMicroseconds(RESOLUTION);
      if (((highpulse >= MAXPULSE) && (pulse_index != 0))|| pulse_index == NUMPULSES) {
        return pulse_index; 
      }
   } 
   pulses[pulse_index] = highpulse; 

   while (! (IRpin_PIN & _BV(IRpin))) { // got a low pulse
      lowpulse++; 
      delayMicroseconds(RESOLUTION);
      if (((lowpulse >= MAXPULSE) && (pulse_index != 0))|| pulse_index == NUMPULSES) {
        return pulse_index; 
      }
   }
   pulses[pulse_index] = lowpulse; 
   pulse_index++;
   
  }
  
}

