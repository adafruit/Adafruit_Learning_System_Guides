#include <Servo.h> 
Servo servo;  

void setup() 
{ 
  servo.attach(9);  // attaches the servo on pin 9 to the servo object 
  servo.write(90);  // change this value to achieve minimum rotation!
} 
 
void loop() 
{ 
}
