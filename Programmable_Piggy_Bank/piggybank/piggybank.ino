/*********************
* connect the COIN wire to digital 2
* set the side switches to "FAST" "NC"
**********************/

// include the library code:
#include <Wire.h>
#include <Adafruit_MCP23017.h>
#include <Adafruit_RGBLCDShield.h>

// The shield uses the I2C SCL and SDA pins. On classic Arduinos
// this is Analog 4 and 5 so you can't use those for analogRead() anymore
// However, you can connect other I2C sensors to the I2C bus and share
// the I2C bus.
Adafruit_RGBLCDShield lcd = Adafruit_RGBLCDShield();

// These #defines make it easy to set the backlight color
#define RED 0x1
#define YELLOW 0x3
#define GREEN 0x2
#define TEAL 0x6
#define BLUE 0x4
#define VIOLET 0x5
#define WHITE 0x7

// attach coin wire to digital 2
#define COIN 2
int coins;
int brightness = 0;    // how bright the LED is
int fadeAmount = 5;    // how many points to fade the LED by
int fadebrightness = 0;    // how bright the LED is when it's flashing

void setup() {
    // declare pin 11 to be an output for LED:
  pinMode(11, OUTPUT);
  // Debugging output
  Serial.begin(9600);
  // set up the LCD's number of rows and columns:
  lcd.begin(16, 2);

  pinMode(COIN, INPUT);
  digitalWrite(COIN, HIGH); // pull up
  coins = 0;
}

void loop() {
  lcd.setCursor(0,0);
  lcd.print(" PLEASE INSERT ");
  lcd.setCursor(0,1);
  lcd.print("  ONE QUARTER  ");
    // set the brightness of pin 11:
  analogWrite(11, brightness);

  // while the coin pin is low (no coin detected), do nothing
  while (! digitalRead(COIN)) {
    delay(1);
  }

  // while the pin is high, we'll track the length with a counter
  uint8_t counter = 0;
  while (digitalRead(COIN)) {
    delay(1);
    counter++;
  }
  Serial.print(counter);
  Serial.println(" ms long pulse");
  
  if ((counter > 60) || (counter < 20))
      return;
      
  coins++;
  lcd.clear();
  lcd.setCursor(0,0);
  lcd.print("   OINK OINK! ");
  lcd.setCursor(0,1);
  lcd.print("YOU HAVE $");
  lcd.print(coins*.25);
  lcd.print("  ");
    // loop through to flash the LED
  fadebrightness = brightness;
  for (int i = brightness; i < 510; i+=5) {
    // turn the pin on:
    analogWrite(11, fadebrightness);
    fadebrightness = fadebrightness + fadeAmount;  
    delay(20);                  
    // reverse the direction of the fading at the ends of the fade: 
    if (fadebrightness == 0 || fadebrightness == 255) {
      fadeAmount = -fadeAmount;
    }
  }
  brightness = brightness + 5;
}
