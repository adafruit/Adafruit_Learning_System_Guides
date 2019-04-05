/*******************************************************************
  Adafruit Animal - control code for toy animal animation
 
  Required library is the Adafruit_SoftServo library
  available at https://github.com/adafruit/Adafruit_SoftServo
  The standard Arduino IDE servo library will not work with 8 bit
  AVR microcontrollers like Trinket and Gemma due to differences
  in available timer hardware and programming. We simply refresh
  by piggy-backing on the timer0 millis() counter
 
  Required hardware includes an Adafruit Trinket microcontroller
  a servo motor, a piezo speaker, a photocell, and a resistor
 
  As written, this is specifically for the Trinket although it should
  be Gemma compatible.  
 
 *******************************************************************/
 
#include <Adafruit_SoftServo.h>  // SoftwareServo (works on non PWM pins)
 
#define SERVO1PIN 0    // Servo control line (orange) on Trinket Pin #0
#define SPEAKER   1    // Piezo Speaker on GPIO #1
#define PHOTOCELL 1    // CdS photocell on GPIO #2 (A1)
 
Adafruit_SoftServo myServo1;  // create servo object
int16_t  servoPosition;       // servo position  

void setup() {
  // Set up the interrupt that will refresh the servo for us automagically
  OCR0A = 0xAF;            // any number is OK
  TIMSK |= _BV(OCIE0A);    // Turn on the compare interrupt (below!)
  
  servoPosition = 90;            // Tell servo to go to midway
  myServo1.attach(SERVO1PIN);    // Attach the servo to pin 0 on Trinket
  myServo1.write(servoPosition); //  and move servo
  delay(15);                     // Wait 15ms for the servo to reach the position
  pinMode(SPEAKER,OUTPUT);       // Set Trinket/Gemma Digital 0 to output
                                 //  to drive the piezo buzzer (important)
}
 
void loop()  {
  uint16_t light_reading;  // value read from photocell voltage divider
  
  if(servoPosition != 0)
     servoPosition = 0;          // if it's up, go down & visa versa
  else
     servoPosition = 180;
  
  light_reading = analogRead(PHOTOCELL);  // Read Analog pin 1 for the changing
                                          // voltage from the CdS divider
  if(light_reading < 800) {               // if the photocell is dark enough, we're petting
    chirp();                              //    so make sound ...
    myServo1.write(servoPosition);        //    and tell servo to move
  }
  delay(1000);   // wait a second between checks/chirps/movements (changable)
}

// Generate the Bird Chirp sound
void chirp() {   
  for(uint8_t i=200; i>180; i--)
     playTone(i,9);
}

// Play a tone for a specific duration.  value is not frequency to save some
//   cpu cycles in avoiding a divide.  
void playTone(int16_t tonevalue, int duration) {
  for (long i = 0; i < duration * 1000L; i += tonevalue * 2) {
     digitalWrite(SPEAKER, HIGH);
     delayMicroseconds(tonevalue);
     digitalWrite(SPEAKER, LOW);
     delayMicroseconds(tonevalue);
  }     
}
 
// We'll take advantage of the built in millis() timer that goes off
// to keep track of time, and refresh the servo every 20 milliseconds
// The SIGNAL(TIMER0_COMPA_vect) function is the interrupt that will be
// called by the microcontroller every 2 milliseconds
volatile uint8_t counter = 0;
SIGNAL(TIMER0_COMPA_vect) {
  // this gets called every 2 milliseconds
  counter += 2;
  // every 20 milliseconds, refresh the servos!
  if (counter >= 20) {
    counter = 0;
    myServo1.refresh();
  }
}
