//Ada_remoteFXTrigger_NeoTrellis_TX
//Remote Effects Trigger Box Transmitter
//by John Park
// & Erin St. Blaine
//for Adafruit Industries

// General purpose button box
// for triggering remote effects
// using packet radio Feather boards
//
//
//MIT License

#include <SPI.h>
#include <RH_RF69.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_NeoTrellis.h>

#include <Encoder.h>
int m = 0; //variable to increment through menu list
int x = 17; //variable for referencing buttons -- setting X to a non-existent button
/********* Encoder Setup ***************/
#define PIN_ENCODER_SWITCH 11
Encoder knob(10, 12);
uint8_t activeRow = 0;
long pos = -999;
long newpos;
int prevButtonState = HIGH;
bool needsRefresh = true;
bool advanced = false;
unsigned long startTime;


/********* NeoTrellis Setup ***************/
Adafruit_NeoTrellis trellis;

#define MOMENTARY 0
#define LATCHING 1
#define MODE LATCHING //all Trellis buttons in latching mode
#define NUMTRELLIS 1
#define numKeys (NUMTRELLIS * 16)
#define INTPIN A2
int NUM_SCREENS = 3;  // change this number to add more screens


//define a callback for key presses
TrellisCallback blink(keyEvent evt){
  // Check is the pad pressed?
  if (evt.bit.EDGE == SEESAW_KEYPAD_EDGE_RISING) {
    //trellis.pixels.setPixelColor(evt.bit.NUM, 0xFFFFFF); //on rising
  } else if (evt.bit.EDGE == SEESAW_KEYPAD_EDGE_FALLING) {
  // or is the pad released?
  //trellis.pixels.setPixelColor(m, Wheel(map(m*2, 0, trellis.pixels.numPixels(), 0, 255))); //off falling
   x = evt.bit.NUM;
  }

  // Turn on/off the neopixels!
  trellis.pixels.show();

  return 0;
} 



/************ OLED Setup ***************/
Adafruit_SSD1306 oled = Adafruit_SSD1306();
#if defined(ESP8266)
  #define BUTTON_A 0
  #define BUTTON_B 16
  #define BUTTON_C 2
  #define LED      0
#elif defined(ESP32)
  #define BUTTON_A 15
  #define BUTTON_B 32
  #define BUTTON_C 14
  #define LED      13
#elif defined(ARDUINO_STM32F2_FEATHER)
  #define BUTTON_A PA15
  #define BUTTON_B PC7
  #define BUTTON_C PC5
  #define LED PB5
#elif defined(TEENSYDUINO)
  #define BUTTON_A 4
  #define BUTTON_B 3
  #define BUTTON_C 8
  #define LED 13
#elif defined(ARDUINO_FEATHER52)
  #define BUTTON_A 31
  #define BUTTON_B 30
  #define BUTTON_C 27
  #define LED 17
#else // 32u4, M0, and 328p
  #define BUTTON_A 9
  #define BUTTON_B 6
  #define BUTTON_C 5
  #define LED      13
#endif


/************ Radio Setup ***************/
// Can be changed to 434.0 or other frequency, must match RX's freq!
#define RF69_FREQ 915.0

#if defined (__AVR_ATmega32U4__) // Feather 32u4 w/Radio
  #define RFM69_CS      8
  #define RFM69_INT     7
  #define RFM69_RST     4
#endif

#if defined(ARDUINO_SAMD_FEATHER_M0) // Feather M0 w/Radio
  #define RFM69_CS      8
  #define RFM69_INT     3
  #define RFM69_RST     4
#endif

#if defined (__AVR_ATmega328P__)  // Feather 328P w/wing
  #define RFM69_INT     3  // 
  #define RFM69_CS      4  //
  #define RFM69_RST     2  // "A"
#endif

#if defined(ESP32)    // ESP32 feather w/wing
  #define RFM69_RST     13   // same as LED
  #define RFM69_CS      33   // "B"
  #define RFM69_INT     27   // "A"
#endif


// Singleton instance of the radio driver
RH_RF69 rf69(RFM69_CS, RFM69_INT);

int lastButton=17; //last button pressed for Trellis logic

int menuList[8]={1,2,3,4,5,6,7,8}; //for rotary encoder choices
//int m = 0; //variable to increment through menu list
int lastTB[8] = {16, 16, 16, 16, 16, 16, 16, 16}; //array to store per-menu Trellis button


/*******************SETUP************/
void setup() {
  delay(500);
  Serial.begin(115200);
  //while (!Serial) { delay(1); } // wait until serial console is open, 
  //remove if not tethered to computer

pinMode(PIN_ENCODER_SWITCH, INPUT_PULLUP);//set encoder push switch pin to input pullup
pinMode(INTPIN, INPUT);
  
 // digitalPinToInterrupt(10); //on M0, Encoder library doesn't auto set these as interrupts
 // digitalPinToInterrupt(12);
  
  // Initialize OLED display
  oled.begin(SSD1306_SWITCHCAPVCC, 0x3C);  // initialize with the I2C addr 0x3C (for the 128x32)
  oled.setTextWrap(false);
  oled.display();
  delay(500);
  oled.clearDisplay();
  oled.display();
  oled.setTextSize(2);
  oled.setTextColor(WHITE);
  pinMode(BUTTON_A, INPUT_PULLUP);
  pinMode(BUTTON_B, INPUT_PULLUP);
  pinMode(BUTTON_C, INPUT_PULLUP);
  pinMode(LED, OUTPUT);     
  pinMode(RFM69_RST, OUTPUT);
  digitalWrite(RFM69_RST, LOW);

  // manual reset
  digitalWrite(RFM69_RST, HIGH);
  delay(10);
  digitalWrite(RFM69_RST, LOW);
  delay(10);
  
  if (!rf69.init()) {
    Serial.println("RFM69 radio init failed");
    while (1);
  }
  Serial.println("RFM69 radio init OK!");
  
  // Defaults after init are 434.0MHz, modulation GFSK_Rb250Fd250, +13dbM (for low power module)
  // No encryption
  if (!rf69.setFrequency(RF69_FREQ)) {
    Serial.println("setFrequency failed");
  }

  // If you are using a high power RF69 eg RFM69HW, you *must* set a Tx power with the
  // ishighpowermodule flag set like this:
  rf69.setTxPower(14, true);

  // The encryption key has to be the same as the one in the server
  uint8_t key[] = { 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
                    0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08};
  rf69.setEncryptionKey(key);
  
  pinMode(LED, OUTPUT);

  Serial.print("RFM69 radio @");  Serial.print((int)RF69_FREQ);  Serial.println(" MHz");

  oled.setCursor(0,0);
  oled.println("RFM69 @ ");
  oled.print((int)RF69_FREQ);
  oled.println(" MHz");
  oled.display();
  delay(1200); //pause to let freq message be read by a human

  oled.clearDisplay();
  oled.setCursor(0,0);
  oled.println("REMOTE FX");
  oled.setCursor(0,16);
  oled.println("TRIGGER");  
  oled.display();

   if (!trellis.begin()) {
    Serial.println("Could not start trellis, check wiring?");
    while(1);
  } else {
    Serial.println("NeoPixel Trellis started");
  }

  //activate all NeoTrellis keys and set callbacks
  for(int i=0; i<NEO_TRELLIS_NUM_KEYS; i++){
    trellis.activateKey(i, SEESAW_KEYPAD_EDGE_RISING);
    trellis.activateKey(i, SEESAW_KEYPAD_EDGE_FALLING);
    trellis.registerCallback(i, blink);
  }

  //do a little animation to show we're on
  for (uint16_t i=0; i<trellis.pixels.numPixels(); i++) {
    trellis.pixels.setPixelColor(i, Wheel(map(i, 0, trellis.pixels.numPixels(), 0, 255)));
    trellis.pixels.show();
    delay(50);
  }
  for (uint16_t i=0; i<trellis.pixels.numPixels(); i++) {
    trellis.pixels.setPixelColor(i, 0x000000);
    trellis.pixels.show();
    delay(50);
  }

}

//////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////

void loop() {
   

/*************Rotary Encoder Menu***********/

    //check the encoder knob, set the current position as origin
    long newpos = knob.read() / 4;//divide for encoder detents
    
    /* // for debugging
     Serial.print("pos=");
     Serial.print(pos);
     Serial.print(", newpos=");
     Serial.println(newpos);
    */

    if(newpos != pos){
      int diff = newpos - pos;//check the different between old and new position
      if(diff>=1){
        m++; 
        m = (m+NUM_SCREENS) % NUM_SCREENS;//modulo to roll over the m variable through the list size
       }

      if(diff==-1){ //rotating backwards
         m--;
         m = (m+NUM_SCREENS) % NUM_SCREENS;
       }
      /* //uncomment for debugging or general curiosity
      Serial.print("Diff = ");
      Serial.print(diff);
      Serial.print("  pos= ");
      Serial.print(pos);
      Serial.print(", newpos=");
      Serial.println(newpos);
      Serial.println(menuList[m]);
      */

      pos = newpos;

      // Serial.print("m is: ");
      //Serial.println(m);
  //write to the display
      oled.setCursor(0,3);
      oled.clearDisplay();

      int p; //for drawing bullet point menu location pixels
      int q;
  
      if (m==0){
        for(p=4;p<8;p++){
          for(q=0;q<4;q++){
            oled.drawPixel(q,p,WHITE);
          }
        }
        oled.print(" Solids");
        clearPixels();
        trellis.pixels.setPixelColor(0, 50,0,0);
        trellis.pixels.setPixelColor(1, 50,50,0);
        trellis.pixels.setPixelColor(2, 0,50,0);
        trellis.pixels.setPixelColor(3, 0,0,50);
        trellis.pixels.setPixelColor(4, 20,0,50);
        trellis.pixels.setPixelColor(5, 50,0,20);
        trellis.pixels.setPixelColor(6, 100,100,100);
        trellis.pixels.setPixelColor(7, 10,10,10);
        trellis.pixels.show();
      }
      if (m==1){
        for(p=8;p<12;p++){
          for(q=0;q<4;q++){
            oled.drawPixel(q,p,WHITE);
          }
        }
        oled.print(" Gradients");
        clearPixels();
        trellis.pixels.setPixelColor(0, 50,0,0);
        trellis.pixels.setPixelColor(1, 50,50,0);
        trellis.pixels.setPixelColor(2, 0,50,0);
        trellis.pixels.setPixelColor(3, 0,0,50);
        trellis.pixels.setPixelColor(4, 20,0,50);
        trellis.pixels.setPixelColor(5, 50,0,20);
        trellis.pixels.setPixelColor(6, 100,100,100);
        trellis.pixels.setPixelColor(7, 10,10,10);
        trellis.pixels.show();
      }
      if (m==2){
        for(p=12;p<16;p++){
          for(q=0;q<4;q++){
            oled.drawPixel(q,p,WHITE);
          }
        }
        oled.print(" Rainbows");
        clearPixels();
        trellis.pixels.setPixelColor(0, 50,0,0);
        trellis.pixels.setPixelColor(1, 50,50,0);
        trellis.pixels.setPixelColor(2, 0,50,0);
        trellis.pixels.setPixelColor(7, 10,10,10);
        trellis.pixels.show();
      }
 
  
      
      oled.display();
    }

    char radiopacket[20];
   
   
/**************Solids**************/
       
        if(m==0){ //next menu item
       
            if (x==0){ //button 1 sends button A command
              radiopacket[0] = 'A';
              oled.clearDisplay();
              oled.setCursor(0,0);
              oled.print("Solid");
              oled.setCursor(50,16);
              oled.print("RED");
              oled.display(); 
            }
            if (x==1){ //button 2 sends button B command
              radiopacket[0] = 'B';
             oled.clearDisplay();
              oled.setCursor(0,0);
              oled.print("Solid");
              oled.setCursor(50,16);
              oled.print("GOLD");
              oled.display(); 
            }
            if (x==2){ //button 3 sends button C command
              radiopacket[0] = 'C';
             oled.clearDisplay();
              oled.setCursor(0,0);
              oled.print("Solid");
              oled.setCursor(50,16);
              oled.print("GREEN");
              oled.display();  
            } 

            if (x==3){ //button 4 sends button D command
              radiopacket[0] = 'D';
             oled.clearDisplay();
              oled.setCursor(0,0);
              oled.print("Solid");
              oled.setCursor(50,16);
              oled.print("BLUE");
              oled.display();  
            }

            if (x==4){ //button 5 sends button E command
              radiopacket[0] = 'E';
              oled.clearDisplay();
              oled.setCursor(0,0);
              oled.print("Solid");
              oled.setCursor(50,16);
              oled.print("PURPLE");
              oled.display(); 
            }
            if (x==5){ //button 6 sends button F command
              radiopacket[0] = 'F';
             oled.clearDisplay();
              oled.setCursor(0,0);
              oled.print("Solid");
              oled.setCursor(50,16);
              oled.print("PINK");
              oled.display(); 
            }
            if (x==6){ //button 7 sends button G command
              radiopacket[0] = 'G';
             oled.clearDisplay();
              oled.setCursor(0,0);
              oled.print("Solid");
              oled.setCursor(50,16);
              oled.print("WHITE");
              oled.display();  
            } 

            if (x==7){ //button 8 sends button H command
              radiopacket[0] = 'H';
             oled.clearDisplay();
              oled.setCursor(0,0);
              oled.print("Solid");
              oled.setCursor(50,16);
              oled.print("OFF");
              oled.display();  
            }
     

 trellis.pixels.show(); // tell the trellis to set the LEDs we requested
}

/**************Gradients**************/
       
        if(m==1){ //next menu item
       
            if (x==0){ //button 1 sends button A command
              radiopacket[0] = 'I';
              oled.clearDisplay();
              oled.setCursor(0,0);
              oled.print("Gradient");
              oled.setCursor(50,16);
              oled.print("RED");
              oled.display(); 
            }
            if (x==1){ //button 2 sends button B command
              radiopacket[0] = 'J';
             oled.clearDisplay();
              oled.setCursor(0,0);
              oled.print("Gradient");
              oled.setCursor(50,16);
              oled.print("GOLD");
              oled.display(); 
            }
            if (x==2){ //button 3 sends button C command
              radiopacket[0] = 'K';
             oled.clearDisplay();
              oled.setCursor(0,0);
              oled.print("Gradient");
              oled.setCursor(50,16);
              oled.print("GREEN");
              oled.display();  
            } 

            if (x==3){ //button 4 sends button D command
              radiopacket[0] = 'L';
             oled.clearDisplay();
              oled.setCursor(0,0);
              oled.print("Gradient");
              oled.setCursor(50,16);
              oled.print("BLUE");
              oled.display();  
            }

            if (x==4){ //button 5 sends button E command
              radiopacket[0] = 'M';
              oled.clearDisplay();
              oled.setCursor(0,0);
              oled.print("Gradient");
              oled.setCursor(50,16);
              oled.print("PURPLE");
              oled.display(); 
            }
            if (x==5){ //button 6 sends button F command
              radiopacket[0] = 'N';
             oled.clearDisplay();
              oled.setCursor(0,0);
              oled.print("Gradient");
              oled.setCursor(50,16);
              oled.print("PINK");
              oled.display(); 
            }
            if (x==6){ //button 7 sends button G command
              radiopacket[0] = 'O';
             oled.clearDisplay();
              oled.setCursor(0,0);
              oled.print("Gradient");
              oled.setCursor(50,16);
              oled.print("WHITE");
              oled.display();  
            } 

            if (x==7){ //button 8 sends button H command
              radiopacket[0] = 'H';
             oled.clearDisplay();
              oled.setCursor(0,0);
              oled.print("Gradient");
              oled.setCursor(50,16);
              oled.print("OFF");
              oled.display();  
            }
 trellis.pixels.show(); // tell the trellis to set the LEDs we requested
}


/**************Rainbows**************/
       
        if(m==2){ //next menu item
       
            if (x==0){ //button 1 sends button A command
              radiopacket[0] = 'P';
              oled.clearDisplay();
              oled.setCursor(0,0);
              oled.print("Rainbow");
              oled.setCursor(50,16);
              oled.print("FADE");
              oled.display(); 
            }
            if (x==1){ //button 2 sends button B command
              radiopacket[0] = 'Q';
             oled.clearDisplay();
              oled.setCursor(0,0);
              oled.print("Rainbow");
              oled.setCursor(50,16);
              oled.print("SOFT");
              oled.display(); 
            }
            if (x==2){ //button 3 sends button C command
              radiopacket[0] = 'R';
             oled.clearDisplay();
              oled.setCursor(0,0);
              oled.print("Rainbow");
              oled.setCursor(50,16);
              oled.print("TWINKLE");
              oled.display();  
            } 

            if (x==7){ //button 8 sends button H command
              radiopacket[0] = 'H';
             oled.clearDisplay();
              oled.setCursor(0,0);
              oled.print("Rainbow");
              oled.setCursor(50,16);
              oled.print("OFF");
              oled.display();  
            }
 trellis.pixels.show(); // tell the trellis to set the LEDs we requested
}



Serial.print("Sending "); 
          Serial.println(radiopacket[0]);

          rf69.send((uint8_t *)radiopacket, strlen(radiopacket));
          rf69.waitPacketSent(); 
          //reset packet so unassigned buttons don't send last command
          radiopacket[0]='Z'; //also being used to turn off NeoPixels 
          //from any unused button

          if (rf69.waitAvailableTimeout(1000)) { 
            // Should be a message for us now   
            uint8_t buf[RH_RF69_MAX_MESSAGE_LEN];
            uint8_t len = sizeof(buf);
            
            if (! rf69.recv(buf, &len)) {
              Serial.println("Receive failed");
              return;
            }
            digitalWrite(LED, HIGH);
            rf69.printBuffer("Received: ", buf, len);
            buf[len] = 0;
            
            //Serial.print("TX Got: "); 
            //Serial.println((char*)buf);
            Serial.print("RSSI: "); 
            Serial.println(rf69.lastRssi(), DEC);

            //delay(1000);//chill for a moment before returning the message to RX unit

            /*************Reply message from RX unit***********/
            //oled.clearDisplay();
            //oled.print((char*)buf[0]);
            //oled.print("RSSI: "); oled.print(rf69.lastRssi());
            //oled.display(); 
            
            
            digitalWrite(LED, LOW);
          }

          //lastButton=i;//set for next pass through to turn this one off
      

       trellis.read();
     delay(100); //the NeoTrellis has a resolution of around 60hz
    
 }


/******************************************/

// Input a value 0 to 255 to get a color value.
// The colors are a transition r - g - b - back to r.
uint32_t Wheel(byte WheelPos) {
  if(WheelPos < 85) {
   return trellis.pixels.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
  } else if(WheelPos < 170) {
   WheelPos -= 85;
   return trellis.pixels.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  } else {
   WheelPos -= 170;
   return trellis.pixels.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
  return 0;
}

void clearPixels() {
 for (uint16_t i=0; i<trellis.pixels.numPixels(); i++) {
    trellis.pixels.setPixelColor(i, 0x000000);
    trellis.pixels.show();
    delay(2);
  }  
  }

 
