/*
* Adafruit Prop-Maker Featherwing
* Switch Example
* 
* Print to the Serial Montior when a switch is pressed.
*/

#if defined(__SAMD21G18A__) || defined(__AVR_ATmega32U4__)
  #define SWITCH_PIN   9
#elif defined(__AVR_ATmega328P__)
  #define SWITCH_PIN   9
#elif defined(NRF52)
  #define SWITCH_PIN   31
#elif defined(ESP8266)
  #define SWITCH_PIN   0
#elif defined(TEENSYDUINO)
  #define SWITCH_PIN   4
#elif defined(ESP32)
  #define SWITCH_PIN   15
#endif

void setup() {
  Serial.begin(115200);
  Serial.println("\nProp-Maker Wing: Switch Example");
  // set up the switch
  pinMode(SWITCH_PIN, INPUT_PULLUP);
}

void loop()
{
  if (!digitalRead(SWITCH_PIN)) {
    Serial.println("Switch pressed!");
  }
}
