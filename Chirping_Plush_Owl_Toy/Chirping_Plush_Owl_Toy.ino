/* 
Chirp Owl written by Becky Stern and T Main for Adafruit Industries
Tutorial: http://learn.adafruit.com/chirping-plush-owl-toy/

Includes animal sounds by Mike Barela
http://learn.adafruit.com/adafruit-trinket-modded-stuffed-animal/animal-sounds

based in part on Debounce
 created 21 November 2006
 by David A. Mellis
 modified 30 Aug 2011
 by Limor Fried
 modified 28 Dec 2012
 by Mike Walters
 
 This example code is in the public domain.
 
 http://www.arduino.cc/en/Tutorial/Debounce
 */

// constants won't change. They're used here to 
// set pin numbers:
const int buttonPin = 0;    // the number of the pushbutton pin
const int speakerPin = 2;      // the number of the LED pin
const int ledPin = 1;

// Variables will change:
int ledState = HIGH;         // the current state of the output pin
int buttonState;             // the current reading from the input pin
int lastButtonState = LOW;   // the previous reading from the input pin

// the following variables are long's because the time, measured in miliseconds,
// will quickly become a bigger number than can be stored in an int.
long lastDebounceTime = 0;  // the last time the output pin was toggled
long debounceDelay = 50;    // the debounce time; increase if the output flickers

void setup() {
  pinMode(buttonPin, INPUT_PULLUP);
  pinMode(speakerPin, OUTPUT);
  //digitalWrite(speakerPin, HIGH);
  digitalWrite(ledPin, LOW);
  //digitalWrite(buttonPin, HIGH);
  // set initial LED state
  //digitalWrite(speakerPin, ledState);
  //Serial.begin(9600);
}

void loop() {
  // read the state of the switch into a local variable:
  int reading = digitalRead(buttonPin);

  // check to see if you just pressed the button 
  // (i.e. the input went from LOW to HIGH),  and you've waited 
  // long enough since the last press to ignore any noise:  

  // If the switch changed, due to noise or pressing:
  if (reading != lastButtonState) {
    // reset the debouncing timer
    lastDebounceTime = millis();
  } 
  
  if ((millis() - lastDebounceTime) > debounceDelay) {
    // whatever the reading is at, it's been there for longer
    // than the debounce delay, so take it as the actual current state:

    // if the button state has changed:
    if (reading != buttonState) {
      buttonState = reading;

      // only toggle the LED if the new button state is HIGH
      //Serial.println("chirp");
        chirp(); // change this line to change animal sound
      	//meow();
        //meow2();
        ////mew();
        //ruff();
        //arf();
    }
  }
  
  // set the LED:
  //digitalWrite(speakerPin, ledState);

  // save the reading.  Next time through the loop,
  // it'll be the lastButtonState:
  lastButtonState = reading;
}


// Generate the Bird Chirp sound
void chirp() {
 for(uint8_t i=200; i>180; i--)
   playTone(i,9);
}

// Play a tone for a specific duration.  value is not frequency to save some
//   cpu cycles in avoiding a divide.  
void playTone(int16_t tonevalue, int duration) {
 for (long i = 0; i < duration * 1000L; i += tonevalue * 2) {
   digitalWrite(speakerPin, HIGH);
   delayMicroseconds(tonevalue);
   digitalWrite(speakerPin, LOW);
   delayMicroseconds(tonevalue);
 }    
}

void meow() {  // cat meow (emphasis ow "me")
  uint16_t i;
  playTone(5100,50);        // "m" (short)
  playTone(394,180);        // "eee" (long)
  for(i=990; i<1022; i+=2)  // vary "ooo" down
     playTone(i,8);
  playTone(5100,40);        // "w" (short)
}

void meow2() {  // cat meow (emphasis on "ow")
  uint16_t i;
  playTone(5100,55);       // "m" (short)
  playTone(394,170);       // "eee" (long)
  delay(30);               // wait a tiny bit
  for(i=330; i<360; i+=2)  // vary "ooo" down
     playTone(i,10);
  playTone(5100,40);       // "w" (short)
}

void mew() {  // cat mew
  uint16_t i;
  playTone(5100,55);       // "m"   (short)
  playTone(394,130);       // "eee" (long)
  playTone(384,35);        // "eee" (up a tiny bit on end)
  playTone(5100,40);       // "w"   (short)
}

void ruff() {   // dog ruff
  uint16_t i;
  for(i=890; i<910; i+=2)     // "rrr"  (vary down)
     playTone(i,3);
  playTone(1664,150);         // "uuu" (hard to do)
  playTone(12200,70);         // "ff"  (long, hard to do)
}

void arf() {    // dog arf
  uint16_t i;
  playTone(890,25);          // "a"    (short)
  for(i=890; i<910; i+=2)    // "rrr"  (vary down)
     playTone(i,5);
  playTone(4545,80);         // intermediate
  playTone(12200,70);        // "ff"   (shorter, hard to do)
}