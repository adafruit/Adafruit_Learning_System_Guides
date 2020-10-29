// This sketch will send out a Nikon D50 trigger signal (probably works with most Nikons)
// See the full tutorial at https://learn.adafruit.com/ir-sensor/making-an-intervalometer
// MIT License, attribution appreciated    Limor Fried, Adafruit Industries
 
int IRledPin =  13;    // LED connected to digital pin 13
 
// The setup() method runs once, when the sketch starts
 
void setup()   {                
  // initialize the IR digital pin as an output:
  pinMode(IRledPin, OUTPUT);      
 
  Serial.begin(9600);
}
 
void loop()                     
{
  Serial.println("Sending IR signal");
 
  SendNikonCode();
 
  delay(60*1000);  // wait one minute (60 seconds * 1000 milliseconds)
}
 
// This procedure sends a 38KHz pulse to the IRledPin 
// for a certain # of microseconds. We'll use this whenever we need to send codes
void pulseIR(long microsecs) {
  // we'll count down from the number of microseconds we are told to wait
 
  cli();  // this turns off any background interrupts
 
  while (microsecs > 0) {
    // 38 kHz is about 13 microseconds high and 13 microseconds low
   digitalWrite(IRledPin, HIGH);  // this takes about 3 microseconds to happen
   delayMicroseconds(10);         // hang out for 10 microseconds, you can also change this to 9 if its not working
   digitalWrite(IRledPin, LOW);   // this also takes about 3 microseconds
   delayMicroseconds(10);         // hang out for 10 microseconds, you can also change this to 9 if its not working
 
   // so 26 microseconds altogether
   microsecs -= 26;
  }
 
  sei();  // this turns them back on
}
 
void SendNikonCode() {
  // This is the code for my particular Nikon, for others use the tutorial
  // to 'grab' the proper code from the remote
 
  pulseIR(2080);
  delay(27);
  pulseIR(440);
  delayMicroseconds(1500);
  pulseIR(460);
  delayMicroseconds(3440);
  pulseIR(480);
 
 
  delay(65); // wait 65 milliseconds before sending it again
 
  pulseIR(2000);
  delay(27);
  pulseIR(440);
  delayMicroseconds(1500);
  pulseIR(460);
  delayMicroseconds(3440);
  pulseIR(480);
}
