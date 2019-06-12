#include <SoftwareSerial.h>
#include "Adafruit_FONA.h"

#define FONA_TX 3
#define FONA_RX 4
#define FONA_RST 5
#define FONA_RI 2

#define MOTOR_PWM A1
#define MOTOR_1 A2
#define MOTOR_2 A3

#define LED 13

#define OPEN true
#define CLOSE false

#define BUSYWAIT 5000  // milliseconds

// this is a large buffer for replies
char replybuffer[255];

// or comment this out & use a hardware serial port like Serial1 (see below)
SoftwareSerial fonaSS = SoftwareSerial(FONA_TX, FONA_RX);

Adafruit_FONA fona = Adafruit_FONA(FONA_RST);

uint8_t readline(char *buff, uint8_t maxbuff, uint16_t timeout = 0);

boolean fonainit(void) {
  Serial.println(F("Initializing....(May take 3 seconds)"));

  digitalWrite(LED, HIGH);
  delay(100);
  digitalWrite(LED, LOW);
  delay(100);
  digitalWrite(LED, HIGH);
  delay(100);
  digitalWrite(LED, LOW);
  delay(100);
   
  // make it slow so its easy to read!
  fonaSS.begin(4800); // if you're using software serial
  //Serial1.begin(4800); // if you're using hardware serial

  // See if the FONA is responding
  if (! fona.begin(fonaSS)) {           // can also try fona.begin(Serial1) 
    Serial.println(F("Couldn't find FONA"));
    return false;
  }
  Serial.println(F("FONA is OK"));
  return true;
  
}

void setup() {
  while (!Serial);  // useful for Leonardo/Micro, remove in production!

  // set LED output for debugging
  pinMode(LED, OUTPUT);
  
  // set up motor pins, but turn them off
  pinMode(MOTOR_1, OUTPUT);
  digitalWrite(MOTOR_1, LOW);
  pinMode(MOTOR_2, OUTPUT);
  digitalWrite(MOTOR_2, LOW);  
  pinMode(MOTOR_PWM, OUTPUT);
  digitalWrite(MOTOR_PWM, LOW);  
  
  Serial.begin(115200);
  Serial.println(F("FONA basic test"));

  while (! fonainit()) {
    delay(5000);
  }
  
  // Print SIM card IMEI number.
  char imei[15] = {0}; // MUST use a 16 character buffer for IMEI!
  uint8_t imeiLen = fona.getIMEI(imei);
  if (imeiLen > 0) {
    Serial.print("SIM card IMEI: "); Serial.println(imei);
  }
  
  pinMode(FONA_RI, INPUT);
  digitalWrite(FONA_RI, HIGH); // turn on pullup on RI
  // turn on RI pin change on incoming SMS!
  fona.sendCheckReply(F("AT+CFGRI=1"), F("OK"));
}

int8_t lastsmsnum = 0;

void loop() {
   digitalWrite(LED, HIGH);
   delay(100);
   digitalWrite(LED, LOW);
       
  while (fona.getNetworkStatus() != 1) {
    Serial.println("Waiting for cell connection");
    delay(2000);
  }
  
  // this is a 'busy wait' loop, we check if the interrupt
  // pin went low, and after BUSYWAIT milliseconds break out to check
  // manually for SMS's and connection status
  // This would be a good place to 'sleep'
  for (uint16_t i=0; i<BUSYWAIT; i++) {
     if (! digitalRead(FONA_RI)) {
        // RI pin went low, SMS received?
        Serial.println(F("RI went low"));
        break;
     } 
     delay(1);
  }
  
  int8_t smsnum = fona.getNumSMS();
  if (smsnum < 0) {
    Serial.println(F("Could not read # SMS"));
    return;
  } else {
    Serial.print(smsnum); 
    Serial.println(F(" SMS's on SIM card!"));
  }
  
  if (smsnum == 0) return;

  // there's an SMS!
  uint8_t n = 1; 
  while (true) {
     uint16_t smslen;
     char sender[25];
     
     Serial.print(F("\n\rReading SMS #")); Serial.println(n);
     uint8_t len = fona.readSMS(n, replybuffer, 250, &smslen); // pass in buffer and max len!
     // if the length is zero, its a special case where the index number is higher
     // so increase the max we'll look at!
     if (len == 0) {
        Serial.println(F("[empty slot]"));
        n++;
        continue;
     }
     if (! fona.getSMSSender(n, sender, sizeof(sender))) {
       // failed to get the sender?
       sender[0] = 0;
     }
     
     Serial.print(F("***** SMS #")); Serial.print(n);
     Serial.print(" ("); Serial.print(len); Serial.println(F(") bytes *****"));
     Serial.println(replybuffer);
     Serial.print(F("From: ")); Serial.println(sender);
     Serial.println(F("*****"));
     
     if (strcasecmp(replybuffer, "open sesame") == 0) {
       // open the door!
       digitalWrite(LED, HIGH);
       moveMotor(OPEN, 800);
       digitalWrite(LED, LOW);
     }
     if (strcasecmp(replybuffer, "close cadabra") == 0) {
       // close the door!
       digitalWrite(LED, HIGH);
       moveMotor(CLOSE, 800);
       digitalWrite(LED, LOW);
     }
     
     delay(3000);
     break;
  }  
  fona.deleteSMS(n);
 
  delay(1000); 
}


void moveMotor(boolean direction, uint16_t t) {
  digitalWrite(MOTOR_PWM, HIGH);   // enable motor
  if (direction) {
    digitalWrite(MOTOR_1, HIGH);
    digitalWrite(MOTOR_2, LOW);
  } else {
    digitalWrite(MOTOR_2, HIGH);
    digitalWrite(MOTOR_1, LOW);  
  }
  delay(t);
  digitalWrite(MOTOR_1, LOW);
  digitalWrite(MOTOR_2, LOW);

  digitalWrite(MOTOR_PWM, LOW);    // disable motor
}
