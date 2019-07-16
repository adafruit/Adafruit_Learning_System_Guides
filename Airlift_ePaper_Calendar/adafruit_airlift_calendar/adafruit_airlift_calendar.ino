/***************************************************
 * ePaper Tri Color Calendar Demo
 * For use with Adafruit Metro M4 Express Airlift and tricolor e-Paper Display Shield
 * 
 * Adafruit invests time and resources providing this open source code.
 * Please support Adafruit and open source hardware by purchasing
 * products from Adafruit.com!
 * 
 * Written by Dan Cogliano for Adafruit Industries
 * Copyright (c) 2019 Adafruit Industries
 * 
 * Notes: 
 * Update the secrets.h file with your WiFi details and Adafruit IO credentials
 */
#include <time.h>
#include "secrets.h" 
#include <Adafruit_GFX.h>    // Core graphics library
#include <Adafruit_EPD.h>
#include <Adafruit_NeoPixel.h>

#include <Fonts/FreeSans9pt7b.h>
#include <Fonts/FreeSansBold9pt7b.h>

#include <SPI.h>
#include <WiFiNINA.h>

enum dayhighlight {RedCircle, BlackCircle, Bold, None};

// pick one of these options for displaying the current day in the current month

dayhighlight currentday = RedCircle;
//dayhighlight currentday = BlackCircle;
//dayhighlight currentday = Bold;
//dayhighlight currentday = None;
 
// Configure the pins used for the ESP32 connection
#if !defined(SPIWIFI_SS)  // if the wifi definition isnt in the board variant
  // Don't change the names of these #define's! they match the variant ones
  #define SPIWIFI     SPI
  #define SPIWIFI_SS    10  // Chip select pin
  #define SPIWIFI_ACK   7   // a.k.a BUSY or READY pin
  #define ESP32_RESETN  5   // Reset pin
  #define ESP32_GPIO0   -1  // Not connected
#endif

const char *wifi_ssid = WIFI_SSID;
const char *wifi_password = WIFI_PASSWORD;
const char *aio_username = AIO_USERNAME;
const char *aio_key = AIO_KEY;

#define SRAM_CS     8
#define EPD_CS      10
#define EPD_DC      9  
#define EPD_RESET -1
#define EPD_BUSY -1

#define NEOPIXELPIN   40

/* This isfor the 2.7" tricolor EPD */
Adafruit_IL91874 gfx(264, 176 ,EPD_DC, EPD_RESET, EPD_CS, SRAM_CS, EPD_BUSY);

WiFiSSLClient client;

Adafruit_NeoPixel neopixel = Adafruit_NeoPixel(1, NEOPIXELPIN, NEO_GRB + NEO_KHZ800);


struct tm *today;
struct tm *pickdate = new struct tm;

int8_t readButtons(void) {
  uint16_t reading = analogRead(A3);
  //Serial.println(reading);

  if (reading > 600) {
    return 0; // no buttons pressed
  }
  if (reading > 400) {
    return 4; // button D pressed
  }
  if (reading > 250) {
    return 3; // button C pressed
  }
  if (reading > 125) {
    return 2; // button B pressed
  }
  return 1; // Button A pressed
}

bool isLeapYear(int year) {
  if (((year % 4 == 0) && (year % 100 != 0)) || (year % 400 == 0))
    return true;
  return false;
}

int getDaysInMonth(int month, int year) {
  int daysInMonth[12] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
  if (month != 2)
    return daysInMonth[(month-1)%12];
  if(isLeapYear(year))
    return 29;
  return 28;
}

int getDayOfWeek(int year, int month, int day)
{
  uint16_t months[] = {
    0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365         };   // days until 1st of month

  uint32_t days = year * 365;        // days until year 
  for (uint16_t i = 4; i < year; i += 4) if (isLeapYear(i) ) days++;     // adjust leap years, test only multiple of 4 of course

  days += months[month-1] + day;    // add the days of this year
  if ((month > 2) && isLeapYear(year)) days++;  // adjust 1 if this year is a leap year, but only after febr

  // make Sunday 0
  days--;
  if(days < 0)
    days+= 7;
  return days % 7;   // remove all multiples of 7
}

void drawCalendar(struct tm * today, struct tm * pickdate)
{
  char *dows[7] = {"Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"};
  char *months[12] = {"January","February","March","April","May","June","July","August","September","October","November","December"};

  pickdate->tm_wday = getDayOfWeek(pickdate->tm_year,pickdate->tm_mon,pickdate->tm_mday);

  Serial.println("drawing calendar for " + String(months[pickdate->tm_mon-1]) + " " + String(pickdate->tm_year));
  neopixel.setPixelColor(0, neopixel.Color(0, 255, 0));
  neopixel.show();
  
  // draw calendar
  String stryear = String(pickdate->tm_year);
  gfx.powerUp();
  gfx.clearBuffer();
  //gfx.setFont(&FreeSans9pt7b);
  gfx.setFont();
  gfx.setTextColor(EPD_BLACK);
  gfx.setCursor(8,4);
  gfx.print(stryear);
  
  String strmonth = months[pickdate->tm_mon-1];

  int daysinmonth = getDaysInMonth(pickdate->tm_mon,pickdate->tm_year);
  gfx.setTextColor(EPD_BLACK);
  gfx.setFont(&FreeSansBold9pt7b);
  int16_t fx, fy;
  uint16_t w, h;
  gfx.getTextBounds((char *)strmonth.c_str(), 0,0, &fx, &fy, &w, &h);

  gfx.setCursor((gfx.width() - w)/2,14);
  gfx.print(strmonth);
  
  int curday = pickdate->tm_mday - pickdate->tm_wday;
  while(curday > 1)
    curday -= 7;

  int x = 0;
  int y = 26;
  for(int i = 0 ; i < 7; i++)
  {
    x = 4 + i * (gfx.width()-8)/7;
    gfx.setTextColor(EPD_BLACK);
    gfx.setFont();
    gfx.getTextBounds(String(dows[i]).substring(0,3), 0,0, &fx, &fy, &w, &h);
    gfx.setCursor(x + (gfx.width()/7-w)/2, y-8);
    gfx.print(String(dows[i]).substring(0,3));
  }
  gfx.drawLine(0,27,gfx.width(),27,EPD_BLACK);
  y = 45;
  while(curday <= daysinmonth)
  {
    for(int i = 0; i < 7; i++)
    {
      x = 4 + i * (gfx.width()-8)/7;
      if(curday >= 1 && curday <= daysinmonth)
      {
          gfx.setCursor(x,y);
          gfx.setTextColor(EPD_BLACK);
          gfx.setFont(&FreeSans9pt7b);          
          int16_t fx, fy;
          uint16_t w, h;
          String strday = String(curday);
          if((today->tm_year == pickdate->tm_year) &&
            (today->tm_mon == pickdate->tm_mon) &&
            (curday == pickdate->tm_mday))
          {
            if(currentday != None)
            {
              gfx.setFont(&FreeSansBold9pt7b);           
            }
            if(currentday == BlackCircle)
            {
              gfx.setTextColor(EPD_INVERSE);
              gfx.fillCircle(x + (gfx.width()-8)/7/2, y, 16, EPD_BLACK);  
            }
            else if(currentday == RedCircle)
            {
              gfx.setTextColor(EPD_RED);
              gfx.fillCircle(x + (gfx.width()-8)/7/2, y, 16, EPD_RED);              
            }
          }
          gfx.getTextBounds(strday.c_str(), 0,0, &fx, &fy, &w, &h);
          gfx.setCursor(x+(gfx.width()-8)/7/2-w/2-fx,y+h/2);
          gfx.setColorBuffer(1, true);  // red is inverted
          gfx.print(curday);
          gfx.setColorBuffer(1, false);  // red is not inverted
      }
      curday++;
    }
    y += 24;
  }
  gfx.display();
  Serial.println("display update completed");
  gfx.powerDown();
  neopixel.setPixelColor(0, neopixel.Color(0, 0, 0));
  neopixel.show(); 
}

#define SERVER "io.adafruit.com"
#define PATH "/api/v2/%s/integrations/time/strftime?x-aio-key=%s"
// our strftime is %Y-%m-%d %H:%M:%S.%L %j %u %z %Z see http://strftime.net/ for decoding details
// See https://apidock.com/ruby/DateTime/strftime for full options
#define TIME_SERVICE_STRFTIME "&fmt=%25Y-%25m-%25d+%25H%3A%25M%3A%25S.%25L+%25j+%25u+%25z+%25Z"

struct tm *getDate(bool force = false)
{
  static tm date;
  char buff[500];
  char pathbuff[500];
  sprintf(pathbuff, PATH,aio_username, aio_key);
  String path = String(pathbuff) + String(TIME_SERVICE_STRFTIME);
  //Serial.println(String("path to check: " ) + String(SERVER) + path);
  wget(SERVER, path.c_str(), 443, buff);
  Serial.println("wget got: " + String(buff));
  String datestr = String(buff);
  date.tm_year = atoi(datestr.substring(0,4).c_str());
  date.tm_mon = atoi(datestr.substring(5,7).c_str());
  date.tm_mday = atoi(datestr.substring(8,10).c_str());
  date.tm_wday = atoi(datestr.substring(28,29).c_str());
  date.tm_hour = atoi(datestr.substring(11,13).c_str());
  date.tm_min = atoi(datestr.substring(14,16).c_str());
  date.tm_sec = atoi(datestr.substring(17,19).c_str());
  return &date;
}

void *wget(const char *host, const char *path, int port, char *buff)
{
  neopixel.setPixelColor(0, neopixel.Color(0, 0, 255));
  neopixel.show(); 
  if (client.connect(host, port)) {
    Serial.println("connected to server");
    // Make a HTTP request:
    // Using HTTP/1.1 to avoid "Transfer-Encoding: chunked" reply
    client.println(String("GET ") + path + String(" HTTP/1.0"));
    client.println("Host: " + String(host));
    client.println("Connection: close");
    client.println();

    uint32_t bytes = 0;
    int capturepos = 0;
    bool capture = false;
    int linelength = 0;
    char lastc = '\0';
    while(true) 
    {
      while (client.available()) {
        char c = client.read();
        if((c == '\n') && (lastc == '\r'))
        {
          if(linelength == 0)
          {
            capture = true;
          }
          linelength = 0;
        }
        else if(capture)
        {
          buff[capturepos++] = c;
          //Serial.write(c);
        }
        else
        {
          if((c != '\n') && (c != '\r'))
            linelength++;
        }
        lastc = c;
        bytes++;
      }
    
      // if the server's disconnected, stop the client:
      if (!client.connected()) {
        //Serial.println();
        Serial.println("disconnecting from server.");
        client.stop();
        buff[capturepos] = '\0';
        Serial.println("read " + String(bytes) + " bytes");
        Serial.println("captured " + String(capturepos) + " bytes");
        break;
      }
    }
  }
  neopixel.setPixelColor(0, neopixel.Color(0, 0, 0));
  neopixel.show(); 
}

void setup() {
  Serial.begin(115200);
  //while(!Serial);
  delay(2000);
  Serial.println("Adafruit Airlift ePaper Calendar");
    
  neopixel.begin();
  neopixel.show();
  
  Serial.print("Connecting to WiFi ");

  WiFi.setPins(SPIWIFI_SS, SPIWIFI_ACK, ESP32_RESETN, ESP32_GPIO0, &SPIWIFI);

  // check for the WiFi module:
  while (WiFi.status() == WL_NO_MODULE) {
    Serial.println("Communication with WiFi module failed!");
    // slow red blink
    while(1)
    {
      neopixel.setPixelColor(0, neopixel.Color(255, 0, 0));
      neopixel.show(); 
      delay(900);
      neopixel.setPixelColor(0, neopixel.Color(0, 0, 0));
      neopixel.show(); 
      delay(100);      
    }
  }

  String fv = WiFi.firmwareVersion();
  if (fv < "1.0.0") {
    Serial.println("Please upgrade the firmware");
  }

  neopixel.setPixelColor(0, neopixel.Color(0, 0, 255));
  neopixel.show(); 
  if(WiFi.begin(wifi_ssid, wifi_password) == WL_CONNECT_FAILED)
  {
    Serial.println("WiFi connection failed!");
    // fast red blink
    while(1)
    {
      neopixel.setPixelColor(0, neopixel.Color(255, 0, 0));
      neopixel.show(); 
      delay(400);
      neopixel.setPixelColor(0, neopixel.Color(0, 0, 0));
      neopixel.show(); 
      delay(100);      
    }    
  }

  int wifitimeout = 15;
  while (WiFi.status() != WL_CONNECTED && wifitimeout > 0) {
    delay(900);
    Serial.print(".");
    neopixel.setPixelColor(0, neopixel.Color(0, 0, 80));
    neopixel.show();
    delay(100);
    wifitimeout--;
  }
  if(wifitimeout == 0)
  {
    Serial.println("WiFi connection failed!");
    // fast red blink
    while(1)
    {
      neopixel.setPixelColor(0, neopixel.Color(255, 0, 0));
      neopixel.show(); 
      delay(400);
      neopixel.setPixelColor(0, neopixel.Color(0, 0, 0));
      neopixel.show(); 
      delay(100);      
    }    

  }
  neopixel.setPixelColor(0, neopixel.Color(0, 0, 0));
  neopixel.show(); 
  Serial.println("Connected to wifi");
  gfx.begin();
  Serial.println("ePaper display initialized");
  gfx.clearBuffer();
  gfx.setRotation(2);

  today = getDate();
  Serial.println("today is " + String(today->tm_mon) + "/" + String(today->tm_mday) + "/" + String(today->tm_year));
  pickdate->tm_year = today->tm_year;
  pickdate->tm_mon = today->tm_mon;
  pickdate->tm_mday = today->tm_mday;
  pickdate->tm_hour = today->tm_hour;
  pickdate->tm_min = today->tm_min;
  pickdate->tm_sec = today->tm_sec;
  drawCalendar(today,pickdate);

}

void loop() {
  static uint32_t timer = millis();
  static uint8_t lastbutton = 2;
  static uint8_t direction = 1;
  if(millis() > (timer + 1000*60*60))
  {
    timer = millis();
    // update date once an hour
    today = getDate();
    if(lastbutton == 2)
    {
      // refresh calendar of current month in case date has since changed.
      Serial.println("Refreshing calendar display");
      today = getDate();
      pickdate->tm_year = today->tm_year;
      pickdate->tm_mon = today->tm_mon;
      pickdate->tm_mday = today->tm_mday;
      drawCalendar(today,pickdate);        
    }
  }
  int button = readButtons();
  if (button == 0) {
    return;
  }
  Serial.print("Button "); Serial.print(button); Serial.println(" pressed");
  if (button == 1) {
    Serial.println("Previous month");
    direction = -1;
    pickdate->tm_mday = 1;
    pickdate->tm_mon--;
    if(pickdate->tm_mon < 1)
    {
      pickdate->tm_mon = 12;
      pickdate->tm_year--;
    }
    drawCalendar(today,pickdate);
    lastbutton = 1;
  }

  if (button == 2) {
    Serial.println("Current month");
    direction = 1;
    pickdate->tm_year = today->tm_year;
    pickdate->tm_mon = today->tm_mon;
    pickdate->tm_mday = today->tm_mday;
    pickdate->tm_hour = today->tm_hour;
    pickdate->tm_min = today->tm_min;
    pickdate->tm_sec = today->tm_sec;
    drawCalendar(today,pickdate);
    lastbutton = 2;
  }

  if (button == 3) {
    Serial.println("Next month");
    direction = 1;
    pickdate->tm_mday = 1;
    pickdate->tm_mon++;
    if(pickdate->tm_mon > 12)
    {
      pickdate->tm_mon = 1;
      pickdate->tm_year++;
    }
    drawCalendar(today,pickdate);
    lastbutton = 3;
  }

  if (button == 4) {
    if(direction >= 0)
        Serial.println("Next year");
    else
      Serial.println("Previous year");

    // next or previous year, depending on previous button press
    pickdate->tm_year = pickdate->tm_year + direction;      
    drawCalendar(today,pickdate);
    lastbutton = 3;
  }

  // wait until button is released
  while (readButtons()) {
    delay(10);
  }

}
