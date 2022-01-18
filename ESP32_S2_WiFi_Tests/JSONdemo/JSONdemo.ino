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

#if defined(USE_OLED)
  #include <Adafruit_SSD1306.h>
  Adafruit_SSD1306 display = Adafruit_SSD1306(128, 32, &Wire);
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

// Initialize the SSL client library
// with the IP address and port of the server
// that you want to connect to (port 443 is default for HTTPS):
WiFiClientSecure client;

void setup() {
  //Initialize serial and wait for port to open:
  Serial.begin(115200);

  #if defined(USE_OLED)
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
        delay(10); // wait for serial port to connect. Needed for native USB port only
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

  // Connect to WPA/WPA2 network. Change this line if using open or WEP network:
  WiFi.begin(ssid, pass);
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

  delay(10000);
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