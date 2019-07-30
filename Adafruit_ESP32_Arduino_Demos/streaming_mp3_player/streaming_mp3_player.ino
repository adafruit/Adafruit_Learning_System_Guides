// Stream MP3s over WiFi on Metro M4 Express and play via music maker shield

#include <SPI.h>
#include <Adafruit_VS1053.h>
#include <WiFiNINA.h>
#include <CircularBuffer.h>
#include "arduino_secrets.h" 

///////please enter your sensitive data in the Secret tab/arduino_secrets.h
char ssid[] = SECRET_SSID;        // your network SSID (name)
char pass[] = SECRET_PASS;    // your network password (use for WPA, or use as key for WEP)

//#define DEBUG 

// SOMA FM Radio 80's http://ice1.somafm.com/u80s-128-mp3
//const char *host = "ice1.somafm.com";
//const char *path = "/u80s-128-mp3";
//const char *path = "/doomed-128-mp3";
//int httpPort = 80;

// WMBR radio http://wmbr.org:8000/med
const char *host = "wmbr.org";
const char *path = "/med";
int httpPort = 8000;

// These are the pins used
#if defined(ADAFRUIT_FEATHER_M4_EXPRESS) || defined(ADAFRUIT_FEATHER_M0_EXPRESS) || defined(ARDUINO_AVR_FEATHER32U4) || defined(ARDUINO_NRF52840_FEATHER) 
  #define VS1053_RESET   -1     // VS1053 reset pin (not used!)
  #define VS1053_CS       6     // VS1053 chip select pin (output)
  #define VS1053_DCS     10     // VS1053 Data/command select pin (output)
  #define VS1053_DREQ     9     // VS1053 Data request, ideally an Interrupt pin
  #define ESP_CS         13
  #define ESP_RESET      12
  #define ESP_READY      11
  #define ESP_GPIO0      -1
#elif defined(ARDUINO_AVR_FEATHER328P) 
  #define VS1053_RESET   -1     // VS1053 reset pin (not used!)
  #define VS1053_CS       6     // VS1053 chip select pin (output)
  #define VS1053_DCS     10     // VS1053 Data/command select pin (output)
  #define VS1053_DREQ     9     // VS1053 Data request, ideally an Interrupt pin
  #define ESP_CS          4
  #define ESP_RESET       3
  #define ESP_READY       2
  #define ESP_GPIO0      -1
#elif defined(ARDUINO_NRF52832_FEATHER )
  #define VS1053_RESET    -1     // VS1053 reset pin (not used!)
  #define VS1053_CS       30     // VS1053 chip select pin (output)
  #define VS1053_DCS      11     // VS1053 Data/command select pin (output)
  #define VS1053_DREQ     31     // VS1053 Data request, ideally an Interrupt pin
  #define ESP_CS          16 
  #define ESP_RESET       15
  #define ESP_READY        7
  #define ESP_GPIO0       -1
#elif defined(TEENSYDUINO) 
  #define VS1053_RESET   -1     // VS1053 reset pin (not used!)
  #define VS1053_CS       3     // VS1053 chip select pin (output)
  #define VS1053_DCS     10     // VS1053 Data/command select pin (output)
  #define VS1053_DREQ     4     // VS1053 Data request, ideally an Interrupt pin
  #define ESP_CS          5
  #define ESP_RESET       6
  #define ESP_READY       9
  #define ESP_GPIO0      -1
#else // Shield version
  #define VS1053_RESET   -1     // VS1053 reset pin (not used!)
  #define VS1053_CS       7     // VS1053 chip select pin (output)
  #define VS1053_DCS      6     // VS1053 Data/command select pin (output)
  #define VS1053_DREQ     3     // VS1053 Data request, ideally an Interrupt pin
  #define ESP_CS         10
  #define ESP_READY       9
  #define ESP_RESET       8
  #define ESP_GPIO0      -1
#endif

Adafruit_VS1053 musicPlayer =  Adafruit_VS1053(VS1053_RESET, VS1053_CS, VS1053_DCS, VS1053_DREQ);

// Use WiFiClient class to create HTTP/TCP connection
WiFiClient client;

int lastvol = 20;

#if defined (__AVR__)
  #define BUFFER_SIZE 128
#else
  #define BUFFER_SIZE 1500
#endif

CircularBuffer<uint8_t, BUFFER_SIZE> buffer;
  
void setup() {
  Serial.begin(115200);
  while (!Serial);
  delay(100);

  Serial.println(F("\n\nAdafruit VS1053 Feather WiFi Radio"));

  /************************* INITIALIZE WIFI */
  WiFi.setPins(ESP_CS, ESP_READY, ESP_RESET, ESP_GPIO0);
  Serial.print(F("Connecting to SSID ")); Serial.println(ssid);
  WiFi.begin(ssid, pass);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(F("WiFi connected"));  
  Serial.println(F("IP address: "));  Serial.println(WiFi.localIP());

  /************************* INITIALIZE MP3 Shield */
  if (! musicPlayer.begin()) { // initialise the music player
     Serial.println(F("Couldn't find VS1053, do you have the right pins defined?"));
     while (1) delay(10);
  }

  Serial.println(F("VS1053 found"));
  //musicPlayer.sineTest(0x44, 10);    // Make a tone to indicate VS1053 is working
  
  // Set volume for left, right channels. lower numbers == louder volume!
  musicPlayer.setVolume(lastvol, lastvol);

  // don't use an IRQ, we'll hand-feed
  /************************* INITIALIZE STREAM */
  Serial.print(F("Connecting to "));  Serial.println(host);
  
  if (!client.connect(host, httpPort)) {
    Serial.println(F("Connection failed"));
    while (1);
  }
  
  // We now create a URI for the request
  Serial.print(F("Requesting URL: ")); Serial.println(path);
  
  // This will send the request to the server
  client.print(String("GET ") + path + " HTTP/1.1\r\n" +
               "Host: " + host + "\r\n" + 
               "Connection: close\r\n\r\n");
}


void loop() {
#if defined(DEBUG)
  Serial.print(F("Client Avail: ")); Serial.print(client.available());
  Serial.print(F("\tBuffer Avail: ")); Serial.println(buffer.available());
#endif

  // Prioritize reading data from the ESP32 into the buffer (it sometimes stalls)
  while (client.available() && buffer.available()) {
    uint8_t minibuff[BUFFER_SIZE];

    int bytesread = client.read(minibuff, buffer.available());
#if defined(DEBUG)
    Serial.print(F("Client read: ")); Serial.println(bytesread);
#endif
    for (int i=0; i<bytesread; i++) {
      buffer.push(minibuff[i]);      // push every byte we read
    }
  }

  // OK if we can't buffer more, see if we should play!
  if (musicPlayer.readyForData() && (buffer.size() > 0)) {
    //wants more data! check we have something available from the stream
    uint8_t mp3buff[32];   // vs1053 likes 32 bytes at a time

    int byteswrite = min(32, buffer.size());
#if defined(DEBUG)
    Serial.print(F("MP3 write: ")); Serial.println(byteswrite);
#endif

    // push to mp3
    for (int i=0; i<byteswrite; i++) {
      mp3buff[i] = buffer.shift();      // push every byte we read
    }
    musicPlayer.playData(mp3buff, byteswrite);
  }
}
