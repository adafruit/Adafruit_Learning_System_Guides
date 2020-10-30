#include <Adafruit_CircuitPlayground.h>

////////////////////////////////////////////////////////////////////////////
void setup() {
  // Initialize serial.
  Serial.begin(9600); 
  
  // Initialize Circuit Playground library.
  CircuitPlayground.begin();
}

////////////////////////////////////////////////////////////////////////////
void loop() {
  // Print cap touch reading on serial port.
  Serial.println(CircuitPlayground.readCap(1));

  // Update rate.
  delay(100);
}
