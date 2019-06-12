// Track Your Treats - FONA808 Shield & Adafruit IO Halloween Candy Route Tracker
// Author: Tony DiCola
//
// See the guide at:
// https://learn.adafruit.com/track-your-treats-halloween-candy-gps-tracker/overview
//
// Released under a MIT license:
// https://opensource.org/licenses/MIT
#include <SoftwareSerial.h>
#include "Adafruit_SleepyDog.h"
#include "Adafruit_FONA.h"
#include "Adafruit_MQTT.h"
#include "Adafruit_MQTT_FONA.h"


// Configuration (you need to change at least the APN and AIO username & key values):

#define LED_PIN              6   // Pin connected to an LED that flashes the status of the project.

#define BUTTON_PIN           5   // Pin connected to the button.

#define LOGGING_PERIOD_SEC   15  // Seconds to wait between logging GPS locations.

#define FONA_RX              2   // FONA serial RX pin (pin 2 for shield).

#define FONA_TX              3   // FONA serial TX pin (pin 3 for shield).

#define FONA_RST             4   // FONA reset pin (pin 4 for shield)

#define FONA_APN             ""  // APN used by cell data service (leave blank if unused).
                                 // Contact your cell service provider to get this value and
                                 // any username or password required too (see below).

#define FONA_USERNAME        ""  // Username used by cell data service (leave blank if unused).

#define FONA_PASSWORD        ""  // Password used by cell data service (leave blank if unused).

#define AIO_SERVER           "io.adafruit.com"  // Adafruit IO server name.

#define AIO_SERVERPORT       1883  // Adafruit IO port.

#define AIO_USERNAME         ""  // Adafruit IO username (see http://accounts.adafruit.com/).

#define AIO_KEY              ""  // Adafruit IO key (see settings page at: https://io.adafruit.com/settings).

#define PATH_FEED_NAME       "treat-path"  // Name of the AIO feed to log regular location updates.

#define GOOD_CANDY_FEED_NAME "treat-good-candy" // Name of the AIO feed to log good candy locations.

#define MAX_TX_FAILURES      3  // Maximum number of publish failures in a row before resetting the whole sketch.


// Global state (you don't need to change this):
SoftwareSerial fonaSS = SoftwareSerial(FONA_TX, FONA_RX);     // FONA software serial connection.
Adafruit_FONA fona = Adafruit_FONA(FONA_RST);                 // FONA library connection.
const char MQTT_SERVER[] PROGMEM    = AIO_SERVER;             // MQTT server, client, username, password.
const char MQTT_CLIENTID[] PROGMEM  = __TIME__ AIO_USERNAME;  // (stored in flash memory)
const char MQTT_USERNAME[] PROGMEM  = AIO_USERNAME;
const char MQTT_PASSWORD[] PROGMEM  = AIO_KEY;
Adafruit_MQTT_FONA mqtt(&fona, MQTT_SERVER, AIO_SERVERPORT,   // MQTT connection.
                        MQTT_CLIENTID, MQTT_USERNAME,
                        MQTT_PASSWORD);
uint8_t txFailures = 0;                                       // Count of how many publish failures have occured in a row.
uint32_t logCounter = 0;                                      // Counter until next location log is recorded.

// Publishing feed setup (you don't need to change this):
// Note that the path ends in '/csv', this means a comma separated set of values
// can be pushed to the feed, including location data like lat, long, altitude.
const char PATH_FEED[] PROGMEM = AIO_USERNAME "/feeds/" PATH_FEED_NAME "/csv";
Adafruit_MQTT_Publish path = Adafruit_MQTT_Publish(&mqtt, PATH_FEED);
const char GOOD_CANDY_FEED[] PROGMEM = AIO_USERNAME "/feeds/" GOOD_CANDY_FEED_NAME "/csv";
Adafruit_MQTT_Publish goodCandy = Adafruit_MQTT_Publish(&mqtt, GOOD_CANDY_FEED);


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

// Timer interrupt called every millisecond to keep track of when the location should be logged.
SIGNAL(TIMER0_COMPA_vect) {
  // Decrease the count since last location log.
  if (logCounter > 0) {
    logCounter--;
  }
}

// Serialize the lat, long, altitude to a CSV string that can be published to the specified feed.
void logLocation(float latitude, float longitude, float altitude, Adafruit_MQTT_Publish& publishFeed) {
  // Initialize a string buffer to hold the data that will be published.
  char sendBuffer[120];
  memset(sendBuffer, 0, sizeof(sendBuffer));
  int index = 0;

  // Start with '0,' to set the feed value.  The value isn't really used so 0 is used as a placeholder.
  sendBuffer[index++] = '0';
  sendBuffer[index++] = ',';

  // Now set latitude, longitude, altitude separated by commas.
  dtostrf(latitude, 2, 6, &sendBuffer[index]);
  index += strlen(&sendBuffer[index]);
  sendBuffer[index++] = ',';
  dtostrf(longitude, 3, 6, &sendBuffer[index]);
  index += strlen(&sendBuffer[index]);
  sendBuffer[index++] = ',';
  dtostrf(altitude, 2, 6, &sendBuffer[index]);

  // Finally publish the string to the feed.
  Serial.print(F("Publishing: "));
  Serial.println(sendBuffer);
  if (!publishFeed.publish(sendBuffer)) {
    Serial.println(F("Publish failed!"));
    txFailures++;
  }
  else {
    Serial.println(F("Publish succeeded!"));
    txFailures = 0;
  }
}

void setup() {
  // Initialize serial output.
  Serial.begin(115200);
  Serial.println(F("Track your Treats - FONA808 & Adafruit IO"));

  // Initialize LED and button.
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  digitalWrite(LED_PIN, LOW);

  // Initialize the FONA module
  Serial.println(F("Initializing FONA....(may take 10 seconds)"));
  fonaSS.begin(4800);
  if (!fona.begin(fonaSS)) {
    halt(F("Couldn't find FONA"));
  }
  fonaSS.println("AT+CMEE=2");
  Serial.println(F("FONA is OK"));

  // Use the watchdog to simplify retry logic and make things more robust.
  // Enable this after FONA is intialized because FONA init takes about 8-9 seconds.
  Watchdog.enable(8000);
  Watchdog.reset();

  // Wait for FONA to connect to cell network (up to 8 seconds, then watchdog reset).
  Serial.println(F("Checking for network..."));
  while (fona.getNetworkStatus() != 1) {
   delay(500);
  }

  // Enable GPS.
  fona.enableGPS(true);

  // Start the GPRS data connection.
  Watchdog.reset();
  fona.setGPRSNetworkSettings(F(FONA_APN), F(FONA_USERNAME), F(FONA_PASSWORD));
  delay(2000);
  Watchdog.reset();
  Serial.println(F("Disabling GPRS"));
  fona.enableGPRS(false);
  delay(2000);
  Watchdog.reset();
  Serial.println(F("Enabling GPRS"));
  if (!fona.enableGPRS(true)) {
    halt(F("Failed to turn GPRS on, resetting..."));
  }
  Serial.println(F("Connected to Cellular!"));

  // Wait a little bit to stabilize the connection.
  Watchdog.reset();
  delay(3000);

  // Now make the MQTT connection.
  int8_t ret = mqtt.connect();
  if (ret != 0) {
    Serial.println(mqtt.connectErrorString(ret));
    halt(F("MQTT connection failed, resetting..."));
  }
  Serial.println(F("MQTT Connected!"));

  // Configure timer0 compare interrupt to run and decrease the log counter every millisecond.
  OCR0A = 0xAF;
  TIMSK0 |= _BV(OCIE0A);
}

void loop() {
  // Watchdog reset at start of loop--make sure everything below takes less than 8 seconds in normal operation!
  Watchdog.reset();

  // Reset everything if disconnected or too many transmit failures occured in a row.
  if (!fona.TCPconnected() || (txFailures >= MAX_TX_FAILURES)) {
    halt(F("Connection lost, resetting..."));
  }

  // Grab a GPS reading.
  float latitude, longitude, speed_kph, heading, altitude;
  bool gpsFix = fona.getGPS(&latitude, &longitude, &speed_kph, &heading, &altitude);

  // Light the LED solid if there's a GPS fix, otherwise flash it on and off once a second.
  if (gpsFix) {
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
      // Button pressed! Log the current location to the good candy feed.
      logLocation(latitude, longitude, altitude, goodCandy);
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
    // Log the current location to the path feed, then reset the counter.
    logLocation(latitude, longitude, altitude, path);
    logCounter = LOGGING_PERIOD_SEC*1000;
  }
}
