// SPDX-FileCopyrightText: 2018 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Example code for recording and playing back servo motion with a 
// analog feedback servo
// http://www.adafruit.com/products/1404


#include <Servo.h>
#include <EEPROM.h>

#define CALIB_MAX 512
#define CALIB_MIN 100
#define SAMPLE_DELAY 25 // in ms, 50ms seems good

uint8_t recordButtonPin = 12;
uint8_t playButtonPin = 7;
uint8_t servoPin = 9;
uint8_t feedbackPin = A0;
uint8_t ledPin = 13;

Servo myServo;  
  
void setup() {
  Serial.begin(9600);
  pinMode(recordButtonPin, INPUT);
  digitalWrite(recordButtonPin, HIGH);
  pinMode(playButtonPin, INPUT);
  digitalWrite(playButtonPin, HIGH);
  pinMode(ledPin, OUTPUT);
  
  Serial.println("Servo RecordPlay");
}

void loop() {
 if (! digitalRead(recordButtonPin)) {
   delay(10);
   // wait for released
   while (! digitalRead(recordButtonPin));
   delay(20);
   // OK released!
   recordServo(servoPin, feedbackPin, recordButtonPin);
 }
 
  if (! digitalRead(playButtonPin)) {
   delay(10);
   // wait for released
   while (! digitalRead(playButtonPin));
   delay(20);
   // OK released!
   playServo(servoPin, playButtonPin);
 }
}

void playServo(uint8_t servoPin, uint8_t buttonPin) {
  uint16_t addr = 0;
  Serial.println("Playing");


  myServo.attach(servoPin);
  while (digitalRead(buttonPin)) {    
    uint8_t x = EEPROM.read(addr);
    Serial.print("Read EE: "); Serial.print(x);
    if (x == 255) break;
    // map to 0-180 degrees
    x = map(x, 0, 254, 0, 180);
    Serial.print(" -> "); Serial.println(x);
    myServo.write(x);
    delay(SAMPLE_DELAY);
    addr++;
    if (addr == 512) break;
  }
  Serial.println("Done");
  myServo.detach();
  delay(250);  
}

void recordServo(uint8_t servoPin, uint8_t analogPin, uint8_t buttonPin) {
  uint16_t addr = 0;
  
  Serial.println("Recording");
  digitalWrite(ledPin, HIGH);
  


  
  pinMode(analogPin, INPUT); 
  while (digitalRead(buttonPin)) {
     uint16_t a = analogRead(analogPin);
     
     Serial.print("Read analog: "); Serial.print(a);
     if (a < CALIB_MIN) a = CALIB_MIN;
     if (a > CALIB_MAX) a = CALIB_MAX;
     a = map(a, CALIB_MIN, CALIB_MAX, 0, 254);
     Serial.print(" -> "); Serial.println(a);
     EEPROM.write(addr, a);
     addr++;
     if (addr == 512) break;
     delay(SAMPLE_DELAY);
  }
  if (addr != 512) EEPROM.write(addr, 255);

  digitalWrite(ledPin, LOW);

  Serial.println("Done");
  delay(250);
}
