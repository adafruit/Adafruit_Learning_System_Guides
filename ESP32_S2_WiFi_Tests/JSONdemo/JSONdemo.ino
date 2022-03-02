// SPDX-FileCopyrightText: 2014 Benoit Blanchon
// SPDX-FileCopyrightText: 2014 Arturo Guadalupi
// SPDX-FileCopyrightText: 2020 Brent Rubell for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*
This example creates a client object that connects and transfers
data using always SSL, then shows how to parse a JSON document in an HTTP response.

It is compatible with the methods normally related to plain
connections, like client.connect(host, port).

Written by Arturo Guadalupi + Copyright Benoit Blanchon 2014-2019
last revision November 2015

*/

#include <WiFiClientSecure.h>
#include <ArduinoJson.h>

// uncomment the next line if you have a 128x32 OLED on the I2C pins
//#define USE_OLED
// uncomment the next line to deep sleep between requests
//#define USE_DEEPSLEEP

#if defined(USE_OLED)
// Some boards have TWO I2C ports, how nifty. We should use the second one sometimes
#if defined(ARDUINO_ADAFRUIT_QTPY_ESP32S2) \
    || defined(ARDUINO_ADAFRUIT_QTPY_ESP32_PICO)
  #define OLED_I2C_PORT &Wire1
#else
  #define OLED_I2C_PORT &Wire
#endif

  #include <Adafruit_SSD1306.h>
  Adafruit_SSD1306 display = Adafruit_SSD1306(128, 32, OLED_I2C_PORT);
#endif

// Enter your WiFi SSID and password
char ssid[] = "YOUR_SSID";             // your network SSID (name)
char pass[] = "YOUR_SSID_PASSWORD";    // your network password (use for WPA, or use as key for WEP)
int keyIndex = 0;                      // your network key Index number (needed only for WEP)


int status = WL_IDLE_STATUS;
// if you don't want to use DNS (and reduce your sketch size)
// use the numeric IP instead of the name for the server:
//IPAddress server(74,125,232,128);  // numeric IP for Google (no DNS)

#define SERVER "cdn.syndication.twimg.com"
#define PATH   "/widgets/followbutton/info.json?screen_names=adafruit"


void setup() {
  //Initialize serial and wait for port to open:
  Serial.begin(115200);

  // Connect to WPA/WPA2 network
  WiFi.begin(ssid, pass);

  #if defined(USE_OLED)
    setupI2C();
    delay(200); // wait for OLED to reset
  
    if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) { // Address 0x3C for 128x32
        Serial.println(F("SSD1306 allocation failed"));
        for(;;); // Don't proceed, loop forever
    }
    display.display();
    display.setTextSize(1);
    display.setTextColor(WHITE);
    display.clearDisplay();
    display.setCursor(0,0);
  #else
    // Don't wait for serial if we have an OLED  
    while (!Serial) {
      // wait for serial port to connect. Needed for native USB port only
      delay(10); 
    }
  #endif
  // attempt to connect to Wifi network:
  Serial.print("Attempting to connect to SSID: ");
  Serial.println(ssid);
  #if defined(USE_OLED)
    display.clearDisplay(); display.setCursor(0,0);
    display.print("Connecting to SSID\n"); display.println(ssid);
    display.display();
  #endif


  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("Connected to WiFi");
  
  #if defined(USE_OLED)
    display.print("...OK!");
    display.display();
  #endif

  printWifiStatus();
}

uint32_t bytes = 0;

void loop() {
  WiFiClientSecure client;
  client.setInsecure(); // don't use a root cert

  Serial.println("\nStarting connection to server...");
  #if defined(USE_OLED)
    display.clearDisplay(); display.setCursor(0,0);
    display.print("Connecting to "); display.print(SERVER);
    display.display();
  #endif

  // if you get a connection, report back via serial:
  if (client.connect(SERVER, 443)) {
    Serial.println("connected to server");
    // Make a HTTP request:
    client.println("GET " PATH " HTTP/1.1");
    client.println("Host: " SERVER);
    client.println("Connection: close");
    client.println();
  }

  // Check HTTP status
  char status[32] = {0};
  client.readBytesUntil('\r', status, sizeof(status));
  if (strcmp(status, "HTTP/1.1 200 OK") != 0) {
    Serial.print(F("Unexpected response: "));
    Serial.println(status);
  #if defined(USE_OLED)
      display.print("Connection failed, code: "); display.println(status);
      display.display();
  #endif

  return;
  }

  // wait until we get a double blank line
  client.find("\r\n\r\n", 4);

  // Allocate the JSON document
  // Use arduinojson.org/v6/assistant to compute the capacity.
  const size_t capacity = JSON_ARRAY_SIZE(1) + JSON_OBJECT_SIZE(8) + 200;
  DynamicJsonDocument doc(capacity);

  // Parse JSON object
  DeserializationError error = deserializeJson(doc, client);
  if (error) {
    Serial.print(F("deserializeJson() failed: "));
    Serial.println(error.c_str());
    return;
  }

  // Extract values
  JsonObject root_0 = doc[0];
  Serial.println(F("Response:"));
  const char* root_0_screen_name = root_0["screen_name"];
  long root_0_followers_count = root_0["followers_count"];

  Serial.print("Twitter username: "); Serial.println(root_0_screen_name);
  Serial.print("Twitter followers: "); Serial.println(root_0_followers_count);
  #if defined(USE_OLED)
    display.clearDisplay(); display.setCursor(0,0);
    display.setTextSize(2);
    display.println(root_0_screen_name);
    display.println(root_0_followers_count);
    display.display();
    display.setTextSize(1);
  #endif

  // Disconnect
  client.stop();
  delay(1000);

#if defined(USE_DEEPSLEEP)
#if defined(USE_OLED)
  display.clearDisplay();
  display.display();
#endif // OLED
#if defined(NEOPIXEL_POWER)
  digitalWrite(NEOPIXEL_POWER, LOW); // off
#elif defined(NEOPIXEL_I2C_POWER)
  digitalWrite(NEOPIXEL_I2C_POWER, LOW); // off
#endif
  // wake up 1 second later and then go into deep sleep
  esp_sleep_enable_timer_wakeup(10 * 1000UL * 1000UL); // 10 sec
  esp_deep_sleep_start(); 
#else
  delay(10 * 1000);
#endif
}

void setupI2C() {
  #if defined(ARDUINO_ADAFRUIT_QTPY_ESP32S2) || defined(ARDUINO_ADAFRUIT_QTPY_ESP32_PICO)
  // ESP32 is kinda odd in that secondary ports must be manually
  // assigned their pins with setPins()!
  Wire1.setPins(SDA1, SCL1);
  #endif
  
  #if defined(NEOPIXEL_I2C_POWER)
  pinMode(NEOPIXEL_I2C_POWER, OUTPUT);
  digitalWrite(NEOPIXEL_I2C_POWER, HIGH); // on
  #endif
  
  #if defined(ARDUINO_ADAFRUIT_FEATHER_ESP32S2)
  // turn on the I2C power by setting pin to opposite of 'rest state'
  pinMode(PIN_I2C_POWER, INPUT);
  delay(1);
  bool polarity = digitalRead(PIN_I2C_POWER);
  pinMode(PIN_I2C_POWER, OUTPUT);
  digitalWrite(PIN_I2C_POWER, !polarity);
  #endif
}

void printWifiStatus() {
  // print the SSID of the network you're attached to:
  Serial.print("SSID: ");
  Serial.println(WiFi.SSID());

  // print your board's IP address:
  IPAddress ip = WiFi.localIP();
  Serial.print("IP Address: ");
  Serial.println(ip);

  // print the received signal strength:
  long rssi = WiFi.RSSI();
  Serial.print("signal strength (RSSI):");
  Serial.print(rssi);
  Serial.println(" dBm");
}
