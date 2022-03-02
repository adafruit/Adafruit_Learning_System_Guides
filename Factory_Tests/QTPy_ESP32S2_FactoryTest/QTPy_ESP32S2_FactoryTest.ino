#include "WiFi.h"
#include <Adafruit_TestBed.h>
extern Adafruit_TestBed TB;

// the setup routine runs once when you press reset:
void setup() {
  Serial.begin(115200);

  // Set up QT port
  Wire1.setPins(SDA1, SCL1);

  // TestBed will handle the neopixel swirl for us
  TB.neopixelPin = PIN_NEOPIXEL;
  TB.neopixelNum = 1;
  TB.begin();

  // Set WiFi to station mode and disconnect from an AP if it was previously connected
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
}

// the loop routine runs over and over again forever:
uint8_t wheelColor=0;
void loop() {
  if (wheelColor == 0) {
    // Test I2C!
    Serial.print("Default (pads) port ");
    TB.theWire = &Wire;
    TB.printI2CBusScan();
    Serial.print("Secondary (QT) port ");
    TB.theWire = &Wire1;
    TB.printI2CBusScan();

    // Test WiFi Scan!
    // WiFi.scanNetworks will return the number of networks found
    int n = WiFi.scanNetworks();
    Serial.print("WiFi AP scan done...");
    if (n == 0) {
        Serial.println("no networks found");
    } else {
        Serial.print(n);
        Serial.println(" networks found");
        for (int i = 0; i < n; ++i) {
            // Print SSID and RSSI for each network found
            Serial.print(i + 1);
            Serial.print(": ");
            Serial.print(WiFi.SSID(i));
            Serial.print(" (");
            Serial.print(WiFi.RSSI(i));
            Serial.print(")");
            Serial.println((WiFi.encryptionType(i) == WIFI_AUTH_OPEN)?" ":"*");
            delay(10);
        }
    }
    Serial.println("");
  }

  TB.setColor(TB.Wheel(wheelColor++)); // swirl NeoPixel

  delay(5);
}
