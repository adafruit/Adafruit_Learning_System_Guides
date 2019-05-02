// Track Your Treats - Ultimate GPS Shield Halloween Candy Route Tracker
// Author: Tony DiCola
//
// See the guide at:
// https://learn.adafruit.com/track-your-treats-halloween-candy-gps-tracker/overview
// 
// Released under a MIT license:
// https://opensource.org/licenses/MIT
#include <SPI.h>
#include <Adafruit_GPS.h>
#include <SoftwareSerial.h>
#include <SD.h>


// Configuration (you don't normally need to change these values):

#define LED_PIN              6   // Pin connected to an LED that flashes the status of the project.

#define BUTTON_PIN           5   // Pin connected to the button.

#define LOGGING_PERIOD_SEC   15  // Seconds to wait between logging GPS locations.

#define GPS_RX_PIN           8   // GPS receiver RX (pin 8 on the shield).

#define GPS_TX_PIN           7   // GPS receiver TX (pin 7 on the shield)   

#define SD_CS_PIN            10  // Chip select pin for SD card.


// Global state (you don't need to change these values):
SoftwareSerial gpsSerial(GPS_RX_PIN, GPS_TX_PIN);  // Software serial connection to GPS receiver.
Adafruit_GPS GPS(&gpsSerial);                      // GPS class to interact with receiver.
File logfile;                                      // SD card log file.
uint32_t logCounter = 0;                           // Counter until next location log is recorded.


// Halt function called when an error occurs.  Will print an error and stop execution while
// doing a fast blink of the LED.  If the watchdog is enabled it will reset after 8 seconds.
void halt(const __FlashStringHelper *error) {
  Serial.println(error);
  while (1) {
    digitalWrite(LED_PIN, LOW);
    delay(100); 
    digitalWrite(LED_PIN, HIGH);
    delay(100);
  }
}

// Timer interrupt called every millisecond to check for new data from the GPS.
SIGNAL(TIMER0_COMPA_vect) {
  // Check for new GPS data.
  GPS.read();
  // Decrease the count since last location log.
  if (logCounter > 0) {
    logCounter--;
  }
}

// Log the current GPS location with the specified note.
void logLocation(const char* note) {
  logfile.print(GPS.latitudeDegrees, 6);
  logfile.print(',');
  logfile.print(GPS.longitudeDegrees, 6);
  logfile.print(',');
  logfile.print(note);
  logfile.println();
  logfile.flush();
}

void setup() {
  // Initialize serial port.
  Serial.begin(115200);
  Serial.println(F("Track your Treats - Ultimate GPS Shield"));

  // Initialize LED and button.
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  // make sure that the default chip select pin is set to
  // output, even if you don't use it:
  pinMode(SD_CS_PIN, OUTPUT);

  // Initialize SD card (assumes running on Uno, for Leonardo see below).
  if (!SD.begin(SD_CS_PIN)) {
  // Initialize SD card for Leonardo or other chips (using software SPI)
  //if (!SD.begin(SD_CS_PIN, 11, 12, 13)) {
    halt(F("Card init. failed!"));
  }

  // Create the next log file on the SD card.
  char filename[15];
  strcpy(filename, "GPSLOG00.CSV");
  for (uint8_t i = 0; i < 100; i++) {
    filename[6] = '0' + i/10;
    filename[7] = '0' + i%10;
    // Create file if it does not exist.
    if (!SD.exists(filename)) {
      break;
    }
  }
  Serial.print("Using log file: "); 
  Serial.println(filename);

  // Open the log file.
  logfile = SD.open(filename, FILE_WRITE);
  if(!logfile) {
    halt(F("Failed to open log file!"));
  }

  // Set the first line of the log file as the column headers.
  logfile.println("latitude,longitude,note");
  logfile.flush();

  // Connect to the GPS receiver and configure it to receive location updates once a second.
  GPS.begin(9600);
  GPS.sendCommand(PMTK_SET_NMEA_OUTPUT_RMCONLY); // Recommended minimum output only (all we need for this project).
  GPS.sendCommand(PMTK_SET_NMEA_UPDATE_1HZ);     // Once a second update rate.
  GPS.sendCommand(PGCMD_NOANTENNA);              // Turn off antenna status.
 
  // Configure timer0 compare interrupt to run and parse GPS data every millisecond.
  // See the SIGNAL function further below for the code that is called during this interrupt.
  OCR0A = 0xAF;
  TIMSK0 |= _BV(OCIE0A);

  Serial.println("Ready!");
}

void loop() {
  // Parse GPS messages when they are received.
  if (GPS.newNMEAreceived()) {
    GPS.parse(GPS.lastNMEA());
  }
  
  // Light the LED solid if there's a GPS fix, otherwise flash it on and off once a second.
  if (GPS.fix) {
    digitalWrite(LED_PIN, HIGH);
  }
  else {
    // No fix, blink the LED once a second and stop further processing.
    digitalWrite(LED_PIN, (millis()/1000) % 2);
    return;
  }

  // Check if the button is pressed.
  if (digitalRead(BUTTON_PIN) == LOW) {
    // Pause a bit to debounce.
    delay(100);
    if (digitalRead(BUTTON_PIN) == LOW) {
      // Button pressed! Log the current location as having good candy.
      logLocation("Good Candy");
      // Then flash the light 5 times to signal the location was recorded.
      for (int i=0; i<5; ++i) {
        digitalWrite(LED_PIN, HIGH);
        delay(250);
        digitalWrite(LED_PIN, LOW);
        delay(250);
      }
    }
  }

  // Periodically log the location.
  if (logCounter == 0) {
    logLocation("Location");
    logCounter = LOGGING_PERIOD_SEC*1000;
  }
}
