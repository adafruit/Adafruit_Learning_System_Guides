/*
  TFT SPI Flash Server - Example WebServer with internal SPI flash storage
    for Adafruit ESP32-S2 TFT Feather

  Copyright (c) 2015 Hristo Gochkov. All rights reserved.
  This file is part of the WebServer library for Arduino environment.

  This library is free software; you can redistribute it and/or
  modify it under the terms of the GNU Lesser General Public
  License as published by the Free Software Foundation; either
  version 2.1 of the License, or (at your option) any later version.

  This library is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
  Lesser General Public License for more details.

  You should have received a copy of the GNU Lesser General Public
  License along with this library; if not, write to the Free Software
  Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
*/

#include <WiFi.h>
#include <WiFiClient.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <SPI.h>
#include "SdFat.h"
#include "Adafruit_SPIFlash.h"
#include "Adafruit_TinyUSB.h"
#include <Adafruit_ST7789.h> 
#include <Fonts/FreeSans9pt7b.h>
#include <ArduinoJson.h>

const char *secrets_filename = "secrets.json";

#define DEFAULT_SSID "MY_SSID"
char ssid[80] = DEFAULT_SSID;

#define DEFAULT_PASSWORD "MY_PASSWORD"
char password[80] = DEFAULT_PASSWORD;

#define DEFAULT_AP "MY_AP"
char ap[80] = DEFAULT_SSID;

#define DEFAULT_AP_PASSWORD "MY_AP_PASSWORD"
char ap_password[80] = DEFAULT_PASSWORD;

#define DEFAULT_HOSTNAME "esp32sd"
char hostname[80] = DEFAULT_HOSTNAME;

StaticJsonDocument<512> doc;

#define EXPOSE_FS_ON_MSD
volatile bool fs_changed = false;

#define DBG_OUTPUT_PORT Serial
Adafruit_ST7789 display = Adafruit_ST7789(TFT_CS, TFT_DC, TFT_RST);

Adafruit_FlashTransport_ESP32 flashTransport;  // internal SPI flash access
Adafruit_SPIFlash flash(&flashTransport); 
FatFileSystem fatfs;  // file system object from SdFat

#if defined(EXPOSE_FS_ON_MSD)
// USB Mass Storage object
Adafruit_USBD_MSC usb_msc;
#endif

WebServer server(80);



void setup(void) {    
#if !defined(EXPOSE_FS_ON_MSD)  
  DBG_OUTPUT_PORT.begin(115200);
  while (!DBG_OUTPUT_PORT) delay(10);
  delay(1000);
#endif

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

  char *projectname = "WordGuesser!";
  for (uint i=0; i<strlen(projectname); i++) {
    if (i % 3 == 0) display.setTextColor(ST77XX_GREEN);
    if (i % 3 == 1) display.setTextColor(ST77XX_YELLOW);
    if (i % 3 == 2) display.setTextColor(ST77XX_BLUE);
    display.print(projectname[i]);
  }

  display.setFont(&FreeSans9pt7b);
  display.setTextSize(1);
  display.setTextColor(ST77XX_WHITE); 
  display.setCursor(0, 40);
  
  if (!flash.begin()) {
    DBG_OUTPUT_PORT.println("failed to load flash");
    display.setTextColor(ST77XX_RED);
    display.println("Failed to load flash");
    while (1) yield();
  }

#if defined(EXPOSE_FS_ON_MSD)
  // Set disk vendor id, product id and revision with string up to 8, 16, 4 characters respectively
  usb_msc.setID("Adafruit", "External Flash", "1.0");

  // Set callback
  usb_msc.setReadWriteCallback(msc_read_cb, msc_write_cb, msc_flush_cb);

  // Set disk size, block size should be 512 regardless of spi flash page size
  usb_msc.setCapacity(flash.size()/512, 512);

  // MSC is ready for read/write
  usb_msc.setUnitReady(true);
  
  usb_msc.begin();
#endif

  // Init file system on the flash
  fatfs.begin(&flash);

  DBG_OUTPUT_PORT.begin(115200);
  DBG_OUTPUT_PORT.setDebugOutput(true);
  DBG_OUTPUT_PORT.println("Adafruit TinyUSB Mass Storage External Flash example");
  DBG_OUTPUT_PORT.print("JEDEC ID: 0x"); 
  DBG_OUTPUT_PORT.println(flash.getJEDECID(), HEX);
  DBG_OUTPUT_PORT.print("Flash size: "); 
  DBG_OUTPUT_PORT.print(flash.size() / 1024); 
  DBG_OUTPUT_PORT.println(" KB");
  DBG_OUTPUT_PORT.print("\n");
  //display.print("Flash size: ");
  //display.print(flash.size() / 1024);
  //display.println(" KB");
  
  File root, file;
  if (root.open("/") )  {
    DBG_OUTPUT_PORT.println("Flash contents:");
  
    // Open next file in root.
    // Warning, openNext starts at the current directory position
    // so a rewind of the directory may be required.
    while ( file.openNext(&root, O_RDONLY) )
    {
      file.printFileSize(&DBG_OUTPUT_PORT);
      DBG_OUTPUT_PORT.write(' ');
      file.printName(&DBG_OUTPUT_PORT);
      if ( file.isDir() )
      {
        // Indicate a directory.
        DBG_OUTPUT_PORT.write('/');
      }
      DBG_OUTPUT_PORT.println();
      file.close();
    }
  
    root.close();
    DBG_OUTPUT_PORT.println();
  }

  parseSecrets();

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  DBG_OUTPUT_PORT.print("Connecting to ");
  DBG_OUTPUT_PORT.println(ssid);
    
  // Wait for connection
  uint8_t i = 0;
  while ((WiFi.status() != WL_CONNECTED) && (i++ < 20)) { //wait 10 seconds
    delay(500);
  }
  if (i == 21) {
    DBG_OUTPUT_PORT.print("Could not connect to");
    DBG_OUTPUT_PORT.println(ssid);
    display.print("Couldnt connect to ");
    display.println(ssid);
  
    // try making access point
    WiFi.mode(WIFI_AP);
    display.print("AP: ");
    display.print(ap);
    display.print(" / ");
    display.println(ap_password);
    WiFi.softAP(ap, ap_password);
    IPAddress myIP = WiFi.softAPIP();
    DBG_OUTPUT_PORT.print("IP address: ");
    DBG_OUTPUT_PORT.println(myIP);
    display.print("IP addr: ");
    display.println(myIP);
  } else {
    display.print("Connected to ");
    display.println(ssid);
    DBG_OUTPUT_PORT.print("Connected! IP address: ");
    DBG_OUTPUT_PORT.println(WiFi.localIP());
    display.print("IP addr: ");
    display.println(WiFi.localIP());
  }
    
  if (MDNS.begin(hostname)) {
    MDNS.addService("http", "tcp", 80);
    DBG_OUTPUT_PORT.println("MDNS responder started");
    DBG_OUTPUT_PORT.print("You can now connect to http://");
    DBG_OUTPUT_PORT.print(hostname);
    DBG_OUTPUT_PORT.println(".local");
    display.print("mDNS: ");
    display.print(hostname);
    display.println(".local");
  }

  server.on("/list", HTTP_GET, printDirectory);
  server.onNotFound(handleNotFound);

  server.begin();
  DBG_OUTPUT_PORT.println("HTTP server started");

}

void loop(void) {
  server.handleClient();
  delay(2);//allow the cpu to switch to other tasks
}



// Callback invoked when received READ10 command.
// Copy disk's data to buffer (up to bufsize) and 
// return number of copied bytes (must be multiple of block size) 
int32_t msc_read_cb (uint32_t lba, void* buffer, uint32_t bufsize)
{
  // Note: SPIFLash Block API: readBlocks/writeBlocks/syncBlocks
  // already include 4K sector caching internally. We don't need to cache it, yahhhh!!
  return flash.readBlocks(lba, (uint8_t*) buffer, bufsize/512) ? bufsize : -1;
}

// Callback invoked when received WRITE10 command.
// Process data in buffer to disk's storage and 
// return number of written bytes (must be multiple of block size)
int32_t msc_write_cb (uint32_t lba, uint8_t* buffer, uint32_t bufsize)
{
  digitalWrite(LED_BUILTIN, HIGH);

  // Note: SPIFLash Block API: readBlocks/writeBlocks/syncBlocks
  // already include 4K sector caching internally. We don't need to cache it, yahhhh!!
  return flash.writeBlocks(lba, buffer, bufsize/512) ? bufsize : -1;
}

// Callback invoked when WRITE10 command is completed (status received and accepted by host).
// used to flush any pending cache.
void msc_flush_cb (void)
{
  // sync with flash
  flash.syncBlocks();

  // clear file system's cache to force refresh
  fatfs.cacheClear();

  fs_changed = true;

  digitalWrite(LED_BUILTIN, LOW);
}



bool parseSecrets() {
  // open file for parsing
  File secretsFile = fatfs.open(secrets_filename);
  if (!secretsFile) {
    DBG_OUTPUT_PORT.println("ERROR: Could not open secrets.json file for reading!");
    return false;
  }

  // check if we can deserialize the secrets.json file
  DeserializationError err = deserializeJson(doc, secretsFile);
  if (err) {
    DBG_OUTPUT_PORT.println("ERROR: deserializeJson() failed with code ");
    DBG_OUTPUT_PORT.println(err.c_str());

    return false;
  }

  // next, we detect the network interface from the `secrets.json`
  DBG_OUTPUT_PORT.println("Attempting to find network interface...");
  strlcpy(ssid, doc["ssid"] | DEFAULT_SSID, sizeof(ssid));
  strlcpy(password, doc["password"] | DEFAULT_PASSWORD, sizeof(password));
  strlcpy(ap, doc["ap"] | DEFAULT_AP, sizeof(ap));
  strlcpy(ap_password, doc["ap_password"] | DEFAULT_AP_PASSWORD, sizeof(ap_password));
  strlcpy(hostname, doc["hostname"] | DEFAULT_HOSTNAME, sizeof(hostname));
       
  // close the tempFile
  secretsFile.close();
  return true;
}


void returnOK() {
  server.send(200, "text/plain", "");
}

void returnFail(String msg) {
  server.send(500, "text/plain", msg + "\r\n");
}

bool loadFromFlash(String path) {
  String dataType = "text/plain";
  if (path.endsWith("/")) {
    path += "index.html";
  }

  if (path.endsWith(".src")) {
    path = path.substring(0, path.lastIndexOf("."));
  } else if (path.endsWith(".htm")) {
    dataType = "text/html";
  } else if (path.endsWith(".html")) {
    dataType = "text/html";
  } else if (path.endsWith(".css")) {
    dataType = "text/css";
  } else if (path.endsWith(".js")) {
    dataType = "application/javascript";
  } else if (path.endsWith(".png")) {
    dataType = "image/png";
  } else if (path.endsWith(".gif")) {
    dataType = "image/gif";
  } else if (path.endsWith(".jpg")) {
    dataType = "image/jpeg";
  } else if (path.endsWith(".ico")) {
    dataType = "image/x-icon";
  } else if (path.endsWith(".xml")) {
    dataType = "text/xml";
  } else if (path.endsWith(".pdf")) {
    dataType = "application/pdf";
  } else if (path.endsWith(".zip")) {
    dataType = "application/zip";
  }

  DBG_OUTPUT_PORT.print(path.c_str());
  
  if (! fatfs.exists(path.c_str())) {
    DBG_OUTPUT_PORT.println("..doesnt exist?");
    return false;
  }
  
  File dataFile = fatfs.open(path.c_str());
  if (! dataFile) {
    DBG_OUTPUT_PORT.println("..couldn't open?");
    return false;
  }
  
  if (dataFile.isDir()) {
    path += "/index.html";
    dataType = "text/html";
    dataFile = fatfs.open(path.c_str());
  }


  if (server.hasArg("download")) {
    dataType = "application/octet-stream";
  }

  if (server.streamFile(dataFile, dataType) != dataFile.size()) {
    DBG_OUTPUT_PORT.println("Sent less data than expected!");
  }

  dataFile.close();
  return true;
}


void printDirectory() {
  if (!server.hasArg("dir")) {
    return returnFail("BAD ARGS");
  }
  String path = server.arg("dir");
  if (path != "/" && !fatfs.exists((char *)path.c_str())) {
    return returnFail("BAD PATH");
  }
  File dir = fatfs.open((char *)path.c_str());
  path = String();
  if (!dir.isDir()) {
    dir.close();
    return returnFail("NOT DIR");
  }
  dir.rewindDirectory();
  server.setContentLength(CONTENT_LENGTH_UNKNOWN);
  server.send(200, "text/json", "");
  WiFiClient client = server.client();

  server.sendContent("[");
  for (int cnt = 0; true; ++cnt) {
    File entry;
    if (!entry.openNext(&dir, O_RDONLY)) {
      break;
    }

    String output;
    if (cnt > 0) {
      output = ',';
    }

    output += "{\"type\":\"";
    output += (entry.isDir()) ? "dir" : "file";
    output += "\",\"name\":\"";
    
    //output += entry.path();
    output += "\"";
    output += "}";
    server.sendContent(output);
    entry.close();
  }
  server.sendContent("]");
  dir.close();
}

void handleNotFound() {
  if (loadFromFlash(server.uri())) {
    return;
  }
  String message = "Internal Flash Not Detected\n\n";
  message += "URI: ";
  message += server.uri();
  message += "\nMethod: ";
  message += (server.method() == HTTP_GET) ? "GET" : "POST";
  message += "\nArguments: ";
  message += server.args();
  message += "\n";
  for (uint8_t i = 0; i < server.args(); i++) {
    message += " NAME:" + server.argName(i) + "\n VALUE:" + server.arg(i) + "\n";
  }
  server.send(404, "text/plain", message);
  DBG_OUTPUT_PORT.print(message);
}
