/***************************************************
  Adafruit MQTT Library ESP8266 Example
  Must use ESP8266 Arduino from:
    https://github.com/esp8266/Arduino
  Written by Tony DiCola for Adafruit Industries.
  MIT license, all text above must be included in any redistribution
 ****************************************************/

#include <ESP8266WiFi.h>
#include "Adafruit_MQTT.h"
#include "Adafruit_MQTT_Client.h"

#define RED    13
#define YELLOW 5
#define GREEN  4

// Prototypes for functions
void MQTT_connect();

/************************* WiFi Access Point *********************************/

#define WLAN_SSID       "YOURWIFI"
#define WLAN_PASS       "YOURWIFIPASS"

/************************* Adafruit.io Setup *********************************/

#define AIO_SERVER      "io.adafruit.com"
#define AIO_SERVERPORT  1883
#define AIO_USERNAME    "YOURUSERNAME"
#define AIO_KEY         "YOURAPIKEY"

/************ Global State (you don't need to change this!) ******************/

// Create an ESP8266 WiFiClient class to connect to the MQTT server.
WiFiClient client;

// Store the MQTT server, username, and password in flash memory.
// This is required for using the Adafruit MQTT library.
const char MQTT_SERVER[] PROGMEM    = AIO_SERVER;
const char MQTT_USERNAME[] PROGMEM  = AIO_USERNAME;
const char MQTT_PASSWORD[] PROGMEM  = AIO_KEY;

// Setup the MQTT client class by passing in the WiFi client and MQTT server and login details.
Adafruit_MQTT_Client mqtt(&client, MQTT_SERVER, AIO_SERVERPORT, MQTT_USERNAME, MQTT_PASSWORD);

/****************************** Feeds ***************************************/

// Setup a feed called 'onoff' for subscribing to changes.
const char RED_FEED[] PROGMEM = AIO_USERNAME "/feeds/redlight";
Adafruit_MQTT_Subscribe redlight = Adafruit_MQTT_Subscribe(&mqtt, RED_FEED);

const char YELLOW_FEED[] PROGMEM = AIO_USERNAME "/feeds/yellowlight";
Adafruit_MQTT_Subscribe yellowlight = Adafruit_MQTT_Subscribe(&mqtt, YELLOW_FEED);

const char GREEN_FEED[] PROGMEM = AIO_USERNAME "/feeds/greenlight";
Adafruit_MQTT_Subscribe greenlight = Adafruit_MQTT_Subscribe(&mqtt, GREEN_FEED);

/*************************** Sketch Code ************************************/

void setup() {
  Serial.begin(115200);
  delay(10);

  Serial.println(F("Adafruit MQTT LED tower"));

  // Connect to WiFi access point.
  Serial.println(); Serial.println();
  Serial.print("Connecting to ");
  Serial.println(WLAN_SSID);

  WiFi.begin(WLAN_SSID, WLAN_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  Serial.println("WiFi connected");
  Serial.println("IP address: "); Serial.println(WiFi.localIP());

  // Setup MQTT subscription for onoff feed.
  mqtt.subscribe(&redlight);
  mqtt.subscribe(&yellowlight);
  mqtt.subscribe(&greenlight);

  pinMode(RED, OUTPUT);
  pinMode(YELLOW, OUTPUT);
  pinMode(GREEN, OUTPUT);
}

uint32_t x=0;

void loop() {
  // Ensure the connection to the MQTT server is alive (this will make the first
  // connection and automatically reconnect when disconnected).  See the MQTT_connect
  // function definition further below.
  MQTT_connect();

  // this is our 'wait for incoming subscription packets' busy subloop
  Adafruit_MQTT_Subscribe *subscription;
  while ((subscription = mqtt.readSubscription(10000))) {
    if (subscription == &redlight) {
      Serial.print(F("RED Got: "));
      Serial.println((char *)redlight.lastread);
      
      if (0 == strcmp((char *)redlight.lastread, "OFF")) {
        digitalWrite(RED, LOW);
      }
      if (0 == strcmp((char *)redlight.lastread, "ON")) {
        digitalWrite(RED, HIGH);
      }
    }

    if (subscription == &yellowlight) {
      Serial.print(F("YELLOW Got: "));
      Serial.println((char *)yellowlight.lastread);
      
      if (0 == strcmp((char *)yellowlight.lastread, "OFF")) {
        digitalWrite(YELLOW, LOW);
      }
      if (0 == strcmp((char *)yellowlight.lastread, "ON")) {
        digitalWrite(YELLOW, HIGH);
      }
    }

    if (subscription == &greenlight) {
      Serial.print(F("GREEN Got: "));
      Serial.println((char *)greenlight.lastread);
      
      if (0 == strcmp((char *)greenlight.lastread, "OFF")) {
        digitalWrite(GREEN, LOW);
      }
      if (0 == strcmp((char *)greenlight.lastread, "ON")) {
        digitalWrite(GREEN, HIGH);
      }
    }
  }


  // ping the server to keep the mqtt connection alive
  if(! mqtt.ping()) {
    mqtt.disconnect();
  }
}

// Function to connect and reconnect as necessary to the MQTT server.
// Should be called in the loop function and it will take care if connecting.
void MQTT_connect() {
  int8_t ret;

  // Stop if already connected.
  if (mqtt.connected()) {
    return;
  }

  Serial.print("Connecting to MQTT... ");

  while ((ret = mqtt.connect()) != 0) { // connect will return 0 for connected
       Serial.println(mqtt.connectErrorString(ret));
       Serial.println("Retrying MQTT connection in 5 seconds...");
       mqtt.disconnect();
       delay(5000);  // wait 5 seconds
  }
  Serial.println("MQTT Connected!");
}
