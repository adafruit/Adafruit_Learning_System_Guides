// Stream MP3s over WiFi on Metro M4 Express and play via music maker shield

#include <SPI.h>
#include <Adafruit_VS1053.h>
#include <WiFiNINA.h>
#include <CircularBuffer.h>
#include "arduino_secrets.h" 

///////please enter your sensitive data in the Secret tab/arduino_secrets.h
char ssid[] = SECRET_SSID;        // your network SSID (name)
char pass[] = SECRET_PASS;    // your network password (use for WPA, or use as key for WEP)


//  http://ice1.somafm.com/u80s-128-mp3
const char *host = "ice1.somafm.com";
const char *path = "/u80s-128-mp3";
//const char *path = "/doomed-128-mp3";
int httpPort = 80;

// These are the pins used
#define VS1053_RESET   -1     // VS1053 reset pin (not used!)
#define VS1053_CS       7     // VS1053 chip select pin (output)
#define VS1053_DCS      6     // VS1053 Data/command select pin (output)
#define VS1053_DREQ     3     // VS1053 Data request, ideally an Interrupt pin

Adafruit_VS1053 musicPlayer =  Adafruit_VS1053(VS1053_RESET, VS1053_CS, VS1053_DCS, VS1053_DREQ);

// Use WiFiClient class to create HTTP/TCP connection
WiFiClient client;

int lastvol = 30;

#define BUFFER_SIZE 1500
CircularBuffer<uint8_t, BUFFER_SIZE> buffer;
  
void setup() {
  Serial.begin(115200);
  while (!Serial);
  delay(100);

  Serial.println("\n\nAdafruit VS1053 Feather WiFi Radio");

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

  /************************* INITIALIZE WIFI */
  Serial.print("Connecting to SSID "); Serial.println(ssid);
  WiFi.begin(ssid, pass);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("WiFi connected");  
  Serial.println("IP address: ");  Serial.println(WiFi.localIP());

  /************************* INITIALIZE STREAM */
  Serial.print("Connecting to ");  Serial.println(host);
  
  if (!client.connect(host, httpPort)) {
    Serial.println("Connection failed");
    while (1);
  }
  
  // We now create a URI for the request
  Serial.print("Requesting URL: "); Serial.println(path);
  
  // This will send the request to the server
  client.print(String("GET ") + path + " HTTP/1.1\r\n" +
               "Host: " + host + "\r\n" + 
               "Connection: close\r\n\r\n");
}


void loop() {
  Serial.print("Client Avail: "); Serial.print(client.available());
  Serial.print("\tBuffer Avail: "); Serial.println(buffer.available());

  // Prioritize reading data from the ESP32 into the buffer (it sometimes stalls)
  while (client.available() && buffer.available()) {
    uint8_t minibuff[BUFFER_SIZE];

    int bytesread = client.read(minibuff, buffer.available());
    Serial.print("Client read: "); Serial.println(bytesread);

    for (int i=0; i<bytesread; i++) {
      buffer.push(minibuff[i]);      // push every byte we read
    }
  }

  // OK if we can't buffer more, see if we should play!
  if (musicPlayer.readyForData() && (buffer.size() > 0)) {
    //wants more data! check we have something available from the stream
    uint8_t mp3buff[32];   // vs1053 likes 32 bytes at a time

    int byteswrite = min(32, buffer.size());
    Serial.print("MP3 write: "); Serial.println(byteswrite);

    // push to mp3
    for (int i=0; i<byteswrite; i++) {
      mp3buff[i] = buffer.shift();      // push every byte we read
    }
    musicPlayer.playData(mp3buff, byteswrite);
  }
}
