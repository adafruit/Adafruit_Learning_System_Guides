/*
    AUTOCHEER DEVICE
    ---
    code by Andy Doro https://andydoro.com/

    using Adafruit Feather hardware
    will play an MP3 at a specified time each day

    sketch can easily be modified to perform some other functions at the specified time, such as operate physical/analog noisemakers


    HARDWARE
    ---
    - any Feather board, e.g. Feather M0 Basic Proto https://www.adafruit.com/product/2772

    - Adalogger FeatherWing https://www.adafruit.com/product/2922
    - CR1220 coin cell https://www.adafruit.com/product/380

    - Music Maker FeatherWing https://www.adafruit.com/product/3357 for 1/8" audio jack output
    or Music Maker FeatherWing w/Amp https://www.adafruit.com/product/3436 for speaker wire output
    - MicroSD card https://www.adafruit.com/product/1294 FAT formatted with "cheer.mp3"

    - FeatherWing Tripler https://www.adafruit.com/product/3417
    or Feather Stacking Headers https://www.adafruit.com/product/2830 for a different form factor



    SOFTWARE
    ---
    libraries
    - VS1053 https://github.com/adafruit/Adafruit_VS1053_Library for Music Maker
    - RCTlib https://github.com/adafruit/RTClib for RTC
    - DST_RTC https://github.com/andydoro/DST_RTC for Daylight Saving Time adjustments

    cheer.mp3, place on FAT formatted SD card and insert into Music Maker
    http://www.orangefreesounds.com/street-crowd-cheering-and-applauding/

*/

// Specifically for use with the Adafruit Feather, the pins are pre-set here!

// include SPI, MP3 and SD libraries
#include <SPI.h>
#include <SD.h>
#include <Adafruit_VS1053.h> // https://github.com/adafruit/Adafruit_VS1053_Library

// Date and time functions using a DS3231 RTC connected via I2C and Wire lib
#include <Wire.h>
#include "RTClib.h" // https://github.com/adafruit/RTClib
#include "DST_RTC.h" // download from https://github.com/andydoro/DST_RTC


// These are the pins used
#define VS1053_RESET   -1     // VS1053 reset pin (not used!)

// Feather ESP8266
#if defined(ESP8266)
#define VS1053_CS      16     // VS1053 chip select pin (output)
#define VS1053_DCS     15     // VS1053 Data/command select pin (output)
#define CARDCS          2     // Card chip select pin
#define VS1053_DREQ     0     // VS1053 Data request, ideally an Interrupt pin

// Feather ESP32
#elif defined(ESP32)
#define VS1053_CS      32     // VS1053 chip select pin (output)
#define VS1053_DCS     33     // VS1053 Data/command select pin (output)
#define CARDCS         14     // Card chip select pin
#define VS1053_DREQ    15     // VS1053 Data request, ideally an Interrupt pin

// Feather Teensy3
#elif defined(TEENSYDUINO)
#define VS1053_CS       3     // VS1053 chip select pin (output)
#define VS1053_DCS     10     // VS1053 Data/command select pin (output)
#define CARDCS          8     // Card chip select pin
#define VS1053_DREQ     4     // VS1053 Data request, ideally an Interrupt pin

// WICED feather
#elif defined(ARDUINO_STM32_FEATHER)
#define VS1053_CS       PC7     // VS1053 chip select pin (output)
#define VS1053_DCS      PB4     // VS1053 Data/command select pin (output)
#define CARDCS          PC5     // Card chip select pin
#define VS1053_DREQ     PA15    // VS1053 Data request, ideally an Interrupt pin

#elif defined(ARDUINO_NRF52832_FEATHER )
#define VS1053_CS       30     // VS1053 chip select pin (output)
#define VS1053_DCS      11     // VS1053 Data/command select pin (output)
#define CARDCS          27     // Card chip select pin
#define VS1053_DREQ     31     // VS1053 Data request, ideally an Interrupt pin

// Feather M4, M0, 328, nRF52840 or 32u4
#else
#define VS1053_CS       6     // VS1053 chip select pin (output)
#define VS1053_DCS     10     // VS1053 Data/command select pin (output)
#define CARDCS          5     // Card chip select pin
// DREQ should be an Int pin *if possible* (not possible on 32u4)
#define VS1053_DREQ     9     // VS1053 Data request, ideally an Interrupt pin

#endif

Adafruit_VS1053_FilePlayer musicPlayer =
  Adafruit_VS1053_FilePlayer(VS1053_RESET, VS1053_CS, VS1053_DCS, VS1053_DREQ, CARDCS);


//RTC_DS3231 rtc;
RTC_PCF8523 rtc; // RTC object
DST_RTC dst_rtc; // DST object

// Do you live in a country or territory that observes Daylight Saving Time?
// https://en.wikipedia.org/wiki/Daylight_saving_time_by_country
// Use 1 if you observe DST, 0 if you don't. This is programmed for DST in the US / Canada. If your territory's DST operates differently,
// you'll need to modify the code in the DST_RTC library to make this work properly.
#define OBSERVE_DST 1

// Define US or EU rules for DST comment out as required. More countries could be added with different rules in DST_RTC.cpp
const char rulesDST[] = "US"; // US DST rules
// const char rulesDST[] = "EU";   // EU DST rules

// the hour and minute you'd like MP3 to start playing
const int PLAYHOUR = 19; // 24 hour time
const int PLAYMIN = 0;

const int VOLUME = 0; // lower means louder!


void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  // if you're using Bluefruit or LoRa/RFM Feather, disable the radio module
  //pinMode(8, INPUT_PULLUP);

  // Wait for serial port to be opened, remove this line for 'standalone' operation
  /*while (!Serial) {
    delay(1);
    }
  */
  delay(500);
  Serial.println("\n\nAdafruit VS1053 Feather Test");

  if (! musicPlayer.begin()) { // initialise the music player
    Serial.println(F("Couldn't find VS1053, do you have the right pins defined?"));
    while (1);
  }

  Serial.println(F("VS1053 found"));


  // Set volume for left, right channels. lower numbers == louder volume!
  musicPlayer.setVolume(VOLUME, VOLUME);

  musicPlayer.sineTest(0x44, 1000);    // Make a tone to indicate VS1053 is working

  if (!SD.begin(CARDCS)) {
    Serial.println(F("SD failed, or not present"));
    while (1);  // don't do anything more
  }
  Serial.println("SD OK!");

  // list files
  printDirectory(SD.open("/"), 0);



#if defined(__AVR_ATmega32U4__)
  // Timer interrupts are not suggested, better to use DREQ interrupt!
  // but we don't have them on the 32u4 feather...
  musicPlayer.useInterrupt(VS1053_FILEPLAYER_TIMER0_INT); // timer int
#else
  // If DREQ is on an interrupt pin we can do background
  // audio playing
  musicPlayer.useInterrupt(VS1053_FILEPLAYER_PIN_INT);  // DREQ int
#endif

  // Play a file in the background, REQUIRES interrupts!
  /*
    Serial.println(F("Playing full track 001"));
    musicPlayer.playFullFile("/track001.mp3");

    Serial.println(F("Playing track 002"));
    musicPlayer.startPlayingFile("/track002.mp3");
  */

  // start RTC
  if (! rtc.begin()) {
    Serial.println("Couldn't find RTC");
    while (1);
  }

  // set RTC time if needed
  //if (rtc.lostPower()) { // if using DS3231
  if (! rtc.initialized()) {
    Serial.println("RTC lost power, lets set the time!");
    // following line sets the RTC to the date & time this sketch was compiled
    rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
    // DST? If we're in it, let's subtract an hour from the RTC time to keep our DST calculation correct. This gives us
    // Standard Time which our DST check will add an hour back to if we're in DST.
    if (OBSERVE_DST == 1) {
      DateTime standardTime = rtc.now();
      if (dst_rtc.checkDST(standardTime) == true) { // check whether we're in DST right now. If we are, subtract an hour.
        standardTime = standardTime.unixtime() - 3600;
      }
      rtc.adjust(standardTime);
    }
  }
}

void loop() {
  // put your main code here, to run repeatedly:

  DateTime theTime;
  // check time
  if (OBSERVE_DST == 1) {
    theTime = dst_rtc.calculateTime(rtc.now()); // takes into account DST
  } else {
    theTime = rtc.now(); // use if you don't need DST
  }

  printTheTime(theTime);

  byte theHour = theTime.hour();
  byte theMinute = theTime.minute();

  //check whether it's time to play mp3
  if (theHour == PLAYHOUR && theMinute == PLAYMIN) {
    Serial.println(F("Playing full track"));
    musicPlayer.playFullFile("/cheer.mp3");
  }

  // only check every second
  delay(1000);

}


// File listing helper
void printDirectory(File dir, int numTabs) {
  while (true) {

    File entry =  dir.openNextFile();
    if (! entry) {
      // no more files
      //Serial.println("**nomorefiles**");
      break;
    }
    for (uint8_t i = 0; i < numTabs; i++) {
      Serial.print('\t');
    }
    Serial.print(entry.name());
    if (entry.isDirectory()) {
      Serial.println("/");
      printDirectory(entry, numTabs + 1);
    } else {
      // files have sizes, directories do not
      Serial.print("\t\t");
      Serial.println(entry.size(), DEC);
    }
    entry.close();
  }
}

// print time to serial
void printTheTime(DateTime theTimeP) {
  Serial.print(theTimeP.year(), DEC);
  Serial.print('/');
  Serial.print(theTimeP.month(), DEC);
  Serial.print('/');
  Serial.print(theTimeP.day(), DEC);
  Serial.print(' ');
  Serial.print(theTimeP.hour(), DEC);
  Serial.print(':');
  Serial.print(theTimeP.minute(), DEC);
  Serial.print(':');
  Serial.print(theTimeP.second(), DEC);
  Serial.println();
}
