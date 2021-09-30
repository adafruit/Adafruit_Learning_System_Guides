# SPDX-FileCopyrightText: 2018 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

#include <SPI.h>
#include <WiFi101.h>
#include <Adafruit_NeoPixel.h>

#define PIN 12
Adafruit_NeoPixel strip = Adafruit_NeoPixel(30, PIN, NEO_GRBW + NEO_KHZ800);


// Define the WINC1500 board connections below.
// If you're following the Adafruit WINC1500 board
// guide you don't need to modify these:
#define WINC_CS   8
#define WINC_IRQ  7
#define WINC_RST  4
#define WINC_EN   2     // or, tie EN to VCC and comment this out

#define LED 13

char ssid[] = "ssid"; //  your network SSID (name)
char pass[] = "password";    // your network password (use for WPA, or use as key for WEP)
int keyIndex = 0;            // your network key Index number (needed only for WEP)

int status = WL_IDLE_STATUS;
#define HOST "api.twitch.tv"
#define PATH "/kraken/streams/adafruit"
#define REFRESH 20  // seconds between refresh

WiFiSSLClient client;

// Fill the dots one after the other with a color
void colorWipe(uint32_t c, uint8_t wait) {
  for(uint16_t i=0; i<strip.numPixels(); i++) {
    strip.setPixelColor(i, c);
    strip.show();
    delay(wait);
  }
}

void setup() {
#ifdef WINC_EN
  pinMode(WINC_EN, OUTPUT);
  digitalWrite(WINC_EN, HIGH);
#endif
  WiFi.setPins(WINC_CS, WINC_IRQ, WINC_RST);

  pinMode(LED, OUTPUT);
  
  //Initialize serial and wait for port to open:
  Serial.begin(9600);

  strip.begin();

  // check for the presence of the shield:
  if (WiFi.status() == WL_NO_SHIELD) {
    Serial.println("WiFi shield not present");
    // don't continue:
    while (true);
  }
}

void loop() {
  // attempt to connect to Wifi network:
  if (WiFi.status() != WL_CONNECTED) {
    while (WiFi.status() != WL_CONNECTED) {
      Serial.print("Attempting to connect to SSID: ");
      Serial.println(ssid);
      // Connect to WPA/WPA2 network. Change this line if using open or WEP network:
      status = WiFi.begin(ssid, pass);
  
      // wait 10 seconds for connection:
      uint8_t timeout = 10;
      while (timeout && (WiFi.status() != WL_CONNECTED)) {
        timeout--;
        delay(1000);
      }
    }
  
    Serial.println("Connected to wifi");
    printWifiStatus();
  }
  
  Serial.println("\nStarting connection to twitch...");
  // if you get a connection, report back via serial:
  if (client.connect(HOST, 443)) {
    Serial.println("connected to twitch api server");
    // Make a HTTP request:
    client.println("GET " PATH " HTTP/1.1");
    client.println("Host: " HOST);
    client.println("Connection: close");
    client.println();
  }

  boolean isStreaming = false;
  while (client.connected()) {
    if (client.find("\"stream\":{\"_id\":")) {
      isStreaming = true;
    }
  }

  Serial.print("Streaming status: "); Serial.println(isStreaming);
  digitalWrite(LED, isStreaming);
  if (isStreaming) {
    colorWipe(strip.Color(255, 0, 0), 50); // Red
  } else {
    colorWipe(strip.Color(10, 10, 10), 50); // Off
  }
  Serial.println("disconnecting from server.");
  client.stop();

  delay(REFRESH*1000);
}


void printWifiStatus() {
  // print the SSID of the network you're attached to:
  Serial.print("SSID: ");
  Serial.println(WiFi.SSID());

  // print your WiFi shield's IP address:
  IPAddress ip = WiFi.localIP();
  Serial.print("IP Address: ");
  Serial.println(ip);

  // print the received signal strength:
  long rssi = WiFi.RSSI();
  Serial.print("signal strength (RSSI):");
  Serial.print(rssi);
  Serial.println(" dBm");
}
