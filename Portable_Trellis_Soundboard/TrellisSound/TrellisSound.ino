#include <Wire.h>
#include "Adafruit_Trellis.h"
#include <SoftwareSerial.h>
#include "Adafruit_Soundboard.h"
 
/************ sound board setup ***********/
// Choose any two pins that can be used with SoftwareSerial to RX & TX
#define SFX_TX 5
#define SFX_RX 6
// Connect to the RST pin on the Sound Board
#define SFX_RST 4
 
#define SFX_ACT 1 // the 'ACT'ivity LED, to tell us if we're still playing
 
// You can also monitor the ACT pin for when audio is playing!
// we'll be using software serial
SoftwareSerial ss = SoftwareSerial(SFX_TX, SFX_RX);
// pass the software serial to Adafruit_soundboard, the second
// argument is the debug port (not used really) and the third 
// arg is the reset pin
Adafruit_Soundboard sfx = Adafruit_Soundboard(&ss, NULL, SFX_RST);
 
/************ Trellis setup ***********/
 
Adafruit_Trellis matrix0 = Adafruit_Trellis();
Adafruit_TrellisSet trellis =  Adafruit_TrellisSet(&matrix0);
 
// set to however many you're working with here, up to 8
#define NUMTRELLIS 1
#define numKeys (NUMTRELLIS * 16)
 
// Connect Trellis Vin to 5V and Ground to ground.
// Connect the INT wire to pin #A2 (can change later!)
#define INTPIN A2
// Connect I2C SDA pin to your Arduino SDA line
// Connect I2C SCL pin to your Arduino SCL line
 
 
char PadToTrack[numKeys][12] = {"T00RAND0WAV",
                                "T00RAND1WAV",
                                "T00RAND2WAV",
                                "T00RAND3WAV",
                                "T10HOLDLWAV",
                               
};       
 
/************ main setup ***********/
 
void setup() {
  Serial.begin(115200);
  Serial.println("Trellis Demo");
 
  // INT pin requires a pullup
  pinMode(INTPIN, INPUT);
  digitalWrite(INTPIN, HIGH);
  // ACT LED
  pinMode(SFX_ACT, INPUT);
  digitalWrite(SFX_ACT, HIGH); //pullup
  
  // begin() with the addresses of each panel in order
  trellis.begin(0x70);  // only one

  // light up all the LEDs in order
  for (uint8_t i=0; i<numKeys; i++) {
    trellis.setLED(i);
    trellis.writeDisplay();    
    delay(50);
  }
  // then turn them off
  for (uint8_t i=0; i<numKeys; i++) {
    trellis.clrLED(i);
    trellis.writeDisplay();    
    delay(50);
  }
 
  // softwareserial at 9600 baud
  ss.begin(9600);
 
  if (!sfx.reset()) {
    Serial.println("SFX not found");
    while (1);
  }
  Serial.println("SFX board found");
 
  uint8_t files = sfx.listFiles();
 
  Serial.println("File Listing");
  Serial.println("========================");
  Serial.println();
  Serial.print("Found "); Serial.print(files); Serial.println(" Files");
  for (uint8_t f=0; f<files; f++) {
    Serial.print(f); 
    Serial.print("\tname: "); Serial.print(sfx.fileName(f));
    Serial.print("\tsize: "); Serial.println(sfx.fileSize(f));
  }
  Serial.println("========================");  
  
  trellis.clear();
  trellis.writeDisplay();
}
 
int currentPlaying = -1;
 
void loop() {
  delay(30); // 30ms delay is required, dont remove me!
  
  if (digitalRead(SFX_ACT) && (currentPlaying != -1)) {
     // *not* playing anything according to ACT lite
     trellis.clear();
     trellis.writeDisplay();
     currentPlaying = -1;
  }
  
  // If a button was just pressed or released...
  if (trellis.readSwitches()) {
    // go through every button
    for (uint8_t i=0; i<numKeys; i++) {
       // if it was pressed, turn it on
       if (trellis.isKeyPressed(i) && (i != currentPlaying)) {
          Serial.print("v"); Serial.println(i);
    
          trellis.clear();
          
//          if (! digitalRead(SFX_ACT)) {
//            Serial.println("stop..."); // check ACT lite first?
//            if (! sfx.stop() ) {
//                Serial.println("Failed to stop");
//            }
//          }
 
          // play!         
          char * filename = PadToTrack[i];
          int ret = sfx.playTrack(filename);
          Serial.print("Playing "); Serial.println(filename);
          
          if (! ret) {
            Serial.println("Failed to play track?");
          } else {
            trellis.setLED(i);
          }
          trellis.writeDisplay();
          
          delay(25);  // give it a chance to start playing
          currentPlaying = i;
          break;
      }
    }
  }
}
