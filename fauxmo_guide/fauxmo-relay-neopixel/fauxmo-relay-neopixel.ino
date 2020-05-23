#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include <ESP8266WiFi.h>
#include "fauxmoESP.h"

#define WIFI_SSID "wifi_ssid"
#define WIFI_PASS "wifi_pass"

#define SERIAL_BAUDRATE 115200

fauxmoESP fauxmo;

#define RELAY_PIN 13
#define NEOPIX_PIN 2
Adafruit_NeoPixel strip = Adafruit_NeoPixel(40, NEOPIX_PIN, NEO_GRB + NEO_KHZ800);
volatile boolean neopixel_state = false; // off by default!

uint32_t Wheel(byte WheelPos); // function prototype

// -----------------------------------------------------------------------------
// Wifi
// -----------------------------------------------------------------------------

void wifiSetup()
{
  // Set WIFI module to STA mode
  WiFi.mode(WIFI_STA);

  // Connect
  Serial.printf("[WIFI] Connecting to %s ", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  // Wait
  while (WiFi.status() != WL_CONNECTED)
  {
    Serial.print(".");
    delay(100);
  }
  Serial.println();

  // Connected!
  Serial.printf("[WIFI] STATION Mode, SSID: %s, IP address: %s\n", WiFi.SSID().c_str(), WiFi.localIP().toString().c_str());
}

void setup()
{
  strip.begin();
  strip.setBrightness(20);
  strip.show(); // Initialize all pixels to 'off'
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);

  // Init serial port and clean garbage
  Serial.begin(SERIAL_BAUDRATE);
  Serial.println();
  Serial.println();
  Serial.println("FauxMo demo sketch");
  Serial.println("After connection, ask Alexa/Echo to 'turn pixels on' or 'off' or 'turn relay on' or 'off'");

  // Wifi
  wifiSetup();
  // for gen3 devices or above
  fauxmo.setPort(80);
  fauxmo.enable(true);

  // Fauxmo
  fauxmo.addDevice("relay");
  fauxmo.addDevice("pixels");

  fauxmo.onSetState([](unsigned char device_id, const char *device_name, bool state, unsigned char value) {
    Serial.printf("[MAIN] %s state: %s\n", device_name, state ? "ON" : "OFF");

    if ((strcmp(device_name, "pixels") == 0))
    {
      // this just sets a variable that the main loop() does something about
      if (state)
      {
        neopixel_state = true;
      }
      else
      {
        neopixel_state = false;
      }
    }

    if ((strcmp(device_name, "relay") == 0))
    {
      // adjust the relay immediately!
      if (state)
      {
        digitalWrite(RELAY_PIN, HIGH);
      }
      else
      {
        digitalWrite(RELAY_PIN, LOW);
      }
    }
  });
}
uint8_t j = 0; // color swirl incrementer
void loop()
{
  fauxmo.handle();
  if (neopixel_state)
  {
    for (int16_t i = 0; i < strip.numPixels(); i++)
    {
      strip.setPixelColor(i, Wheel(((i * 256 / strip.numPixels()) + j) & 255));
    }
    strip.show();
    j++;
    delay(20);
  }
  else
  {
    for (int16_t i = 0; i < strip.numPixels(); i++)
    {
      strip.setPixelColor(i, 0);
    }
    strip.show();
  }
}

// Input a value 0 to 255 to get a color value.
// The colours are a transition r - g - b - back to r.
uint32_t Wheel(byte WheelPos)
{
  if (WheelPos < 85)
  {
    return strip.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
  }
  else if (WheelPos < 170)
  {
    WheelPos -= 85;
    return strip.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  }
  else
  {
    WheelPos -= 170;
    return strip.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
}