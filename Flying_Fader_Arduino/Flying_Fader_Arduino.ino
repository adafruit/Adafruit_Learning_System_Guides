// SPDX-FileCopyrightText: 2022 John Park for Adafruit Industries
// SPDX-License-Identifier: MIT
// Motorized fader demo
// capsense implementation by @todbot / Tod Kurt

#include <Bounce2.h>

const int pwmA = 12;  // motor pins
const int pwmB = 11;

const int fader = A0;  // fader pin
int fader_pos = 0;
float filter_amt = 0.75;
float speed = 1.0;

int saved_positions[] = { 230, 180, 120, 60 } ;
int current_saved_position = 1 ;

const int num_buttons = 4;
const int button_pins[num_buttons] = {10, 9, 8, 7};  // feather silk != arduino pin number. 10, 9, 6, 5 on board
Bounce buttons[num_buttons];
bool motor_release_state = false;  // to handle motor release

class FakeyTouch 
{
  public:
  FakeyTouch( int apin, int athreshold = 300 ) {  // tune the threshold value to your hardware
    pin = apin;
    thold = athreshold;
  }  
  void begin() {
    baseline = readTouch();
  }
  int readTouch() {
    pinMode(pin, OUTPUT);
    digitalWrite(pin,HIGH);
    pinMode(pin,INPUT);
    int i = 0;
    while( digitalRead(pin) ) { i++; }
    return i;
  }
  bool isTouched() {
    return (readTouch() > baseline + thold);
  }
  int baseline;
  int thold;
  int pin; 
};

const int touchpin_F = A3;
FakeyTouch touchF = FakeyTouch( touchpin_F );


void setup() {
  Serial.begin(9600);
  delay(1000);
  pinMode (pwmA, OUTPUT);
  pinMode (pwmB, OUTPUT);
  analogWriteFreq(100);
  analogWrite(pwmA, 0); 
  analogWrite(pwmB, 0);
  for (uint8_t i=0; i< num_buttons; i++){
    buttons[i].attach( button_pins[i], INPUT_PULLUP);
  }
}

int last_fader_pos = fader_pos;


void loop() {
  for (uint8_t i=0; i< num_buttons; i++){
    buttons[i].update();
    if( buttons[i].fell()) {
      current_saved_position = i;
      go_to_position(saved_positions[current_saved_position]);
    }
  }

  if( touchF.isTouched()){
    motor_release_state = true;
    analogWrite(pwmA, 0);
    analogWrite(pwmB, 0);
    delay(60);
  }
  else{
    motor_release_state = false;
    go_to_position(saved_positions[current_saved_position]);
  }
  
  fader_pos = int( (filter_amt * last_fader_pos) + ( (1.0-filter_amt) * int(analogRead(fader) / 4 )) );
  if (abs(fader_pos - last_fader_pos) > 1) {
    Serial.println(fader_pos);
    if (motor_release_state==false){
      go_to_position(saved_positions[current_saved_position]);
    }
    last_fader_pos = fader_pos;
  }
}

void go_to_position(int new_position) {
  fader_pos = int(analogRead(fader) / 4);
  while (abs(fader_pos - new_position) > 4) {
   if (fader_pos > new_position) {
    speed = 2.25 * abs(fader_pos - new_position) / 256 + 0.2;
    speed = constrain(speed, -1.0, 1.0);
      if (speed > 0.0) {
        analogWrite(pwmA, 255);
        analogWrite(pwmB, 0);
      }
   }
   if (fader_pos < new_position) {
      speed = 2.25 * abs(fader_pos - new_position) / 256 - 0.2;
      speed = constrain(speed, -1.0, 1.0);
        if (speed > 0.0) {
          analogWrite(pwmA, 0);
          analogWrite(pwmB, 255);
        }
      }
      
    fader_pos = int(analogRead(fader) / 4);
    
  }
  analogWrite(pwmA, 0);
  analogWrite(pwmB, 0);
}
