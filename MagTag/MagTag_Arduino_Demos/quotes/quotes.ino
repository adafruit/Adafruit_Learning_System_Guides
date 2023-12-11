// SPDX-FileCopyrightText: 2017 Evandro Copercini
//
// SPDX-License-Identifier: Apache-2.0

/*
  Wifi secure connection example for ESP32
  Running on TLS 1.2 using mbedTLS
  2017 - Evandro Copercini - Apache 2.0 License.
*/

#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include "Adafruit_ThinkInk.h"
#include "Adafruit_NeoPixel.h"
#include <Fonts/FreeSans9pt7b.h>

const char* ssid     = "adafruit";     // your network SSID (name of wifi network)
const char* password = "ffffffff"; // your network password

const char*  server = "www.adafruit.com";
const char*  path   = "/api/quotes.php";

WiFiClientSecure client;
ThinkInk_290_Grayscale4_T5 display(EPD_DC, EPD_RESET, EPD_CS, -1, -1);
Adafruit_NeoPixel intneo = Adafruit_NeoPixel(4, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);


void deepSleep() {
  pinMode(NEOPIXEL_POWER, OUTPUT);
  pinMode(SPEAKER_SHUTDOWN, OUTPUT);
  digitalWrite(SPEAKER_SHUTDOWN, LOW); // off
  digitalWrite(NEOPIXEL_POWER, HIGH); // off
  digitalWrite(EPD_RESET, LOW); // off (yes required to save a few mA)
  pinMode(13, OUTPUT);
  digitalWrite(13, LOW);

  esp_sleep_enable_timer_wakeup(60 * 1000000); // 60 seconds
  esp_deep_sleep_start();  
}

void setup() {
  //Initialize serial and wait for port to open:
  Serial.begin(115200);
  //while (!Serial) delay(10);

  pinMode(BUTTON_A, INPUT_PULLUP);
  pinMode(BUTTON_B, INPUT_PULLUP);
  pinMode(BUTTON_C, INPUT_PULLUP);
  pinMode(BUTTON_D, INPUT_PULLUP);
  pinMode(EPD_BUSY, INPUT);
  pinMode(13, OUTPUT);
  digitalWrite(13, HIGH);

  
  display.begin(THINKINK_GRAYSCALE4);

  Serial.print("Attempting to connect to SSID: ");
  Serial.println(ssid);

  display.clearBuffer();
  display.setFont(&FreeSans9pt7b);
  display.setTextSize(1);
  display.setTextColor(EPD_BLACK);
  display.setCursor(10, 30);
  display.print("Connecting to SSID ");
  display.println(ssid);
  display.display();
  
  WiFi.begin(ssid, password);

  // attempt to connect to Wifi network:
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(100);
  }

  Serial.print("Connected to ");
  Serial.println(ssid);

  //client.setCACert(test_root_ca);
  //client.setCertificate(test_client_key); // for client verification
  //client.setPrivateKey(test_client_cert);	// for client verification

// Neopixel power
  pinMode(NEOPIXEL_POWER, OUTPUT);
  digitalWrite(NEOPIXEL_POWER, LOW); // on
  intneo.fill(25, 0, 0);
  intneo.show();
  
  Serial.println("\nStarting connection to server...");
  client.setInsecure();
  if (!client.connect(server, 443)) {
    Serial.println("Connection failed!");
    deepSleep();
  }

  intneo.fill(25, 25, 0);
  intneo.show();
  
  Serial.println("Connected to server!");
  // Make a HTTP request:
  client.print("GET "); client.print(path); client.println(" HTTP/1.1");
  client.print("Host: "); client.println(server);
  client.println("Connection: close");
  client.println();

  // Check HTTP status
  char status[32] = {0};
  client.readBytesUntil('\r', status, sizeof(status));
  if (strcmp(status, "HTTP/1.1 200 OK") != 0) {
    Serial.print(F("Unexpected response: "));
    Serial.println(status);
    deepSleep();
  }

  intneo.fill(0, 25, 0);
  intneo.show();
  while (client.connected()) {
    String line = client.readStringUntil('\n');
    if (line == "\r") {
      Serial.println("headers received");
      break;
    }
  }

  intneo.fill(0, 25, 25);
  intneo.show();
  while (client.peek() != '[') {
    client.read();
  }

  intneo.fill(0, 0, 25);
  intneo.show();
    
  // Allocate the JSON document
  // Use arduinojson.org/v6/assistant to compute the capacity.
  const size_t capacity = JSON_ARRAY_SIZE(1) + JSON_OBJECT_SIZE(8) + 200;
  DynamicJsonDocument doc(capacity);

  // Parse JSON object
  DeserializationError error = deserializeJson(doc, client);
  if (error) {
    Serial.print(F("deserializeJson() failed: "));
    Serial.println(error.c_str());
    deepSleep();
  }

  intneo.fill(0, 25, 25);
  intneo.show();
  
  // Extract values
  JsonObject root_0 = doc[0];
  Serial.println(F("Response:"));
  const char* root_0_text = root_0["text"];
  const char* root_0_author = root_0["author"];

  Serial.print("Quote: "); Serial.println(root_0_text);
  Serial.print("Author: "); Serial.println(root_0_author);

  display.clearBuffer();
  display.setFont(&FreeSans9pt7b);
  display.setTextSize(1);
  display.setTextWrap(true);
  display.setTextColor(EPD_BLACK);
  display.setCursor(10, 30);
  display.println(root_0_text);
  display.setTextColor(EPD_DARK);
  display.setCursor(40, 120);
  display.println(root_0_author);
  display.display();
  while (!digitalRead(EPD_BUSY)) {
    delay(10);
  }

  while (client.available() > 0)
  {
    //read back one line from the server
    String line = client.readStringUntil('\r');
    Serial.println(line);
  }
  
  // disconnect
  client.stop();
  deepSleep();
}

void loop() {

}
