/* 
Portable solar panel efficiency tracker. For testing out solar panels!
See https://learn.adafruit.com/portable-solar-charging-tracker for more information
Code is public domain, MIT License by Limor "Ladyada" Fried 
*/

// include the library code:
#include <LiquidCrystal.h>
#include <Wire.h>

// initialize the library with the numbers of the interface pins
LiquidCrystal lcd(2, 3, 4, 5, 6, 7 );

#define aref_voltage 3.3         // we tie 3.3V to ARef and measure it with a multimeter!

int lipoPin = 3;      // the battery 
float lipoMult = 1.666;  // how much to multiply to get the original voltage

int PVPin = 2;      // the cell
float PVMult = 2;  // how much to multiply to get the original voltage

int currentPin = 1;
float currentMult = 208; // how much to multiply to get the original current draw
    
void setup(void) {
  // We'll send debugging information via the Serial monitor
  Serial.begin(9600);   
  
  // set up the LCD's number of rows and columns: 
  lcd.begin(16, 2);
  lcd.clear();
  // Print a message to the LCD.
  lcd.print("Solar logger");
  delay(2000);
  lcd.clear();
  // If you want to set the aref to something other than 5v
  analogReference(EXTERNAL);
  
  byte delta[8] = {
	B00000,
	B00100,
	B00100,
	B01010,
	B01010,
	B10001,
	B11111,
	B00000
};

  lcd.createChar(0, delta);
}



void loop(void) {
  int adcreading;
 
  adcreading = analogRead(lipoPin);  
  Serial.println(adcreading);
  
  float lipoV = adcreading;
  lipoV *= aref_voltage;
  lipoV /= 1024;
  lipoV *= lipoMult;

  lcd.clear();
  Serial.print("LiPo voltage = ");
  Serial.println(lipoV);     // the raw analog reading
  
  lcd.setCursor(0, 0);
  lcd.print("LiPo=");
  lcd.print(lipoV);
  lcd.print(' ');
  lcd.write((uint8_t)0);
  
  adcreading = analogRead(PVPin);  
  float PVV = adcreading;
  PVV *= aref_voltage;
  PVV /= 1024;
  PVV *= PVMult;
  
  lcd.print((int)((PVV-lipoV) * 1000), DEC);  // in mV
  lcd.print("mV");
  
  Serial.print("PV voltage = ");
  Serial.println(PVV);     // the raw analog reading

  lcd.setCursor(0, 1);
  lcd.print("PV=");
  lcd.print(PVV);
  
  adcreading = analogRead(currentPin);  
  float currentI = adcreading;
  currentI *= aref_voltage;
  currentI /= 1024;
  currentI *= currentMult;
  Serial.print("Current (mA) = ");
  Serial.println(currentI);     // the raw analog reading
  
  lcd.print(" I=");
  lcd.print((int)currentI);
  lcd.print("mA");
  delay(1000);
}
