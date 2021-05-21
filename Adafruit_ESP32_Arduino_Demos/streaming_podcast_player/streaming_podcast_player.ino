// Stream MP3s over WiFi on Metro M4 Express and play via music maker shield

//#define DEBUG_OUTPUT

#include <ArduinoHttpClient.h>
#include <WiFiNINA.h>
#include <CircularBuffer.h>  // From Agileware
#include "Adafruit_MP3.h"
#include "arduino_secrets.h" 
#include <Adafruit_TinyUSB.h>

///////please enter your sensitive data in the Secret tab/arduino_secrets.h
char ssid[] = SECRET_SSID;        // your network SSID (name)
char pass[] = SECRET_PASS;    // your network password (use for WPA, or use as key for WEP)

// Use ~64Kbps streams if possible, 128kb+ is too much data ;)

// CircuitPython weekly
//const char *xmlfeed = "http://adafruit-podcasts.s3.amazonaws.com/circuitpython_weekly_meeting/audio-podcast.xml";
const char *xmlfeed = "http://www.2600.com/oth.xml"; // yay they have a 16 kbps

// Too high bitrate!
//const char *xmlfeed = "http://feeds.soundcloud.com/users/soundcloud:users:93913472/sounds.rss";
//const char *xmlfeed = "https://theamphour.com/feed/";

/************* WiFi over ESP32 client for MP3 datastream */
WiFiClient http_client; // Use WiFiClient class to create HTTP/TCP connection
WiFiSSLClient https_client; // Use WiFiClient class to create HTTP/TCP connection
char *stream_host, *stream_path;
int stream_port = 80;

/************* Native MP3 decoding supported on M4 chips */
Adafruit_MP3 player;  // The MP3 player
#define BUFFER_SIZE 8000     // we need a lot of buffer to keep from underruns! but not too big?
CircularBuffer<uint8_t, BUFFER_SIZE> buffer;
bool paused = true;
float gain = 1;

void setup() {
  Serial.begin(115200);
  while (!Serial);
  delay(100);
  Serial.println("\nAdafruit Native MP3 Podcast Radio");

  /************************* INITIALIZE WIFI */
  Serial.print("Connecting to SSID "); Serial.println(ssid);
  WiFi.begin(ssid, pass);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.print("WiFi connected. ");  
  Serial.print("My IP address: ");  Serial.println(WiFi.localIP());


  char *mp3_stream, *pubdate;
  getLatestMP3(xmlfeed, &mp3_stream, &pubdate);
  Serial.println(mp3_stream);
  Serial.println(pubdate);

  splitURL(mp3_stream, &stream_host, &stream_port, &stream_path);
  if (stream_port == 443) {
    Serial.println("We don't support SSL MP3 playback, defaulting back to port 80");
    stream_port = 80;
  }
  player.begin();

  //do this when there are samples ready
  player.setSampleReadyCallback(writeDacs);

  //do this when more data is required
  player.setBufferCallback(getMoreData);

  analogWrite(A0, 2048);
  player.play();
  player.pause();
  

  connectStream();
}

bool getLatestMP3(String xmlfeed, char **mp3_url, char **date_str) {
  char *xml_host, *xml_path;
  int xml_port = 80;

  bool found_mp3=false, found_date=false;

  splitURL(xmlfeed, &xml_host, &xml_port, &xml_path);
        
  Serial.print("XML Server: "); Serial.println(xml_host);
  Serial.print("XML Port #"); Serial.println(xml_port);  
  Serial.print("XML Path: "); Serial.println(xml_path);

  WiFiClient *xml_client;
  if (xml_port == 443) {
      xml_client = &https_client;
  } else {
      xml_client = &http_client;
  }
  
  if (!xml_client->connect(xml_host, xml_port)) {
    Serial.println("Connection failed");
    return false;
  }

  // We now create a URI for the request
  Serial.print("Requesting XML URL: "); Serial.println(xml_path);
  
  // This will send the request to the server
  xml_client->print(String("GET ") + xml_path + " HTTP/1.1\r\n" +
                    "Host: " + xml_host + "\r\n" + 
                    "Connection: close\r\n\r\n");

  while (xml_client->connected()) {
    if (!xml_client->available()) { continue; }
    char c = xml_client->read();    
    Serial.print(c);
    if (c == '<') {
      String tag = xml_client->readStringUntil('>');
      Serial.print(tag);

      if (!found_mp3 && (tag.indexOf("enclosure") != -1)) {  // get first enclosure
        int i = tag.indexOf("url=\"");
        if (i == -1) continue;
        tag = tag.substring(i+5);
        int end = tag.indexOf("\"");
        if (end == -1) continue;
        tag = tag.substring(0, end);
        *mp3_url = (char *)malloc(tag.length()+1);
        tag.toCharArray(*mp3_url, tag.length()+1);
        // Serial.print("****"); Serial.println(*mp3_url);
        found_mp3 = true;
      }
      
      if (!found_date && (tag.indexOf("pubDate") != -1)) {  // get first pubdate
        String date = xml_client->readStringUntil('<');
        *date_str = (char *)malloc(date.length()+1);
        date.toCharArray(*date_str, date.length()+1);
        //  Serial.print("****"); Serial.println(*date_str);
        found_date = true;
      }
    }
    if (found_date && found_mp3) {
       break;
    }
  }
  xml_client->stop();
  return (found_date && found_mp3);
}

void connectStream(void) {
  http_client.stop();
  /************************* INITIALIZE STREAM */
  Serial.print("Stream Server: "); Serial.println(stream_host);
  Serial.print("Stream Port #"); Serial.println(stream_port);  
  Serial.print("Stream Path: "); Serial.println(stream_path);
  
  if (!http_client.connect(stream_host, stream_port)) {
    Serial.println("Connection failed");
    while (1);
  }
  
  // We now create a URI for the request
  Serial.print("Requesting URL: "); Serial.println(stream_path);
  
  // This will send the request to the server
  http_client.print(String("GET ") + stream_path + " HTTP/1.1\r\n" +
                    "Host: " + stream_host + "\r\n" + 
                    "Connection: close\r\n\r\n");
}


void loop() {
  if (!http_client.connected()) {
    connectStream();
  }
#ifdef DEBUG_OUTPUT
  Serial.print("Client Avail: "); Serial.print(http_client.available());
  Serial.print("\tBuffer Avail: "); Serial.println(buffer.available());
#endif
  int ret = player.tick();

  if (ret != 0) {   // some error, best to pause & rebuffer
    Serial.print("MP3 error: "); Serial.println(ret);
    player.pause(); paused = true;
  }
  if ( paused && (buffer.size() > 6000)) {  // buffered, restart!
    player.resume(); paused = false;
  }

  // Prioritize reading data from the ESP32 into the buffer (it sometimes stalls)
  if (http_client.available() && buffer.available()) {
   
    uint8_t minibuff[BUFFER_SIZE];

    int bytesread = http_client.read(minibuff, buffer.available());
#ifdef DEBUG_OUTPUT
    Serial.print("Client read: "); Serial.print(bytesread);
#endif

    noInterrupts();
    for (int i=0; i<bytesread; i++) {
      buffer.push(minibuff[i]);      // push every byte we read
    }
    interrupts();
#ifdef DEBUG_OUTPUT
    Serial.println(" OK");
#endif
  }
}


void writeDacs(int16_t l, int16_t r){
  uint16_t val = map(l, -32768, 32767, 0, 4095 * gain);
  analogWrite(A0, val);
}


int getMoreData(uint8_t *writeHere, int thisManyBytes){
#ifdef DEBUG_OUTPUT
  Serial.print("Wants: "); Serial.print(thisManyBytes);
#endif 
  int toWrite = min(buffer.size(), thisManyBytes);
#ifdef DEBUG_OUTPUT
  Serial.print(" have: "); Serial.println(toWrite);
#endif 
  // this is a bit of a hack but otherwise the decoder chokes
  if (toWrite < 128) {
    //return 0;    // we'll try again later!
  }
  for (int i=0; i<toWrite; i++) {
    writeHere[i] = buffer.shift();
  }
  return toWrite;
}


bool splitURL(String url, char **host, int *port, char **path){
  Serial.println(url);
  if (url.startsWith("http://")) {
    Serial.println("Regular HTTP stream");
    url = url.substring(7);
    *port = 80;
  }
  if (url.startsWith("https://")) {
    Serial.println("Secure HTTPS stream");
    url = url.substring(8);
    *port = 443;
  }

  // extract host before port
  int colon = url.indexOf(':');
  int slash = url.indexOf('/');
  if ((slash != -1) && (colon != -1) && (colon < slash)) {
    String host_str = url.substring(0, colon);
    *host = (char *)malloc(host_str.length()+1);
    host_str.toCharArray(*host, host_str.length()+1);
    url = url.substring(colon+1);
    // extract port before /
    slash = url.indexOf('/');
    if (slash != -1) {
      String port_str = url.substring(0, slash);
      *port = port_str.toInt();
    } else {
      Serial.println("Couldn't locate path /");
      return false;
    }
    url = url.substring(slash);
  } else {
    // extract host before /
    slash = url.indexOf('/');
    if (slash != -1) {
      String host_str = url.substring(0, slash);
      *host = (char *)malloc(host_str.length()+1);
      host_str.toCharArray(*host, host_str.length()+1);
      url = url.substring(slash);
    } else {
      Serial.println("Couldn't locate path /");
      return false;
    }
  }
  *path = (char *)malloc(url.length()+1);
  url.toCharArray(*path, url.length()+1);
}
