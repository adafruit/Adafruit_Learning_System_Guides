#if 0 // Change to 1 to enable this code (must enable ONE user*.cpp only!)

#include <Arduino.h>
#include <Servo.h>

Servo myservo;

void user_setup(void) {
  myservo.attach(3);
}

void user_loop(void) {
  int pos = map(millis() % 2000, 0, 2000, 0, 180);
  myservo.write(pos);
}

#endif // 0
