/*******************************************************************
  Bionic Eye sketch for Adafruit Trinket.  

  by Bill Earl
  for Adafruit Industries
 
  Required library is the Adafruit_SoftServo library
  available at https://github.com/adafruit/Adafruit_SoftServo
  The standard Arduino IDE servo library will not work with 8 bit
  AVR microcontrollers like Trinket and Gemma due to differences
  in available timer hardware and programming. We simply refresh
  by piggy-backing on the timer0 millis() counter
 
  Trinket:        Bat+    Gnd       Pin #0  Pin #1
  Connection:     Servo+  Servo-    Tilt    Rotate
                  (Red)   (Brown)   Servo   Servo
                                    (Orange)(Orange)
 
 *******************************************************************/
 
#include <Adafruit_SoftServo.h>  // SoftwareServo (works on non PWM pins)
 
#define TILTSERVOPIN 0    // Servo control line (orange) on Trinket Pin #0
#define ROTATESERVOPIN 1  // Servo control line (orange) on Trinket Pin #1
 
Adafruit_SoftServo TiltServo, RotateServo;  //create TWO servo objects
   
void setup() 
{
  // Set up the interrupt that will refresh the servo for us automagically
  OCR0A = 0xAF;            // any number is OK
  TIMSK |= _BV(OCIE0A);    // Turn on the compare interrupt (below!)
  
  TiltServo.attach(TILTSERVOPIN);   // Attach the servo to pin 0 on Trinket
  RotateServo.attach(ROTATESERVOPIN);   // Attach the servo to pin 1 on Trinket
  delay(15);                    // Wait 15ms for the servo to reach the position
}
 
void loop()  
{
  delay(100);  
  TiltServo.detach();   // release the servo
  RotateServo.detach();   // release the servo
 
  if(random(100) > 80)  // on average, move once every 500ms
  {
    TiltServo.attach(TILTSERVOPIN);   // Attach the servo to pin 0 on Trinket
    TiltServo.write(random(120, 180));    // Tell servo to go to position
  }
  if(random(100) > 90)  // on average, move once every 500ms
  {
    RotateServo.attach(ROTATESERVOPIN);   // Attach the servo to pin 1 on Trinket
    RotateServo.write(random(0, 180));    // Tell servo to go to position
  }
}
 
// We'll take advantage of the built in millis() timer that goes off
// to keep track of time, and refresh the servo every 20 milliseconds
// The SIGNAL(TIMER0_COMPA_vect) function is the interrupt that will be
// Called by the microcontroller every 2 milliseconds
volatile uint8_t counter = 0;
SIGNAL(TIMER0_COMPA_vect) 
{
  // this gets called every 2 milliseconds
  counter += 2;
  // every 20 milliseconds, refresh the servos!
  if (counter >= 20) 
  {
    counter = 0;
    TiltServo.refresh();
    RotateServo.refresh();
  }
}