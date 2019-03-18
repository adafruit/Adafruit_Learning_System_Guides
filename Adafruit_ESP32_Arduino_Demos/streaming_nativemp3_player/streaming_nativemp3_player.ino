// Stream MP3s over WiFi on Metro M4 Express and play via music maker shield

//#define DEBUG_OUTPUT

#include <SPI.h>
#include <WiFiNINA.h>
#include <CircularBuffer.h>  // From Agileware
#include <Adafruit_MP3.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ILI9341.h>
#include "arduino_secrets.h" 

///////please enter your sensitive data in the Secret tab/arduino_secrets.h
char ssid[] = SECRET_SSID;        // your network SSID (name)
char pass[] = SECRET_PASS;    // your network password (use for WPA, or use as key for WEP)



// USE ~64Kbps streams if possible, 128kb is too much data ;)
// To convert shoutcast urls https://www.radiodj.ro/community/index.php?topic=3326.0

// These wont work well, but they might some day in the future
//const char *stream = "http://ice1.somafm.com/u80s-128-mp3";           // soma fm 80s @ 128 kbps
//const char *stream = "http://77.235.42.90/;stream.mp3";               // shoutcast swiss downtempo @ 128 kbps
//const char *stream = "http://uk7.internet-radio.com:8226/;stream.mp3";  // Box UK Radio danceradiouk

// Best options:
const char *stream = "https://18123.live.streamtheworld.com/CSPANRADIO.mp3"; // CSPAN radio @ 40 KBps
//const char *stream = "http://wmbr.org:8000/med";                      // WMBR @ 64Kbps
//const char *stream = "http://amber.streamguys.com:4870/;stream.mp3";  // WZBC @ 56kbps
//const char *stream = "https://adafruit-podcasts.s3.amazonaws.com/media/G_br7smHsvU_NA.mp3";  // circuitpy podcast, VBR
//const char *stream = "http://bbcmedia.ic.llnwd.net/stream/bbcmedia_radio4lw_mf_p";  // Radio 4 mono 128k

WiFiClient client; // Use WiFiClient class to create HTTP/TCP connection
String host, path;
int port = 80;

Adafruit_MP3 player;  // The MP3 player
#define BUFFER_SIZE 8000     // we need a lot of buffer to keep from underruns! but not too big?
CircularBuffer<uint8_t, BUFFER_SIZE> buffer;
bool paused = true;
float gain = 1;

void setup() {
  Serial.begin(115200);
  //while (!Serial);
  delay(100);
  Serial.println("\nAdafruit Native MP3 WiFi Radio");

  String stream_str = String(stream);
  Serial.println(stream_str);
  if (stream_str.startsWith("http://")) {
    Serial.println("Regular HTTP stream");
    stream_str = stream_str.substring(7);
  }
  if (stream_str.startsWith("https://")) {
    Serial.println("Secre HTTPS stream");
    stream_str = stream_str.substring(8);
  }

  // extract host before port
  int colon = stream_str.indexOf(':');
  if (colon != -1) {
    host = stream_str.substring(0, colon);
    stream_str = stream_str.substring(colon+1);
    // extract port before /
    int slash = stream_str.indexOf('/');
    if (slash != -1) {
      String port_str = stream_str.substring(0, slash);
      port = port_str.toInt();
    } else {
      Serial.println("Couldn't locate path /");
      while (1);
    }
    stream_str = stream_str.substring(slash);
  } else {
    // extract host before /
    int slash = stream_str.indexOf('/');
    if (slash != -1) {
      host = stream_str.substring(0, slash);
      stream_str = stream_str.substring(slash);
    } else {
      Serial.println("Couldn't locate path /");
      while (1);
    }
  }
  path = String(stream_str);
  Serial.print("Server: "); Serial.println(host);
  Serial.print("Port #"); Serial.println(port);  
  Serial.print("Path: "); Serial.println(path);

  player.begin();

  //do this when there are samples ready
  player.setSampleReadyCallback(writeDacs);

  //do this when more data is required
  player.setBufferCallback(getMoreData);

  analogWrite(A0, 2048);
  player.play();
  player.pause();
  
  /************************* INITIALIZE WIFI */
  Serial.print("Connecting to SSID "); Serial.println(ssid);
  WiFi.begin(ssid, pass);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("WiFi connected");  
  Serial.println("IP address: ");  Serial.println(WiFi.localIP());

  connectStream();
}


void connectStream(void) {
  client.stop();
  /************************* INITIALIZE STREAM */
  Serial.print("Connecting to ");  Serial.println(host);
  
  if (!client.connect(host.c_str(), port)) {
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
  if (!client.connected()) {
    connectStream();
  }
#ifdef DEBUG_OUTPUT
  Serial.print("Client Avail: "); Serial.print(client.available());
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
  if (client.available() && buffer.available()) {
   
    uint8_t minibuff[BUFFER_SIZE];

    int bytesread = client.read(minibuff, buffer.available());
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
    return 0;    // we'll try again later!
  }
  for (int i=0; i<toWrite; i++) {
    writeHere[i] = buffer.shift();
  }
  return toWrite;
}
