// Adafruit Trinket React Counter Sketch - 7-segment display
//
// Use a 7-segment LED backpack to display the number of times a 
// button has been pressed.  Great for building a physical 'like'
// or react button.  The value will be stored  in EEPROM so it 
// will persist between power down/up.
//
// NOTE: As-is this sketch needs to run on a Trinket because it
// assumes the switch on pin #1 has a pull-down resistor to ground.
// If using another board without this pull-down you can explicitly
// add a ~10kohm resistor from digital #1 to ground.
//
// Author: Tony DiCola
// License: MIT (https://opensource.org/licenses/MIT)
#include <EEPROM.h>
#include <Wire.h>
#include "Adafruit_LEDBackpack.h"
#include "Adafruit_GFX.h"


// Uncomment the line below to reset the counter value in EEPROM to zero.
// After uncommenting reload the sketch and during the setup the counter
// will be reset.  Then comment the line again and reload to start again
// (if you don't comment it out then every time the board powers on it
// will reset back to zero!).
//#define RESET_COUNT

// OR just hold the button for longer than the RESET_HOLD_SECOND below
// to reset the count!

// Configuration:
#define LED_BACKPACK_ADDRESS   0x70   // I2C address of the backpack display.
                                      // Keep the default 0x70 unless you
                                      // change the backpack's address bridges.

#define COUNT_BUTTON_PIN       1      // Digital input connected to the button that
                                      // will increase the count. This line should
                                      // have a pull-down resistor to ground.  The
                                      // opposite side of the button should be
                                      // connected to a high level like 5V or 3.3V.

#define COUNT_ADDRESS          0      // Address in EEPROM to store the counter.
                                      // This will take 2 bytes (16-bit value).
                                      // You don't need to change this unless you
                                      // want to play with different EEPROM locations.

#define RESET_HOLD_SECONDS     5      // Number of seconds to hold the button down to
                                      // force a reset of the count to zero.  Set to 0
                                      // to disable this functionality.

// 7-segment display
Adafruit_7segment backpack = Adafruit_7segment();
uint32_t holdStart = 0;

void update_display() {
  // Get the count value from EEPROM and print it to the display.
  uint16_t count;
  EEPROM.get(COUNT_ADDRESS, count);
  backpack.print(count, DEC);
  backpack.writeDisplay();
}

void setup() {
  // Setup button inputs.
  pinMode(COUNT_BUTTON_PIN, INPUT);
  
  // Initialize the LED backpack display.
  backpack.begin(LED_BACKPACK_ADDRESS);

  // Clear the count in EEPROM if desired.
  #ifdef RESET_COUNT
    uint16_t count = 0;
    EEPROM.put(COUNT_ADDRESS, count);
  #endif

  // Update the display with the current count value.
  update_display();

  // Reset the last known time the button wasn't being held.
  holdStart = millis();
}

void loop() {
  // Take a couple button readings with a small delay in between to detect when
  // the signal changes from high to low, i.e. the button was released.
  int firstCount = digitalRead(COUNT_BUTTON_PIN);
  delay(20);
  int secondCount = digitalRead(COUNT_BUTTON_PIN);

  // Check for count button release.
  if (firstCount == HIGH && secondCount == LOW) {
    // Button was released!
    // Increment the count value stored in EEPROM.
    uint16_t count;
    EEPROM.get(COUNT_ADDRESS, count);
    count += 1;
    EEPROM.put(COUNT_ADDRESS, count);
    // Update the display with the latest count value.
    update_display();
  }

  // Reset the hold start if the button wasn't pressed (i.e. first and last were not both high levels).
  if ((firstCount != HIGH) || (secondCount != HIGH)) {
    holdStart = millis();
  }

  // Check if the button has been held for the amount of reset time.
  if ((RESET_HOLD_SECONDS > 0) && ((millis() - holdStart) >= (RESET_HOLD_SECONDS*1000))) {
    // Reset to zero and update the display!
    uint16_t count = 0;
    EEPROM.put(COUNT_ADDRESS, count);
    update_display();
    // Reset the hold time to start over again.
    holdStart = millis();
    // Flash the display a few times to give time to remove finger.
    for (int i=0; i<5; ++i) {
      delay(200);
      backpack.clear();
      backpack.writeDisplay();
      delay(200);
      update_display();
    }
  }
}
