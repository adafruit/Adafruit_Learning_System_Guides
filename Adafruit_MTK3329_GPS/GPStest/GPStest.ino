/ Test code for Adafruit GPS modules using MTK driver
// such as www.adafruit.com/products/660 (discontinued)
// For new use see www.adafruit.com/products/746 (needs different code)
// help support open source hardware & software! -adafruit

#include <SoftSerial.h>
SoftSerial mySerial(2, 3);

// Connect the GPS Power pin to 3.3V
// Connect the GPS Ground pin to ground
// Connect the GPS VBAT pin to 3.3V if no battery is used
// Connect the GPS TX (transmit) pin to Digital 2
// Connect the GPS RX (receive) pin to Digital 3
// For 3.3V only modules such as the UP501, connect a 10K
// resistor between digital 3 and GPS RX and a 10K resistor 
// from GPS RX to ground.

// different commands to set the update rate from once a second (1 Hz) to 10 times a second (10Hz)
#define PMTK_SET_NMEA_UPDATE_1HZ  "$PMTK220,1000*1F"
#define PMTK_SET_NMEA_UPDATE_5HZ  "$PMTK220,200*2C"
#define PMTK_SET_NMEA_UPDATE_10HZ "$PMTK220,100*2F"

// turn on only the second sentence (GPRMC)
#define PMTK_SET_NMEA_OUTPUT_RMCONLY "$PMTK314,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*29"
// turn on ALL THE DATA
#define PMTK_SET_NMEA_OUTPUT_ALLDATA "$PMTK314,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0*28"

// to generate your own sentences, check out the MTK command datasheet and use a checksum calculator
// such as the awesome http://www.hhhh.org/wiml/proj/nmeaxor.html

void setup()  
{
  Serial.begin(57600);
  Serial.println("Adafruit MTK3329 NMEA test!");

  // 9600 NMEA is the default baud rate
  mySerial.begin(9600);
  
  // uncomment this line to turn on only the "minimum recommended" data for high update rates!
  //mySerial.println(PMTK_SET_NMEA_OUTPUT_RMCONLY);

  // uncomment this line to turn on all the available data - for 9600 baud you'll want 1 Hz rate
  mySerial.println(PMTK_SET_NMEA_OUTPUT_ALLDATA);
  
  // Set the update rate
  // 1 Hz update rate
  mySerial.println(PMTK_SET_NMEA_UPDATE_1HZ);
  // 5 Hz update rate- for 9600 baud you'll have to set the output to RMC only (see above)
  //mySerial.println(PMTK_SET_NMEA_UPDATE_5HZ);
  // 10 Hz update rate - for 9600 baud you'll have to set the output to RMC only (see above)
  //mySerial.println(PMTK_SET_NMEA_UPDATE_10HZ);

}

void loop()                     // run over and over again
{

  if (mySerial.available()) {
      Serial.print((char)mySerial.read());
  }
  if (Serial.available()) {
      mySerial.print((char)Serial.read());
  }
}
