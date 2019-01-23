/*
* Adafruit Prop-Maker Featherwing
* LED Example
* 
* Rainbow swirl example for 3W LED.
*/

#if defined(__SAMD21G18A__) || defined(__AVR_ATmega32U4__)
  // No green PWM on 32u4
  #define POWER_PIN    10
  #define RED_LED      11
  #define GREEN_LED    12  // no PWM on atmega32u4
  #define BLUE_LED     13
#elif defined(__AVR_ATmega328P__)
  // No Red or Blue PWM
  #define POWER_PIN    10
  #define RED_LED      2
  #define GREEN_LED    3  // the only PWM pin!
  #define BLUE_LED     4
#elif defined(NRF52)
  #define POWER_PIN    11
  #define RED_LED      7
  #define GREEN_LED    15
  #define BLUE_LED     16
#elif defined(ESP8266)
  #define POWER_PIN    15
  #define RED_LED      13
  #define GREEN_LED    12
  #define BLUE_LED     14
#elif defined(TEENSYDUINO)
  #define POWER_PIN    10
  #define RED_LED      9
  #define GREEN_LED    6
  #define BLUE_LED     5
#elif defined(ESP32)
  #define POWER_PIN    33
  #define RED_LED 0
  #define GREEN_LED 1
  #define BLUE_LED 2
  #define RED_PIN  27
  #define GREEN_PIN    12
  #define BLUE_PIN     13
  #define analogWrite ledcWrite
#endif

uint8_t i=0;

void setup() {
  Serial.begin(115200);
  Serial.println("\nProp-Maker Wing: LED Example");
  
  // set up the power pin
  pinMode(POWER_PIN, OUTPUT);
  // disable the power pin, we're not writing to the LEDs
  digitalWrite(POWER_PIN, LOW);

  // Set up the LED Pins
  pinMode(RED_LED, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(BLUE_LED, OUTPUT);
  #if defined(ESP32)
    ledcSetup(RED_LED, 5000, 8);
    ledcAttachPin(RED_PIN, RED_LED);
    ledcSetup(GREEN_LED, 5000, 8);
    ledcAttachPin(GREEN_PIN, GREEN_LED);
    ledcSetup(BLUE_LED, 5000, 8);
    ledcAttachPin(BLUE_PIN, BLUE_LED);
  #endif
  
  analogWrite(RED_LED, 0);
  analogWrite(GREEN_LED, 0);
  analogWrite(BLUE_LED, 0);
}

uint32_t Wheel(byte WheelPos) {
  WheelPos = 255 - WheelPos;
  if(WheelPos < 85) {
    return (255 - WheelPos * 3, 0, WheelPos * 3);
  }
  if(WheelPos < 170) {
    WheelPos -= 85;
    return (0, WheelPos * 3, 255 - WheelPos * 3);
  }
  WheelPos -= 170;
  return (WheelPos * 3, 255 - WheelPos * 3, 0);
}

void loop()
{
  // set RGB Colors
  uint32_t color = Wheel(i++);
  uint8_t red = color >> 16;
  uint8_t green = color >> 8;
  uint8_t blue = color;

  // turn on the power pin
  digitalWrite(POWER_PIN, HIGH);

  // write colors to the 3W LED
  analogWrite(RED_LED, red);
  analogWrite(GREEN_LED, green);
  analogWrite(BLUE_LED, blue);
  delay(100);
}
