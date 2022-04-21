// SPDX-FileCopyrightText: 2022 s60sc with changes by ladyada
// SPDX-License-Identifier: GPL-3.0-or-later

 /*
   ESP32_AdBlocker acts as a DNS Sinkhole by returning 0.0.0.0 for any domain names in its blocked list, 
   else forwards to an external DNS server to resolve IP addresses. This prevents content being retrieved 
   from or sent to blocked domains. Searches generally take <200us.

   To use ESP32_AdBlocker, enter its IP address in place of the DNS server IPs in your router/devices.
   Currently it does have an IPv6 address and some devices use IPv6 by default, so disable IPv6 DNS on 
   your device / router to force it to use IPv4 DNS.

   Blocklist files can downloaded from hosting sites and should either be in HOSTS format 
   or Adblock format (only domain name entries processed)

   arduino-esp32 library DNSServer.cpp modified as custom AdBlockerDNSServer.cpp so that DNSServer::processNextRequest()
   calls checkBlocklist() in ESP32_AdBlocker to check if domain blocked, which returns the relevant IP. 
   Based on idea from https://github.com/rubfi/esphole

   Compile with partition scheme 'No OTA (2M APP/2M SPIFFS)'

   s60sc 2021
*/

#include <WiFi.h>
#include <string>
#include <algorithm>
#include <bits/stdc++.h>
//#include <unordered_map>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
//#include <ESPAsyncWebServer.h> // https://github.com/me-no-dev/ESPAsyncWebServer & https://github.com/me-no-dev/AsyncTCP
#include <Preferences.h>

#include <Adafruit_SPIFlash.h>
#include <Adafruit_TinyUSB.h>
#include <Adafruit_ST7789.h>
#include <Fonts/FreeSans9pt7b.h>

#include "AdBlockerDNSServer.h" // customised


#include "config.h"

//static AsyncWebServer webServer(80);
static DNSServer dnsServer;

//std::unordered_set <std::string> blockSet ; // holds hashed list of blocked domains in memory [too much memory overhead]
std::vector<std::string> blockVec; // holds sorted list of blocked domains in memory
static uint8_t* downloadBuff; // temporary store for ptocessing downloaded blocklist file
static const char* BLOCKLISTFILE = {"/hosts.txt"};
static uint32_t blockCnt, allowCnt = 0;

Adafruit_ST7789 display = Adafruit_ST7789(TFT_CS, TFT_DC, TFT_RST);
Adafruit_FlashTransport_ESP32 flashTransport;  // internal SPI flash access
Adafruit_SPIFlash flash(&flashTransport); 
FatFileSystem fatfs;  // file system object from SdFat

char ssid[80] = DEFAULT_SSID;
char password[80] = DEFAULT_PASSWORD;
char hostname[80] = DEFAULT_HOSTNAME;
char hostfile[255] = DEFAULT_HOSTFILE;


bool init_filesystem(void);
bool parseSecrets();

static float inline inKB(size_t inVal) {
  return (float)(inVal / 1024.0);
}

void setup() {
#if !defined(EXPOSE_FS_ON_MSD)  
  DBG_OUTPUT_PORT.begin(115200);
  while (!DBG_OUTPUT_PORT) delay(10);
  delay(1000);
#endif

  if (!flash.begin()) {
    DBG_OUTPUT_PORT.println("failed to load flash");
    display.setTextColor(ST77XX_RED);
    display.println("Failed to load flash");
    while (1) yield();
  }  

  if (! init_filesystem()) {
    DBG_OUTPUT_PORT.printf("Aborting as no filesystem available");
    display.setTextColor(ST77XX_RED);
    display.println("Failed to load filesys");
    while (1) yield();
  }
  
  DBG_OUTPUT_PORT.printf("Sketch size %0.1fKB, PSRAM %s available\n", inKB(ESP.getSketchSize()), (psramFound()) ? "IS" : "NOT");


  // turn on TFT by default
  pinMode(TFT_I2C_POWER, OUTPUT);
  digitalWrite(TFT_I2C_POWER, HIGH);
  pinMode(TFT_BACKLITE, OUTPUT);
  digitalWrite(TFT_BACKLITE, LOW);
  delay(10);
  display.init(135, 240);           // Init ST7789 240x135
  display.setRotation(3);
  display.fillScreen(ST77XX_BLACK);
  digitalWrite(TFT_BACKLITE, HIGH);

  display.setTextColor(ST77XX_WHITE); 
  display.setCursor(0, 0);
  display.setTextSize(3);
  display.print("ESPHole");

  display.setFont(&FreeSans9pt7b);
  display.setTextSize(1);
  display.setTextColor(ST77XX_WHITE); 
  display.setCursor(0, 40);


  parseSecrets();  
  startWifi();
  getNTP();

  bool haveBlocklist = fatfs.exists(BLOCKLISTFILE);
  if (!haveBlocklist) {
    DBG_OUTPUT_PORT.println("No blocklist stored, need to download ...");
    display.println("Downloading blocklist");
    if (downloadFile()) 
      haveBlocklist = createBlocklist();
  } else {
    haveBlocklist = loadBlocklist();
  }

  if (haveBlocklist) {
    // DNS server startup
    dnsServer.setErrorReplyCode(DNSReplyCode::ServerFailure);
    if (dnsServer.start(DNS_PORT, "*", WiFi.localIP())) {
      DBG_OUTPUT_PORT.printf("\nDNS Server started on %s:%d\n", WiFi.localIP().toString().c_str(), DNS_PORT);
    } else {
      puts("Aborting as DNS Server not running");
      return;
    }
  } else {
    puts("Aborting as no resources available");
    return;
  }
  DBG_OUTPUT_PORT.printf("Free DRAM: %0.1fKB, Free PSRAM: %0.1fKB\n*** Ready...\n\n", inKB(ESP.getFreeHeap()), inKB(ESP.getFreePsram()));
}

uint32_t timestamp = 0;
void loop() {
  dnsServer.processNextRequest();
  if (((timestamp + 2000) < millis()) || (timestamp > millis())){
    Serial.print(".");
    timestamp = millis();
#if !defined(DEBUG_ESP_DNS)
    display.setFont(&FreeSans9pt7b);
    display.setTextSize(2);
    display.setTextColor(ST77XX_RED);
    display.fillRect(0, 90, 240, 55, ST77XX_BLACK);
    display.setCursor(0, 118);
    display.print(blockCnt);
    display.println(" Nahs!");
#endif

  }
  //checkAlarm();
}

static void startWifi() {
  WiFi.mode(WIFI_AP_STA);
  DBG_OUTPUT_PORT.printf("Connecting to SSID: %s\n", ssid);
  //WiFi.config(ADBLOCKER, GATEWAY, SUBNET, RESOLVER);
  WiFi.begin(ssid, password);
  display.print("Conn'ing to ");
  display.print(ssid);
  display.print("...");
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    DBG_OUTPUT_PORT.printf(".");
  }
  DBG_OUTPUT_PORT.println("");

  display.println("OK!");
  DBG_OUTPUT_PORT.print("Connected! IP address: ");
  DBG_OUTPUT_PORT.println(WiFi.localIP());
  display.print("IP addr: ");
  display.println(WiFi.localIP());
}

IPAddress checkBlocklist(const char* domainName) {
  // called from ESP32_DNSServer
  IPAddress ip = IPAddress(0, 0, 0, 0); // IP to return for blocked domain
  if (strlen(domainName)) {
    uint64_t uselapsed = micros();
    // search for domain in blocklist
    //bool blocked = (blockSet.find(std::string(domainName)) == blockSet.end()) ? false : true;
    bool blocked = binary_search(blockVec.begin(), blockVec.end(), std::string(domainName));
    uint64_t checkTime = micros() - uselapsed;

    uint32_t mselapsed = millis();
    // if not blocked, get IP address for domain from external DNS
    if (!blocked)  WiFi.hostByName(domainName, ip);
    uint32_t resolveTime = millis() - mselapsed;

    
#ifdef DEBUG_ESP_DNS
    display.setFont(&FreeSans9pt7b);
    display.setTextSize(1);
    display.setTextColor(ST77XX_WHITE);
    display.setTextWrap(true);
    display.fillRect(0, 90, 240, 55, ST77XX_BLACK);
    display.setCursor(0, 105);
    display.println(domainName);
#endif
    DBG_OUTPUT_PORT.printf("%s %s in %lluus", (blocked) ? "*Blocked*" : "Allowed", domainName, checkTime);
    if (!blocked) {
      DBG_OUTPUT_PORT.printf(", resolved to %s in %ums\n", ip.toString().c_str(), resolveTime);
#ifdef DEBUG_ESP_DNS
      display.setTextColor(ST77XX_GREEN);
      display.println(ip.toString().c_str());
#endif
    }
    else {
      puts("");
#ifdef DEBUG_ESP_DNS
      display.setTextColor(ST77XX_RED);
      display.println("BLOCKED");
#endif
    }

    if (blocked) blockCnt++;
    else allowCnt++;
  }
  return ip;
}

static bool loadBlocklist() {
  // load blocklist file into memory from storage
  size_t remaining = heap_caps_get_largest_free_block(MALLOC_CAP_8BIT);
  DBG_OUTPUT_PORT.printf("Loading blocklist %s\n", hostfile);
  uint32_t loadTime = millis();
  if (psramFound()) heap_caps_malloc_extmem_enable(5); // force vector into psram
  blockVec.reserve((psramFound()) ? MAX_DOMAINS : 1000);
  if (psramFound()) heap_caps_malloc_extmem_enable(100000);
  
  File file = fatfs.open(BLOCKLISTFILE, FILE_READ);
  if (file) {
    DBG_OUTPUT_PORT.printf("File size %0.1fKB loading into %0.1fKB %s memory ...\n", inKB(file.size()),
      inKB(remaining), (psramFound()) ? "PSRAM" : "DRAM");
    char domainLine[MAX_LINELEN + 1];
    int itemsLoaded = 0;
    if (psramFound()) heap_caps_malloc_extmem_enable(5); // force vector into psram

    while (file.available()) {
      size_t lineLen = file.readBytesUntil('\n', domainLine, MAX_LINELEN);
      if (lineLen) {
        domainLine[lineLen] = 0;
        //blockSet.insert(std::string(domainLine));
        blockVec.push_back(std::string(domainLine));
        itemsLoaded++;
        if (itemsLoaded%500 == 0) { // check memory too often triggers watchdog
          remaining = heap_caps_get_largest_free_block(MALLOC_CAP_8BIT);
          if (remaining < (MIN_MEMORY)) {
            DBG_OUTPUT_PORT.printf("Blocklist truncated to avoid memory overflow, %u bytes remaining\n", remaining);
            break;
          }
        }
        if (itemsLoaded >= MAX_DOMAINS ) {
          // max 64K vectors else esp32 crashes
          DBG_OUTPUT_PORT.printf("Blocklist truncated as maximum number of domains loaded - %u\n", MAX_DOMAINS);
          break;
        }
      }
    }
    file.close();
    //for (int i=0; i < blockVec.size(); i++) DBG_OUTPUT_PORT.printf("%s\n", blockVec.at(i).c_str());

    if (psramFound()) heap_caps_malloc_extmem_enable(100000);
    if (!itemsLoaded) {
      puts("Aborting as empty blocklist read ..."); // SPIFFS issue
      delay(100);
      ESP.restart();
    }
    display.print("Checking ");
    display.print(itemsLoaded);
    display.println(" domains");
      
    DBG_OUTPUT_PORT.printf("Loaded %u domains from blocklist file in %.01f secs\n", itemsLoaded, (float)((millis() - loadTime) / 1000.0));
    return true;
  }
  puts(" - not found");
  return false;
}

static bool sortBlocklist() {
  // read downloaded blocklist from storage, sort in alpha order to allow binary search, rewrite to storage
  free(downloadBuff);
  delay(100);
  if (loadBlocklist()) {
    puts("Sorting blocklist alphabetically ...");
    uint32_t sortTime = millis();
    sort(blockVec.begin(), blockVec.end());
    DBG_OUTPUT_PORT.printf("Sorted blocklist after %0.1f secs, saving to file ...\n", (float)((millis() - sortTime) / 1000.0));
    sortTime = millis();
    std::string previous = "";
    int duplicate = 0;
    
    // rewrite file with sorted domains
    fatfs.remove(BLOCKLISTFILE);
    File file = fatfs.open(BLOCKLISTFILE, FILE_WRITE);
    if (file) {
      for (auto domain : blockVec) {
        if (domain.compare(previous) != 0) {
          // store unduplicated domain
          file.write((uint8_t*)domain.c_str(), strlen(domain.c_str()));
          file.write((uint8_t*)"\n", 1);
          previous.assign(domain);
        } else duplicate++;
      }
      file.close();
      DBG_OUTPUT_PORT.printf("Saved into file removing %u duplicates after %0.1f secs, restarting ...\n", duplicate, (float)((millis() - sortTime) / 1000.0));
      delay(100);
      ESP.restart(); // quicker to restart than clear vector
      return true;
    } else puts ("Failed to write to blocklist file");
  }
  return false;
}

static size_t inline extractDomains() {
  // extract domain names from downloaded blocklist
  size_t downloadBuffPtr = 0;
  char *saveLine, *saveItem = NULL;
  char* tokenLine = strtok_r((char*)downloadBuff, "\n", &saveLine);
  char* tokenItem;

  // for each line
  while (tokenLine != NULL) {
    if (strncmp(tokenLine, "127.0.0.1", 9) == 0 || strncmp(tokenLine, "0.0.0.0", 7) == 0) {
      // HOSTS file format matched, extract domain name
      tokenItem = strtok_r(tokenLine, " \t", &saveItem); // skip over first token
      if (tokenItem != NULL) tokenItem = strtok_r(NULL, " \t", &saveItem); // domain in second token
    } else if (strncmp(tokenLine, "||", 2) == 0)
      tokenItem = strtok_r(tokenLine, "|^", &saveItem); // Adblock format - domain in first token
    else tokenItem = NULL; // no match
    if (tokenItem != NULL) {
      // write processed line back to buffer
      size_t itemLen = strlen(tokenItem);
      int wwwOffset = (strncmp(tokenItem, "www.", 4) == 0) ? 4 : 0;  // remove any leading "www."
      memcpy(downloadBuff + downloadBuffPtr, tokenItem + wwwOffset, itemLen - wwwOffset);
      downloadBuffPtr += itemLen;
      memcpy(downloadBuff + downloadBuffPtr, (uint8_t*)"\n", 1);
      downloadBuffPtr++;
    }
    tokenLine = strtok_r(NULL, "\n", &saveLine);
  }
  downloadBuff[downloadBuffPtr] = 0; // string terminator
  return downloadBuffPtr;
}

static bool createBlocklist() {
  // after blocklist file downloaded, the content is parsed to extract the domain names, then written to storage
  uint32_t createTime = millis();
  size_t blocklistSize = extractDomains();
            
  // check storage space available, else abort
  size_t storageAvailable = flashFreeSpace();
  storageAvailable -= 1024*32; // leave overhead space
  if (storageAvailable < blocklistSize) {
    DBG_OUTPUT_PORT.printf("Aborting as insufficient storage %0.1fKB ...\n", inKB(storageAvailable));
    delay(100);
    ESP.restart();
  }
  DBG_OUTPUT_PORT.printf("Creating extracted unsorted blocklist of %0.1fKB\n", inKB(blocklistSize));


  Serial.println("-----------------------------------------------");
  Serial.println((const char *)downloadBuff);
  Serial.println("-----------------------------------------------");

  File file = fatfs.open(BLOCKLISTFILE, FILE_WRITE);
  if (file) {
    // write buffer to file
    size_t written = file.write(downloadBuff, blocklistSize);
    if (!written) {
      puts("Aborting as blocklist empty after writing ..."); // SPIFFS issue
      delay(100);
      ESP.restart();
    }
    file.close();
    DBG_OUTPUT_PORT.printf("Blocklist file of %0.1fKB created in %.01f secs\n", inKB(written), (float)((millis() - createTime) / 1000.0));
    return (sortBlocklist());
  } else DBG_OUTPUT_PORT.printf("Failed to store blocklist %s\n", BLOCKLISTFILE);
  free(downloadBuff);
  return false;
}

static bool downloadFile() {
  size_t downloadBuffPtr = 0;
  WiFiClientSecure *client = new WiFiClientSecure;
  if (!client) {
    puts("Failed to create secure client");
    return false;
  } else {
    // scoping block
    {
      client->setInsecure(); // don't use a root cert
      HTTPClient http;
      // open connection to blocklist host
      if (http.begin(*client, hostfile)) {
        DBG_OUTPUT_PORT.printf("Downloading %s\n", hostfile);
        uint32_t loadTime = millis();
        // start connection and send HTTP header
        int httpCode = http.GET();

        if (httpCode > 0) {
          DBG_OUTPUT_PORT.printf("Response code: %d\n", httpCode);
          if (httpCode == HTTP_CODE_OK || httpCode == HTTP_CODE_MOVED_PERMANENTLY) {
            // get length of content (is -1 when Server sends no Content-Length header)
            int len = http.getSize();
            if (len > 0) {
              DBG_OUTPUT_PORT.printf("File size: %0.1fKB", inKB(len));
            }
            else {
              DBG_OUTPUT_PORT.printf("File size unknown");
            }
            size_t availableMem = heap_caps_get_largest_free_block(MALLOC_CAP_8BIT);
            DBG_OUTPUT_PORT.printf(", with %0.1fKB memory available for download ...\n", inKB(availableMem));
            if (len > 0 && len > availableMem) {
              puts("Aborting as file too large");
              delay(100);
              ESP.restart();
            }

            int chunk = 128; // amount to consume per read of stream
            // allocate memory for download buffer
            downloadBuff = (psramFound()) ? (uint8_t*)ps_malloc(availableMem) : (uint8_t*)malloc(availableMem);
            WiFiClient * stream = http.getStreamPtr(); // stream data to client

            while (http.connected() && (len > 0 || len == -1)) {
              size_t streamSize = stream->available();
              if (streamSize) {
                // consume up to chunk bytes and write to memory
                int readc = stream->readBytes(downloadBuff + downloadBuffPtr, ((streamSize > chunk) ? chunk : streamSize));
                downloadBuffPtr += readc;
                if (len > 0) len -= readc;
                if ((downloadBuffPtr + chunk) >= availableMem) {
                  puts("Aborting as file too large");
                  delay(100);
                  ESP.restart();
                }
              }
              delay(1);
            }
            downloadBuff[downloadBuffPtr] = 0; // string terminator
            Serial.println("-----------------------------------------------");
            Serial.println((const char *)downloadBuff);
            Serial.println("-----------------------------------------------");
            DBG_OUTPUT_PORT.printf("Download completed in %0.1f secs, stored %0.1fKB\n", ((millis() - loadTime) / 1000.0), inKB(downloadBuffPtr));
          }
        } else DBG_OUTPUT_PORT.printf("Connection failed with error: %s\n", http.errorToString(httpCode).c_str());
      } else {
        DBG_OUTPUT_PORT.printf("Unable to download %s\n", hostfile);
        delay(100);
        ESP.restart();
      }
      http.end();
    }
    delete client;
  }
  return (downloadBuffPtr) ? true : false;
}


static inline time_t getEpochSecs() {
  struct timeval tv;
  gettimeofday(&tv, NULL);
  return tv.tv_sec;
}

static void getNTP() {
  // get current time from NTP server and apply to ESP32
  const char* ntpServer = "0.adafruit.pool.ntp.org";
  const long gmtOffset_sec = 0;  // offset from GMT
  const int daylightOffset_sec = 3600; // daylight savings offset in secs
  int i = 0;
  do {
    configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
    delay(1000);
  } while (getEpochSecs() < 1000 && i++ < 5); // try up to 5 times
  // set timezone as required
  setenv("TZ", TIMEZONE, 1);
  if (getEpochSecs() > 1000) {
    time_t currEpoch = getEpochSecs();
    char timeFormat[20];
    strftime(timeFormat, sizeof(timeFormat), "%d/%m/%Y %H:%M:%S", localtime(&currEpoch));
    DBG_OUTPUT_PORT.printf("Got current time from NTP: %s\n", timeFormat);
  }
  else puts("Unable to sync with NTP");
}

static void checkAlarm() {
  // once per day at given time, load updated blocklist from host site
  static time_t rolloverEpoch = setAlarm(UPDATE_HOUR);
  if (getEpochSecs() >= rolloverEpoch) { 
    puts("Scheduled restart to load updated blocklist ...");
    delay(100);
    ESP.restart();
  }
}

static time_t setAlarm(uint8_t alarmHour) {
  // calculate future alarm datetime based on current datetime
  struct tm* timeinfo;
  time_t rawtime;
  time(&rawtime);
  timeinfo = localtime(&rawtime);
  // set alarm date & time for next day at given hour
  timeinfo->tm_mday += 1; 
  timeinfo->tm_hour = alarmHour;
  timeinfo->tm_min = 0;
  // return future datetime as epoch seconds
  return mktime(timeinfo);
}
