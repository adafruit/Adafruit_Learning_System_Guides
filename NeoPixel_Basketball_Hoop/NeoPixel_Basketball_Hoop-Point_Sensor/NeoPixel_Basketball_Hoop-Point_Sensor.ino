#include <Adafruit_NeoPixel.h>

#define     PIN                     1
#define     IR_LED                  0           // Digital pin that is hooked up to the IR LED.
#define     IR_SENSOR               2     
#define     BASKET_CHECK_SECONDS   0.1          //How often it checks to see if there is a ball.
Adafruit_NeoPixel strip = Adafruit_NeoPixel(60, PIN, NEO_GRB + NEO_KHZ800);
///////////////////////////////////////////////////////
// Setup function
//
// Called once at start up.
///////////////////////////////////////////////////////
void setup(void){
   
  // Set up the input and output pins.
  pinMode(IR_LED, OUTPUT);
  pinMode(IR_SENSOR, INPUT);
  strip.begin();
  strip.show(); // Initialize all pixels to 'off'
}

///////////////////////////////////////////////////////
// Loop Function
//
// Called continuously after setup function.
///////////////////////////////////////////////////////
void loop(void) {
  if (isBallInHoop()) {  
    timedRainbowCycle(2000, 10);
  }
  
  // Delay for 100 milliseconds so the ball in hoop check happens 10 times a second.
  delay(100);
}



///////////////////////////////////////////////////////
// isBallInHoop function
//
// Returns true if a ball is blocking the sensor.
///////////////////////////////////////////////////////
boolean isBallInHoop() {
  // Pulse the IR LED at 38khz for 1 millisecond
  pulseIR(1000);

  // Check if the IR sensor picked up the pulse (i.e. output wire went to ground).
  if (digitalRead(IR_SENSOR) == LOW) {
    return false; // Sensor can see LED, return false.
  }

  return true; // Sensor can't see LED, return true.
}

///////////////////////////////////////////////////////
// pulseIR function
//
// Pulses the IR LED at 38khz for the specified number
// of microseconds.
///////////////////////////////////////////////////////
void pulseIR(long microsecs) {
  // 38khz IR pulse function from Adafruit tutorial: http://learn.adafruit.com/ir-sensor/overview
  
  // we'll count down from the number of microseconds we are told to wait
 
  cli();  // this turns off any background interrupts
 
  while (microsecs > 0) {
    // 38 kHz is about 13 microseconds high and 13 microseconds low
   digitalWrite(IR_LED, HIGH);  // this takes about 3 microseconds to happen
   delayMicroseconds(10);         // hang out for 10 microseconds, you can also change this to 9 if its not working
   digitalWrite(IR_LED, LOW);   // this also takes about 3 microseconds
   delayMicroseconds(10);         // hang out for 10 microseconds, you can also change this to 9 if its not working
 
   // so 26 microseconds altogether
   microsecs -= 26;
  }
 
 
 
  sei();  // this turns them back on
  

  
  }

void timedRainbowCycle(uint32_t milliseconds, uint8_t wait) {
  // Get the starting time in milliseconds.
  uint32_t start = millis();
  // Use a counter to increment the current color position.
  uint32_t j = 0;
  // Loop until it's time to stop (desired number of milliseconds have elapsed).
  while (millis() - start < milliseconds) {
    // Change all the light colors.
    for (int i = 0; i < strip.numPixels(); ++i) {
      strip.setPixelColor(i, Wheel(((i * 256 / strip.numPixels()) + j) & 255));
    }
    strip.show();
    // Wait the deisred number of milliseconds.
    delay(wait);
    // Increment counter so next iteration changes.
    j += 1;
  }
  // Turn all the pixels off after the animation is done.
  for (int i = 0; i < strip.numPixels(); ++i) {
    strip.setPixelColor(i, 0);
  }
  strip.show();
}
uint32_t Wheel(byte WheelPos) {
  if(WheelPos < 85) {
   return strip.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
  } else if(WheelPos < 170) {
   WheelPos -= 85;
   return strip.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  } else {
   WheelPos -= 170;
   return strip.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
}
