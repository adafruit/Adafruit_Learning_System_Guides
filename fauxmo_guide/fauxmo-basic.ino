#include <Arduino.h>
#include <ESP8266WiFi.h>
#include "fauxmoESP.h"

#define WIFI_SSID "YOUR_SSID"
#define WIFI_PASS "YOUR_WIFI_PASSWORD"
#define SERIAL_BAUDRATE 115200

fauxmoESP fauxmo;

// -----------------------------------------------------------------------------
// Wifi
// -----------------------------------------------------------------------------

void wifiSetup() {

    // Set WIFI module to STA mode
    WiFi.mode(WIFI_STA);

    // Connect
    Serial.printf("[WIFI] Connecting to %s ", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASS);

    // Wait
    while (WiFi.status() != WL_CONNECTED) {
        Serial.print(".");
        delay(100);
    }
    Serial.println();

    // Connected!
    Serial.printf("[WIFI] STATION Mode, SSID: %s, IP address: %s\n", WiFi.SSID().c_str(), WiFi.localIP().toString().c_str());
}

void setup() {
  // Init serial port and clean garbage
  Serial.begin(SERIAL_BAUDRATE);
  Serial.println("FauxMo demo sketch");
  Serial.println("After connection, ask Alexa/Echo to 'turn <devicename> on' or 'off'");

  // Wifi
  wifiSetup();

  // Fauxmo
  fauxmo.addDevice("relay");
  fauxmo.addDevice("pixels");
  // Gen3 Devices or above
  fauxmo.setPort(80);

  // Allow the FauxMo to be discovered
  fauxmo.enable(true);
  
  fauxmo.onSetState([](unsigned char device_id, const char * device_name, bool state, unsigned char value) {
    Serial.print("Device: ");Serial.print(device_name);
    Serial.print(" state");
    if(state) {
      Serial.println("ON!");
    }
    else {
      Serial.println("off");
    }

  });

}

void loop() {
  fauxmo.handle();
}