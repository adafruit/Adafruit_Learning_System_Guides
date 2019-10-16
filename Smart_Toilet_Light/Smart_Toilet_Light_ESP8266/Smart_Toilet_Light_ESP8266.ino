// Smart Toilet Light with ESP8266
//
// Use a feed in Adafruit IO to control the color and animation of a neopixel
// Attaching the neopixel to the bowl of a toilet so it shines down into it will
// create an interesting nightlight that can display information (like from IFTTT
// triggers).
//
// Author: Tony DiCola
// License: MIT (https://opensource.org/licenses/MIT)
#include <ESP8266WiFi.h>
#include "Adafruit_MQTT.h"
#include "Adafruit_MQTT_Client.h"
#include "Adafruit_NeoPixel.h"


// Configuration that you _must_ fill in:
#define WLAN_SSID       "... WiFi SSID ..."    // Your WiFi AP name.
#define WLAN_PASS       "... Password ..."     // Your WiFi AP password.
#define AIO_USERNAME    "... AIO username ..." // Adafruit IO username (see http://accounts.adafruit.com).
#define AIO_KEY         "... AIO key ..."      // Adafruit IO key

// Configuration you can optionally change (but probably want to keep the same):
#define PIXEL_PIN       2                      // Pin connected to the NeoPixel data input.
#define PIXEL_COUNT     1                      // Number of NeoPixels.
#define PIXEL_TYPE      NEO_RGB + NEO_KHZ800   // Type of the NeoPixels (see strandtest example).
#define LIGHT_FEED      "toilet-light"         // Name of the feed in Adafruit IO to listen for colors.
#define AIO_SERVER      "io.adafruit.com"      // Adafruit IO server address.
#define AIO_SERVERPORT  1883                   // AIO server port.
#define PING_SEC        60                     // How many seconds to wait between MQTT pings.
                                               // Used to help keep the connection alive during
                                               // long periods of inactivity.


// Global state (you don't need to change this):
// Put strings in flash memory (required for MQTT library).
const char MQTT_SERVER[] PROGMEM    = AIO_SERVER;
const char MQTT_USERNAME[] PROGMEM  = AIO_USERNAME;
const char MQTT_PASSWORD[] PROGMEM  = AIO_KEY;
const char MQTT_PATH[] PROGMEM      = AIO_USERNAME "/feeds/" LIGHT_FEED;
// Create ESP8266 wifi client, MQTT client, and feed subscription.
WiFiClient client;
Adafruit_MQTT_Client mqtt(&client, MQTT_SERVER, AIO_SERVERPORT, MQTT_USERNAME, MQTT_PASSWORD);
Adafruit_MQTT_Subscribe lightFeed = Adafruit_MQTT_Subscribe(&mqtt, MQTT_PATH);
// Create NeoPixel.
Adafruit_NeoPixel pixels = Adafruit_NeoPixel(PIXEL_COUNT, PIXEL_PIN, PIXEL_TYPE);
// Other global state:
uint32_t nextPing = 0;       // Next time a MQTT ping should be sent.
int red = 0;                 // RGB color for the current animation.
int green = 0;
int blue = 0;
int animation = 0;           // Current animation (0 = none, 1 = pulse, 2 = rainbow cycle).
int pulsePeriodMS = 0;       // Period of time (in MS) for the pulse animation.


// Explicit declaration of MQTT_connect function defined further below.
// Necessary because of bug/issue with recent Arduino builder & ESP8266.
void MQTT_connect();

// Function to set all the NeoPixels to the specified color.
void lightPixels(uint32_t color) {
  for (int i=0; i<PIXEL_COUNT; ++i) {
    pixels.setPixelColor(i, color);
  }
  pixels.show();
}

// Function to parse a hex byte value from a string.
// The passed in string MUST be at least 2 characters long!
// If the value can't be parsed then -1 is returned, otherwise the
// byte value is returned.
int parseHexByte(char* data) {
  char high = tolower(data[0]);
  char low = tolower(data[1]);
  uint8_t result = 0;
  // Parse the high nibble.
  if ((high >= '0') && (high <= '9')) {
    result += 16*(high-'0');
  }
  else if ((high >= 'a') && (high <= 'f')) {
    result += 16*(10+(high-'a'));
  }
  else {
    // Couldn't parse the high nibble.
    return -1;
  }
  // Parse the low nibble.
  if ((low >= '0') && (low <= '9')) {
    result += low-'0';
  }
  else if ((low >= 'a') && (low <= 'f')) {
    result += 10+(low-'a');
  }
  else {
    // Couldn't parse the low nibble.
    return -1;
  }
  return result;
}

// Linear interpolation of value y within range y0...y1 given a value x
// and the range x0...x1.
float lerp(float x, float y0, float y1, float x0, float x1) {
  return y0 + (y1-y0)*((x-x0)/(x1-x0));
}

// Pulse the pixels from their color down to black (off) and back
// up every pulse period milliseconds.
void pulseAnimation() {
  // Calculate how far we are into the current pulse period.
  int n = millis() % pulsePeriodMS;
  // Pulse up or down depending on how far along into the period.
  if (n < (pulsePeriodMS/2)) {
    // In the first half so pulse up.
    // Interpolate between black/off and full color using n.
    uint8_t cr = (uint8_t)lerp(n, 0, red,   0, pulsePeriodMS/2-1);
    uint8_t cg = (uint8_t)lerp(n, 0, green, 0, pulsePeriodMS/2-1);
    uint8_t cb = (uint8_t)lerp(n, 0, blue,  0, pulsePeriodMS/2-1);
    // Light the pixels.
    lightPixels(pixels.Color(cr, cg, cb));
  }
  else {
    // In the second half so pulse down.
    // Interpolate between full color and black/off color using n.
    uint8_t cr = (uint8_t)lerp(n, red,   0, pulsePeriodMS/2, pulsePeriodMS-1);
    uint8_t cg = (uint8_t)lerp(n, green, 0, pulsePeriodMS/2, pulsePeriodMS-1);
    uint8_t cb = (uint8_t)lerp(n, blue,  0, pulsePeriodMS/2, pulsePeriodMS-1);
    // Light the pixels.
    lightPixels(pixels.Color(cr, cg, cb));
  }
  
}

// Input a value 0 to 255 to get a color value.
// The colours are a transition r - g - b - back to r.
uint32_t Wheel(byte WheelPos) {
  WheelPos = 255 - WheelPos;
  if(WheelPos < 85) {
    return pixels.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  }
  if(WheelPos < 170) {
    WheelPos -= 85;
    return pixels.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
  WheelPos -= 170;
  return pixels.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
}

void rainbowAnimation() {
  // Assume the rainbow cycles every 2.56 seconds so there's a
  // 10 millisecond delay every color change.
  int n = (millis()/10) % 256;
  lightPixels(Wheel(n));
}

void setup() {
  // Initialize serial output.
  Serial.begin(115200);
  delay(10);
  Serial.println("Smart Toilet Light with ESP8266");

  // Initialize NeoPixels and turn them off.
  pixels.begin();
  lightPixels(pixels.Color(0, 0, 0));

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

  // Setup MQTT subscription.
  mqtt.subscribe(&lightFeed);
}

void loop() {
  // Do any NeoPixel animation logic.
  if (animation == 1) {
    pulseAnimation();
  }
  else if (animation == 2) {
    rainbowAnimation();
  }
  
  // Ensure the connection to the MQTT server is alive (this will make the first
  // connection and automatically reconnect when disconnected).  See the MQTT_connect
  // function definition further below.
  MQTT_connect();

  // Check if any new data has been received from the light feed.
  Adafruit_MQTT_Subscribe *subscription;
  while ((subscription = mqtt.readSubscription(10))) {
    if (subscription == &lightFeed) {
      // Received data from the light feed!
      // Parse the data to see how to change the light.
      char* data = (char*)lightFeed.lastread;
      int dataLen = strlen(data);
      Serial.print("Got: ");
      Serial.println(data);
      if (dataLen < 1) {
        // Stop processing if not enough data was received.
        continue;
      }
      // Check the first character to determine the light change command.
      switch (data[0]) {
        case 'S':
          // Solid color.
          // Expect 6 more characters with the hex red, green, blue color.
          if (dataLen >= 7) {
            // Parse out the RGB color bytes.
            int r = parseHexByte(&data[1]);
            int g = parseHexByte(&data[3]);
            int b = parseHexByte(&data[5]);
            if ((r < 0) || (g < 0) || (b < 0)) {
              // Couldn't parse the color, stop processing.
              break; 
            }
            // Light the pixels!
            lightPixels(pixels.Color(r, g, b));
            // Change the animation to none/stop animating.
            animation = 0;
          }
          break;
        case 'P':
          // Pulse animation.
          // Expect 8 more characters with the hex red, green, blue color, and
          // a byte value with the frequency to pulse within a 10 second period.
          // I.e. to make it the light pulse once every 2 seconds send the value
          // 5 so that the light pulses 5 times within a ten second period (every
          // 2 seconds).
          if (dataLen >= 9) {
            // Parse out the RGB color and frequency bytes.
            int r = parseHexByte(&data[1]);
            int g = parseHexByte(&data[3]);
            int b = parseHexByte(&data[5]);
            int f = parseHexByte(&data[7]);
            if ((r < 0) || (g < 0) || (b < 0) || (f < 0)) {
              // Couldn't parse the data, stop processing.
              break; 
            }
            // Change the color for the pulse animation.
            red   = r;
            green = g;
            blue  = b;
            // Calculate the pulse length in milliseconds from the specified frequency.
            pulsePeriodMS = (10.0 / (float)f) * 1000.0;
            // Change the animation to pulse.
            animation = 1;
          }
          break;
        case 'R':
          // Rainbow cycle animation.
          animation = 2;
          break;
      }
    }
  }

  // Ping the MQTT server periodically to prevent the connection from being closed.
  if (millis() >= nextPing) {
    // Attempt to send a ping.
    if(! mqtt.ping()) {
      // Disconnect if the ping failed.  Next loop iteration a reconnect will be attempted.
      mqtt.disconnect();
    }
    // Set the time for the next ping.
    nextPing = millis() + PING_SEC*1000L;
  }
}

// Function to connect and reconnect as necessary to the MQTT server.
// Should be called in the loop function and it will take care of connecting.
void MQTT_connect() {
  int8_t ret;

  // Stop if already connected.
  if (mqtt.connected()) {
    return;
  }

  Serial.print("Connecting to MQTT... ");

  uint8_t retries = 3;
  while ((ret = mqtt.connect()) != 0) { // connect will return 0 for connected
       Serial.println(mqtt.connectErrorString(ret));
       Serial.println("Retrying MQTT connection in 5 seconds...");
       mqtt.disconnect();
       delay(5000);  // wait 5 seconds
       retries--;
       if (retries == 0) {
         // basically die and wait for WDT to reset me
         while (1);
       }
  }
  Serial.println("MQTT Connected!");
}
