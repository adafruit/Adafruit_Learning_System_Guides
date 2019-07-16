/*
IMPORTANT: THIS SOFTWARE CURRENTLY DOES NOT WORK, and future
status is uncertain.  Twitter has changed their API to require
SSL (Secure Sockets Layer) on -all- connections, a complex
operation beyond the Arduino's ability to handle.  The code is
being kept around on the chance that a suitable proxy service
becomes available...but at present we have no such service, no
code for such, nor a schedule or even a firm commitment to
pursue it.  For projects requiring Twitter we now recommend
using an SSL-capable system such as Raspberry Pi.  For example:
https://github.com/adafruit/Python-Thermal-Printer
*/

/*
Gutenbird demo sketch: monitors one or more Twitter accounts for changes,
displaying updates on attached thermal printer.
Written by Adafruit Industries, distributed under BSD License.
MUST BE CONFIGURED FOR TWITTER 1.1 API BEFORE USE.  See notes below.
REQUIRES ARDUINO IDE 1.0 OR LATER -- Back-porting is not likely to occur,
as the code is deeply dependent on the Stream class, etc.
Requires Adafruit fork of Peter Knight's Cryptosuite library for Arduino:
https://github.com/adafruit/Cryptosuite
Required hardware includes an Ethernet-connected Arduino board such as the
Arduino Ethernet or other Arduino-compatible board with an Arduino Ethernet
Shield, plus an Adafruit Mini Thermal Receipt printer and all related power
supplies and cabling.
Resources:
http://www.adafruit.com/products/418 Arduino Ethernet
http://www.adafruit.com/products/284 FTDI Friend
http://www.adafruit.com/products/201 Arduino Uno
http://www.adafruit.com/products/201 Ethernet Shield
http://www.adafruit.com/products/597 Mini Thermal Receipt Printer
http://www.adafruit.com/products/600 Printer starter pack
Uses Twitter 1.1 API.  This REQUIRES a Twitter account and some account
configuration.  Start at dev.twitter.com, sign in with your Twitter
credentials, select "My Applications" from the avatar drop-down menu at the
top right, then "Create a new application."  Provide a name, description,
placeholder URL and complete the captcha, after which you'll be provided a
"consumer key" and "consumer secret" for your app.  Select "Create access
token" to also generate an "access token" and "access token secret."
ALL FOUR STRINGS must be copied to the correct positions in the globals below,
and configure the search string to your liking.  DO NOT SHARE your keys or
secrets!  If you put code on Github or other public repository, replace them
with dummy strings.
Copyright (c) 2013 Adafruit Industries.
All rights reserved.
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
- Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.
- Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
*/

#include <SPI.h>
#include <Ethernet.h>
#include <EthernetUdp.h>
#include <Dns.h>
#include <sha1.h>
#include <Adafruit_Thermal.h>
#include <SoftwareSerial.h>

// Similar to F(), but for PROGMEM string pointers rather than literals
#define F2(progmem_ptr) (const __FlashStringHelper *)progmem_ptr

// Configurable globals.  Edit to your needs. -------------------------------

const char PROGMEM
  // Twitter application credentials -- see notes above -- DO NOT SHARE.
  consumer_key[]  = "PUT_YOUR_CONSUMER_KEY_HERE",
  access_token[]  = "PUT_YOUR_ACCESS_TOKEN_HERE",
  signingKey[]    = "PUT_YOUR_CONSUMER_SECRET_HERE"      // Consumer secret
    "&"             "PUT_YOUR_ACCESS_TOKEN_SECRET_HERE", // Access token secret
  // The ampersand is intentional -- do not delete!

  // queryString can be any valid Twitter API search string, including
  // boolean operators.  See http://dev.twitter.com/docs/using-search
  // for options and syntax.  Funny characters do NOT need to be URL
  // encoded here -- the code takes care of that.
  queryString[]   = "from:Adafruit",

// Other globals.  You probably won't need to change these. -----------------

  endpoint[]      = "/1.1/search/tweets.json",
  agent[]         = "Gutenbird v1.0";
const char
  host[]          = "api.twitter.com";
const int
  led_pin         = 3,           // To status LED (hardware PWM pin)
  // Pin 4 is skipped -- this is the Card Select line for Arduino Ethernet!
  printer_RX_Pin  = 5,           // Printer connection: green wire
  printer_TX_Pin  = 6,           // Printer connection: yellow wire
  printer_Ground  = 7;           // Printer connection: black wire
const unsigned long
  pollingInterval = 60L * 1000L, // Note: Twitter server will allow 150/hr max
  searchesPerDay  = 86400000L / pollingInterval,
  connectTimeout  = 15L * 1000L, // Max time to wait for server connection
  responseTimeout = 15L * 1000L; // Max time to wait for data from server
Adafruit_Thermal
  printer(printer_RX_Pin, printer_TX_Pin);
byte
  maxTweets = 1, // One tweet on first run; avoid runaway output
  sleepPos  = 0, // Current "sleep throb" table position
  resultsDepth,  // Used in JSON parsing
  // Ethernet MAC address is found on sticker on Ethernet shield or board:
  mac[] = { 0x90, 0xA2, 0xDA, 0x00, 0x76, 0x09 };
IPAddress
  ip(192,168,0,118); // Fallback address -- code will try DHCP first
char
  lastId[21],    // 18446744073709551615\0 (64-bit maxint as string)
  timeStamp[32], // WWW, DD MMM YYYY HH:MM:SS +XXXX\0
  fromUser[16],  // Max username length (15) + \0
  msgText[141],  // Max tweet length (140) + \0
  name[12],      // Temp space for name:value parsing
  value[141];    // Temp space for name:value parsing
int
  searchCount = 0;
unsigned long
  currentTime = 0L;
EthernetClient
  client;
PROGMEM byte
  sleepTab[] = { // "Sleep throb" brightness table (reverse for second half)
      0,   0,   0,   0,   0,   0,   0,   0,   0,   1,
      1,   1,   2,   3,   4,   5,   6,   8,  10,  13,
     15,  19,  22,  26,  31,  36,  41,  47,  54,  61,
     68,  76,  84,  92, 101, 110, 120, 129, 139, 148,
    158, 167, 177, 186, 194, 203, 211, 218, 225, 232,
    237, 242, 246, 250, 252, 254, 255 };

// --------------------------------------------------------------------------

void setup() {

  // Set up LED "sleep throb" ASAP, using Timer1 interrupt:
  TCCR1A  = _BV(WGM11); // Mode 14 (fast PWM), 64:1 prescale, OC1A off
  TCCR1B  = _BV(WGM13) | _BV(WGM12) | _BV(CS11) | _BV(CS10);
  ICR1    = 8333;       // ~30 Hz between sleep throb updates
  TIMSK1 |= _BV(TOIE1); // Enable Timer1 interrupt
  sei();                // Enable global interrupts

  randomSeed(analogRead(0));
  Serial.begin(57600);
  pinMode(printer_Ground, OUTPUT);
  digitalWrite(printer_Ground, LOW); // Just a reference ground, not power
  printer.begin();
  printer.sleep();

  // Initialize Ethernet connection.  Request dynamic
  // IP address, fall back on fixed IP if that fails:
  Serial.print(F("Initializing Ethernet..."));
  if(Ethernet.begin(mac)) {
    Serial.print(F("OK\r\n"));
  } else {
    Serial.print(F("\r\nno DHCP response, using static IP address."));
    Ethernet.begin(mac, ip);
  }

  // Get initial time from time server (make a few tries if needed)
  for(uint8_t i=0; (i<5) && !(currentTime = getTime()); delay(15000L), i++);

  // Clear all string data
  strcpy_P(lastId, PSTR("1"));
  timeStamp[0] = fromUser[0] = msgText[0] = name[0] = value[0] = 0;
}

// Search occurs in loop. ---------------------------------------------------

void loop() {
  uint8_t                  *in, out, i;
  char                      nonce[9],       // 8 random digits + NUL
                            searchTime[11], // 32-bit int + NUL
                            b64[29];
  unsigned long             startTime, t;
  static const char PROGMEM b64chars[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

  startTime = millis();

  // Disable Timer1 interrupt during network access, else there's trouble.
  // Just show LED at steady 100% while working.  :T
  TIMSK1 &= ~_BV(TOIE1);
  analogWrite(led_pin, 255);

  // Initialize unique values for query
  sprintf(nonce, "%04x%04x", random() ^ currentTime, startTime ^ currentTime);
  sprintf(searchTime, "%ld", currentTime);

  // Some debugging/testing/status stuff
  Serial.print(F("  Current time: "));
  Serial.println(currentTime);
  Serial.print(F("  Last ID: "));
  Serial.println(lastId);

  Sha1.initHmac_P((uint8_t *)signingKey, sizeof(signingKey) - 1);

  // A dirty hack makes the Oauth song and dance MUCH simpler within the
  // Arduino's limited RAM and CPU.  A proper general-purpose implementation
  // would be expected to URL-encode keys and values (from the complete list
  // of GET parameters and authentication values), sort by encoded key,
  // concatenate and URL-encode the combined result.  Sorting is avoided
  // because every query this program performs has exactly the same set of
  // parameters, so we've pre-sorted the list as it appears here.  Keys
  // (and many values) are pre-encoded because they never change; many are
  // passed through verbatim because the format is known to not require
  // encoding.  Most reside in PROGMEM, not RAM.  This is bending a LOT of
  // rules of Good and Proper Authentication and would land you an 'F' in
  // Comp Sci class, but it handles the required task and is VERY compact.
  Sha1.print(F("GET&http%3A%2F%2F"));
  Sha1.print(host);
  urlEncode(Sha1, endpoint, true, false);
  Sha1.print(F("&count%3D"));
  Sha1.print(maxTweets);
  Sha1.print(F("%26include_entities%3D0%26oauth_consumer_key%3D"));
  Sha1.print(F2(consumer_key));
  Sha1.print(F("%26oauth_nonce%3D"));
  Sha1.print(nonce);
  Sha1.print(F("%26oauth_signature_method%3DHMAC-SHA1%26oauth_timestamp%3D"));
  Sha1.print(searchTime);
  Sha1.print(F("%26oauth_token%3D"));
  Sha1.print(F2(access_token));
  Sha1.print(F("%26oauth_version%3D1.0%26q%3D"));
  urlEncode(Sha1, queryString, true, true);
  Sha1.print(F("%26since_id%3D"));
  Sha1.print(lastId);

  // base64-encode SHA-1 hash output.  This is NOT a general-purpose base64
  // encoder!  It's stripped down for the fixed-length hash -- always 20
  // bytes input, always 27 chars output + '='.
  for(in = Sha1.resultHmac(), out=0; ; in += 3) { // octets to sextets
    b64[out++] =   in[0] >> 2;
    b64[out++] = ((in[0] & 0x03) << 4) | (in[1] >> 4);
    if(out >= 26) break;
    b64[out++] = ((in[1] & 0x0f) << 2) | (in[2] >> 6);
    b64[out++] =   in[2] & 0x3f;
  }
  b64[out] = (in[1] & 0x0f) << 2;
  // Remap sextets to base64 ASCII chars
  for(i=0; i<=out; i++) b64[i] = pgm_read_byte(&b64chars[b64[i]]);
  b64[i++] = '=';
  b64[i++] = 0;

  Serial.print(F("Connecting to server..."));
  t = millis();
  while((client.connect(host, 80) == false) &&
    ((millis() - t) < connectTimeout));

  if(client.connected()) { // Success!
    Serial.print(F("OK\r\nIssuing HTTP request..."));

    // Unlike the hash prep, parameters in the HTTP request don't require
    // sorting, but are still somewhat ordered by function: GET parameters
    // (search values), HTTP headers and Oauth credentials.
    client.print(F("GET "));
    client.print(F2(endpoint));
    client.print(F("?count="));
    client.print(maxTweets);
    client.print(F("&since_id="));
    client.print(lastId);
    client.print(F("&include_entities=0&q="));
    urlEncode(client, queryString, true, false);
    client.print(F(" HTTP/1.1\r\nHost: "));
    client.print(host);
    client.print(F("\r\nUser-Agent: "));
    client.print(F2(agent));
    client.print(F("\r\nConnection: close\r\n"
                       "Content-Type: application/x-www-form-urlencoded;charset=UTF-8\r\n"
                       "Authorization: Oauth oauth_consumer_key=\""));
    client.print(F2(consumer_key));
    client.print(F("\", oauth_nonce=\""));
    client.print(nonce);
    client.print(F("\", oauth_signature=\""));
    urlEncode(client, b64, false, false);
    client.print(F("\", oauth_signature_method=\"HMAC-SHA1\", oauth_timestamp=\""));
    client.print(searchTime);
    client.print(F("\", oauth_token=\""));
    client.print(F2(access_token));
    client.print(F("\", oauth_version=\"1.0\"\r\n\r\n"));

    Serial.print(F("OK\r\nAwaiting results (if any)..."));
    t = millis();
    while((!client.available()) && ((millis() - t) < responseTimeout));
    if(client.available()) { // Response received?
      // Could add HTTP response header parsing here (400, etc.)
      if(client.find("\r\n\r\n")) { // Skip HTTP response header
        Serial.print(F("OK\r\nProcessing results...\r\n"));
        resultsDepth = 0;
        jsonParse(0, 0);
      } else Serial.print(F("response not recognized.\r\n"));
    } else   Serial.print(F("connection timed out.\r\n"));
    Serial.print(F("Done.\r\n"));

    client.stop();
  } else { // Couldn't contact server
    Serial.print(F("failed\r\n"));
  }

  // Update time in seconds.  Once per day, re-sync with time server
  currentTime += pollingInterval / 1000L;
  if((++searchCount >= searchesPerDay) && (t = getTime())) {
    currentTime = t;
    searchCount = 0;
  }

  // Sometimes network access & printing occurrs so quickly, the steady-on
  // LED wouldn't even be apparent, instead resembling a discontinuity in
  // the otherwise smooth sleep throb.  Keep it on at least 4 seconds.
  while((millis() - startTime) < 4000UL);

  // Pause between queries, factoring in time already spent on network
  // access, parsing, printing and LED pause above.
  if((millis() - startTime) < pollingInterval) {
    Serial.print(F("Pausing..."));
    sleepPos = sizeof(sleepTab); // Resume following brightest position
    TIMSK1 |= _BV(TOIE1); // Re-enable Timer1 interrupt for sleep throb
    while((millis() - startTime) < pollingInterval);
    Serial.print(F("done\r\n"));
  }
}

// Helper functions. --------------------------------------------------------

boolean jsonParse(int depth, byte endChar) {
  int     c, i;
  boolean readName = true;
  for(;;) {
    while(isspace(c = timedRead())); // Scan past whitespace
    if(c < 0)        return false;   // Timeout
    if(c == endChar) return true;    // EOD

    if(c == '{') { // Object follows
      if(!jsonParse(depth + 1, '}')) return false;
      if(!depth)                     return true; // End of file
      if(depth == resultsDepth) { // End of object in results list
        // Output one tweet to printer
        printer.wake();
        printer.inverseOn();
        printer.write(' ');
        printer.print(fromUser);
        for(i=strlen(fromUser); i<31; i++) printer.write(' ');
        printer.inverseOff();
        printer.underlineOn();
        printer.print(timeStamp);
        for(i=strlen(timeStamp); i<32; i++) printer.write(' ');
        printer.underlineOff();
        printer.println(msgText);
        printer.feed(3);
        printer.sleep();

        // Dump to serial console as well
        Serial.print(F("  User: "));
        Serial.println(fromUser);
        Serial.print(F("  Text: "));
        Serial.println(msgText);
        Serial.print(F("  Time: "));
        Serial.println(timeStamp);

        // Clear strings for next object
        timeStamp[0] = fromUser[0] = msgText[0] = 0;

        maxTweets = 5; // After first, subsequent queries allow more tweets
      }
    } else if(c == '[') { // Array follows
      if((!resultsDepth) && (!strcasecmp(name, "statuses")))
        resultsDepth = depth + 1;
      if(!jsonParse(depth + 1,']')) return false;
    } else if((c == '"') || (c == '\'')) { // String follows
      if(readName) { // Name-reading mode
        if(!readString(name, sizeof(name)-1, c)) return false;
      } else { // Value-reading mode
        if(!readString(value, sizeof(value)-1, c)) return false;
        // Process name and value strings:
        if       (!strcasecmp(name, "max_id_str")) {
          strncpy(lastId, value, sizeof(lastId)-1);
        } else if(!strcasecmp(name, "created_at")) {
          // Use created_at value for tweet, not user
          if(depth == (resultsDepth + 1)) {
            strncpy(timeStamp, value, sizeof(timeStamp)-1);
          }
        } else if(!strcasecmp(name, "screen_name")) {
          strncpy(fromUser, value, sizeof(fromUser)-1);
        } else if(!strcasecmp(name, "text")) {
          strncpy(msgText, value, sizeof(msgText)-1);
        } else if((!strcasecmp(name, "id_str")) &&
                  (strcasecmp(value, lastId) > 0) &&
                  (depth == (resultsDepth + 1))) {
          strncpy(lastId, value, sizeof(lastId)-1);
        }
      }
    } else if(c == ':') { // Separator between name:value
      readName = false; // Now in value-reading mode
      value[0] = 0;     // Clear existing value data
    } else if(c == ',') {
      // Separator between name:value pairs.
      readName = true; // Now in name-reading mode
      name[0]  = 0;    // Clear existing name data
    } // Else true/false/null or a number follows.  These values aren't
      // used or expected by this program, so just ignore...either a comma
      // or endChar will come along eventually, these are handled above.
  }
}

// Read string from client stream into destination buffer, up to a maximum
// requested length.  Buffer should be at least 1 byte larger than this to
// accommodate NUL terminator.  Opening quote is assumed already read,
// closing quote will be discarded, and stream will be positioned
// immediately following the closing quote (regardless whether max length
// is reached -- excess chars are discarded).  Returns true on success
// (including zero-length string), false on timeout/read error.
boolean readString(char *dest, int maxLen, char quote) {
  int c, len = 0;

  while((c = timedRead()) != quote) { // Read until closing quote
    if(c == '\\') {    // Escaped char follows
      c = timedRead(); // Read it
      // Certain escaped values are for cursor control --
      // there might be more suitable printer codes for each.
      if     (c == 'b') c = '\b'; // Backspace
      else if(c == 'f') c = '\f'; // Form feed
      else if(c == 'n') c = '\n'; // Newline
      else if(c == 'r') c = '\r'; // Carriage return
      else if(c == 't') c = '\t'; // Tab
      else if(c == 'u') c = unidecode(4);
      else if(c == 'U') c = unidecode(8);
      // else c is unaltered -- an escaped char such as \ or "
    } // else c is a normal unescaped char

    if(c < 0) return false; // Timeout

    // In order to properly position the client stream at the end of
    // the string, characters are read to the end quote, even if the max
    // string length is reached...the extra chars are simply discarded.
    if(len < maxLen) dest[len++] = c;
  }

  dest[len] = 0;
  return true; // Success (even if empty string)
}

// Read a given number of hexadecimal characters from client stream,
// representing a Unicode symbol.  Return -1 on error, else return nearest
// equivalent glyph in printer's charset.  (See notes below -- for now,
// always returns '-' or -1.)
int unidecode(byte len) {
  int c, v, result = 0;
  while(len--) {
    if((c = timedRead()) < 0) return -1; // Stream timeout
    if     ((c >= '0') && (c <= '9')) v =      c - '0';
    else if((c >= 'A') && (c <= 'F')) v = 10 + c - 'A';
    else if((c >= 'a') && (c <= 'f')) v = 10 + c - 'a';
    else return '-'; // garbage
    result = (result << 4) | v;
  }

  // To do: some Unicode symbols may have equivalents in the printer's
  // native character set.  Remap any such result values to corresponding
  // printer codes.  Until then, all Unicode symbols are returned as '-'.
  // (This function still serves an interim purpose in skipping a given
  // number of hex chars while watching for timeouts or malformed input.)

  return '-';
}

// Read from client stream with a 5 second timeout.  Although an
// essentially identical method already exists in the Stream() class,
// it's declared private there...so this is a local copy.
int timedRead(void) {
  unsigned long start = millis();
  while((!client.available()) && ((millis() - start) < 5000L));
  return client.read();  // -1 on timeout
}

// URL-encoding output function for Print class.
// Input from RAM or PROGMEM (flash).  Double-encoding is a weird special
// case for Oauth (encoded strings get encoded a second time).
void urlEncode(
  Print      &p,       // EthernetClient, Sha1, etc.
  const char *src,     // String to be encoded
  boolean     progmem, // If true, string is in PROGMEM (else RAM)
  boolean     x2)      // If true, "double encode" parenthesis
{
  static const char PROGMEM hexChar[] = "0123456789ABCDEF";
  uint8_t c;

  while((c = (progmem ? pgm_read_byte(src) : *src))) {
    if(((c >= 'a') && (c <= 'z')) || ((c >= 'A') && (c <= 'Z')) ||
       ((c >= '0') && (c <= '9')) || strchr_P(PSTR("-_.~"), c)) {
      p.write(c);
    } else {
      if(x2) p.print("%25");
      else   p.write('%');
      p.write(pgm_read_byte(&hexChar[c >> 4]));
      p.write(pgm_read_byte(&hexChar[c & 15]));
    }
    src++;
  }
}

// Minimalist time server query; adapted from Arduino UdpNTPClient tutorial.
unsigned long getTime(void) {
  EthernetUDP   udp;
  DNSClient     dns;
  IPAddress     addr;
  byte          buf[48];
  unsigned long t = 0L;

  Serial.print(F("Polling time server..."));

  udp.begin(8888);
  dns.begin(Ethernet.dnsServerIP());

  // Get a time server address from NTP pool
  if(dns.getHostByName("pool.ntp.org", addr)) {
    static const char PROGMEM
      timeReqA[] = { 227,  0,  6, 236 },
      timeReqB[] = {  49, 78, 49,  52 };

    // Assemble and issue request packet
    memset(buf, 0, sizeof(buf));
    memcpy_P( buf    , timeReqA, sizeof(timeReqA));
    memcpy_P(&buf[12], timeReqB, sizeof(timeReqB));

    udp.beginPacket(addr, 123);
    udp.write(buf, sizeof(buf));
    udp.endPacket();

    delay(1000); // Allow time for response
    if(udp.parsePacket()) {
      // Read result, convert to UNIX time format
      udp.read(buf, sizeof(buf));
      t = (((unsigned long)buf[40] << 24) |
           ((unsigned long)buf[41] << 16) |
           ((unsigned long)buf[42] <<  8) |
            (unsigned long)buf[43]) - 2208988800UL;
      Serial.print(F("OK\r\n"));
    }
  }
  udp.stop();
  if(!t) Serial.print(F("error\r\n"));

  return t;
}

// Timer1 interrupt handler for sleep throb
ISR(TIMER1_OVF_vect, ISR_NOBLOCK) {
  // Sine table contains only first half...reflect for second half...
  analogWrite(led_pin, pgm_read_byte(&sleepTab[
    (sleepPos >= sizeof(sleepTab)) ?
    (sizeof(sleepTab) * 2 - 1 - sleepPos) : sleepPos]));
  if(++sleepPos >= (sizeof(sleepTab) * 2)) sleepPos = 0; // Roll over
  TIFR1 |= TOV1; // Clear Timer1 interrupt flag
}
