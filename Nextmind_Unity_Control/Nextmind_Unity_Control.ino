#include <Servo.h>

Servo servo;
int numberRecvd;
String dataString = "";

void setup(){
  
  Serial.begin(9600);
  
  pinMode(5, OUTPUT);
  servo.attach(5);
  servo.write(0);
}

void loop(){
  
  if (Serial.available() > 0){
    
    dataString = "";
    while (Serial.available() > 0)
    {
      dataString += char(Serial.read());
      delay(2);
    }

    numberRecvd = dataString.toInt();

    switch (numberRecvd) {
      case 1:
        servo.write(125);
        break;
      case 2:
        servo.write(90);
        break;
      case 3:
        servo.write(55);
        break;
      default:
        servo.write(0);
        break;
    }

    Serial.flush();
    Serial.print("received: ");
    Serial.println(numberRecvd);
  }
  
  delay(20);
}
