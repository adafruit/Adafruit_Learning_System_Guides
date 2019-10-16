#include <time.h>
#include <Adafruit_GFX.h>    // Core graphics library
#include <Adafruit_EPD.h>
#include <Adafruit_NeoPixel.h>
#include <ArduinoJson.h>        //https://github.com/bblanchon/ArduinoJson
#include <SPI.h>
#include <WiFiNINA.h>

#include "secrets.h"
#include "OpenWeatherMap.h"

#include "Fonts/meteocons48pt7b.h"
#include "Fonts/meteocons24pt7b.h"
#include "Fonts/meteocons20pt7b.h"
#include "Fonts/meteocons16pt7b.h"

#include "Fonts/moon_phases20pt7b.h"
#include "Fonts/moon_phases36pt7b.h"

#include <Fonts/FreeSans9pt7b.h>
#include <Fonts/FreeSans12pt7b.h>
#include <Fonts/FreeSans18pt7b.h>
#include <Fonts/FreeSansBold12pt7b.h>
#include <Fonts/FreeSansBold24pt7b.h>

#define SRAM_CS     8
#define EPD_CS      10
#define EPD_DC      9  
#define EPD_RESET -1
#define EPD_BUSY -1

#define NEOPIXELPIN   40

// This is for the 2.7" tricolor EPD
Adafruit_IL91874 gfx(264, 176 ,EPD_DC, EPD_RESET, EPD_CS, SRAM_CS, EPD_BUSY);

AirliftOpenWeatherMap owclient(&Serial);
OpenWeatherMapCurrentData owcdata;
OpenWeatherMapForecastData owfdata[3];

Adafruit_NeoPixel neopixel = Adafruit_NeoPixel(1, NEOPIXELPIN, NEO_GRB + NEO_KHZ800);

  const char *moonphasenames[29] = {
    "New Moon",
    "Waxing Crescent",
    "Waxing Crescent",
    "Waxing Crescent",
    "Waxing Crescent",
    "Waxing Crescent",
    "Waxing Crescent",
    "Quarter",
    "Waxing Gibbous",
    "Waxing Gibbous",
    "Waxing Gibbous",
    "Waxing Gibbous",
    "Waxing Gibbous",
    "Waxing Gibbous",
    "Full Moon",
    "Waning Gibbous",
    "Waning Gibbous",
    "Waning Gibbous",
    "Waning Gibbous",
    "Waning Gibbous",
    "Waning Gibbous",
    "Last Quarter",
    "Waning Crescent",
    "Waning Crescent",
    "Waning Crescent",
    "Waning Crescent",
    "Waning Crescent",
    "Waning Crescent",
    "Waning Crescent"
};

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

bool wifi_connect(){
  
  Serial.print("Connecting to WiFi... ");

  WiFi.setPins(SPIWIFI_SS, SPIWIFI_ACK, ESP32_RESETN, ESP32_GPIO0, &SPIWIFI);

  // check for the WiFi module:
  if(WiFi.status() == WL_NO_MODULE) {
    Serial.println("Communication with WiFi module failed!");
    displayError("Communication with WiFi module failed!");
    while(true);
  }

  String fv = WiFi.firmwareVersion();
  if (fv < "1.0.0") {
    Serial.println("Please upgrade the firmware");
  }

  neopixel.setPixelColor(0, neopixel.Color(0, 0, 255));
  neopixel.show(); 
  if(WiFi.begin(WIFI_SSID, WIFI_PASSWORD) == WL_CONNECT_FAILED)
  {
    Serial.println("WiFi connection failed!");
    displayError("WiFi connection failed!");
    return false;
  }

  int wifitimeout = 15;
  int wifistatus; 
  while ((wifistatus = WiFi.status()) != WL_CONNECTED && wifitimeout > 0) {
    delay(1000);
    Serial.print(".");
    wifitimeout--;
  }
  if(wifitimeout == 0)
  {
    Serial.println("WiFi connection timeout with error " + String(wifistatus));
    displayError("WiFi connection timeout with error " + String(wifistatus));
    neopixel.setPixelColor(0, neopixel.Color(0, 0, 0));
    neopixel.show(); 
    return false;
  }
  neopixel.setPixelColor(0, neopixel.Color(0, 0, 0));
  neopixel.show(); 
  Serial.println("Connected");
  return true;
}

void wget(String &url, int port, char *buff)
{
  int pos1 = url.indexOf("/",0);
  int pos2 = url.indexOf("/",8);
  String host = url.substring(pos1+2,pos2);
  String path = url.substring(pos2);
  Serial.println("to wget(" + host + "," + path + "," + port + ")");
  wget(host, path, port, buff);
}

void wget(String &host, String &path, int port, char *buff)
{
  //WiFiSSLClient client;
  WiFiClient client;

  neopixel.setPixelColor(0, neopixel.Color(0, 0, 255));
  neopixel.show();
  client.stop();
  if (client.connect(host.c_str(), port)) {
    Serial.println("connected to server");
    // Make a HTTP request:
    client.println(String("GET ") + path + String(" HTTP/1.0"));
    client.println("Host: " + host);
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
        //Serial.print(c);
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
        Serial.println("captured " + String(capturepos) + " bytes");
        break;
      }
    }
  }
  else
  {
    Serial.println("problem connecting to " + host + ":" + String(port));
    buff[0] = '\0';
  }
  neopixel.setPixelColor(0, neopixel.Color(0, 0, 0));
  neopixel.show(); 
}

int getStringLength(String s)
{
  int16_t  x = 0, y = 0;
  uint16_t w, h;
  gfx.getTextBounds(s, 0, 0, &x, &y, &w, &h);
  return w + x;
}

/*
return value is percent of moon cycle ( from 0.0 to 0.999999), i.e.:

0.0: New Moon
0.125: Waxing Crescent Moon
0.25: Quarter Moon
0.375: Waxing Gibbous Moon
0.5: Full Moon
0.625: Waning Gibbous Moon
0.75: Last Quarter Moon
0.875: Waning Crescent Moon

*/
float getMoonPhase(time_t tdate)
{

  time_t newmoonref = 1263539460; //known new moon date (2010-01-15 07:11)
  // moon phase is 29.5305882 days, which is 2551442.82048 seconds
  float phase = abs( tdate - newmoonref) / (double)2551442.82048;
  phase -= (int)phase; // leave only the remainder
  if(newmoonref > tdate)
  phase = 1 - phase;
  return phase;
}

void displayError(String str)
{
    // show error on display
    neopixel.setPixelColor(0, neopixel.Color(255, 0, 0));
    neopixel.show(); 

    Serial.println(str);

    gfx.setTextColor(EPD_BLACK);
    gfx.powerUp();
    gfx.clearBuffer();
    gfx.setTextWrap(true);
    gfx.setCursor(10,60);
    gfx.setFont(&FreeSans12pt7b);
    gfx.print(str);
    gfx.display();
    neopixel.setPixelColor(0, neopixel.Color(0, 0, 0));
    neopixel.show();
}

void displayHeading(OpenWeatherMapCurrentData &owcdata)
{

  time_t local = owcdata.observationTime + owcdata.timezone;
  struct tm *timeinfo = gmtime(&local);
  char datestr[80];
  // date
  //strftime(datestr,80,"%a, %d %b %Y",timeinfo);
  strftime(datestr,80,"%a, %b %d",timeinfo);
  gfx.setFont(&FreeSans18pt7b);
  gfx.setCursor((gfx.width()-getStringLength(datestr))/2,30);
  gfx.print(datestr);
  
  // city
  strftime(datestr,80,"%A",timeinfo);
  gfx.setFont(&FreeSansBold12pt7b);
  gfx.setCursor((gfx.width()-getStringLength(owcdata.cityName))/2,60);
  gfx.print(owcdata.cityName);
}

void displayForecastDays(OpenWeatherMapCurrentData &owcdata, OpenWeatherMapForecastData owfdata[], int count = 3)
{
  for(int i=0; i < count; i++)
  {
    // day

    time_t local = owfdata[i].observationTime + owcdata.timezone;
    struct tm *timeinfo = gmtime(&local);
    char strbuff[80];
    strftime(strbuff,80,"%I",timeinfo);
    String datestr = String(atoi(strbuff));
    strftime(strbuff,80,"%p",timeinfo);
    // convert AM/PM to lowercase
    strbuff[0] = tolower(strbuff[0]);
    strbuff[1] = tolower(strbuff[1]);
    datestr = datestr + " " + String(strbuff);
    gfx.setFont(&FreeSans9pt7b);
    gfx.setCursor(i*gfx.width()/3 + (gfx.width()/3-getStringLength(datestr))/2,94);
    gfx.print(datestr);
    
    // weather icon
    String wicon = owclient.getMeteoconIcon(owfdata[i].icon);
    gfx.setFont(&meteocons20pt7b);
    gfx.setCursor(i*gfx.width()/3 + (gfx.width()/3-getStringLength(wicon))/2,134);
    gfx.print(wicon);
  
    // weather main description
    gfx.setFont(&FreeSans9pt7b);
    gfx.setCursor(i*gfx.width()/3 + (gfx.width()/3-getStringLength(owfdata[i].main))/2,154);
    gfx.print(owfdata[i].main);

    // temperature
    int itemp = (int)(owfdata[i].temp + .5);
    int color = EPD_BLACK;
    if((OWM_METRIC && itemp >= METRIC_HOT)|| (!OWM_METRIC && itemp >= ENGLISH_HOT))
      color = EPD_RED;
    gfx.setTextColor(color);
    gfx.setFont(&FreeSans9pt7b);
    gfx.setCursor(i*gfx.width()/3 + (gfx.width()/3-getStringLength(String(itemp)))/2,172);
    gfx.print(itemp);
    gfx.drawCircle(i*gfx.width()/3 + (gfx.width()/3-getStringLength(String(itemp)))/2 + getStringLength(String(itemp)) + 6,163,3,color);
    gfx.drawCircle(i*gfx.width()/3 + (gfx.width()/3-getStringLength(String(itemp)))/2 + getStringLength(String(itemp)) + 6,163,2,color); 
    gfx.setTextColor(EPD_BLACK);   
  }  
}

void displayForecast(OpenWeatherMapCurrentData &owcdata, OpenWeatherMapForecastData owfdata[], int count = 3)
{
  gfx.powerUp();
  gfx.clearBuffer();
  neopixel.setPixelColor(0, neopixel.Color(0, 255, 0));
  neopixel.show();  

  gfx.setTextColor(EPD_BLACK);
  displayHeading(owcdata);

  displayForecastDays(owcdata, owfdata, count);
  gfx.display();
  gfx.powerDown();
  neopixel.setPixelColor(0, neopixel.Color(0, 0, 0));
  neopixel.show(); 
}

void displayAllWeather(OpenWeatherMapCurrentData &owcdata, OpenWeatherMapForecastData owfdata[], int count = 3)
{
  gfx.powerUp();
  gfx.clearBuffer();
  neopixel.setPixelColor(0, neopixel.Color(0, 255, 0));
  neopixel.show();  

  gfx.setTextColor(EPD_BLACK);

  // date string
  time_t local = owcdata.observationTime + owcdata.timezone;
  struct tm *timeinfo = gmtime(&local);
  char datestr[80];
  // date
  //strftime(datestr,80,"%a, %d %b %Y",timeinfo);
  strftime(datestr,80,"%a, %b %d %Y",timeinfo);
  gfx.setFont(&FreeSans9pt7b);
  gfx.setCursor((gfx.width()-getStringLength(datestr))/2,14);
  gfx.print(datestr);
  
  // weather icon
  String wicon = owclient.getMeteoconIcon(owcdata.icon);
  gfx.setFont(&meteocons24pt7b);
  gfx.setCursor((gfx.width()/3-getStringLength(wicon))/2,56);
  gfx.print(wicon);

  // weather main description
  gfx.setFont(&FreeSans9pt7b);
  gfx.setCursor((gfx.width()/3-getStringLength(owcdata.main))/2,72);
  gfx.print(owcdata.main);

  // temperature
  gfx.setFont(&FreeSansBold24pt7b);
  int itemp = owcdata.temp + .5;
  int color = EPD_BLACK;
  if((OWM_METRIC && (int)itemp >= METRIC_HOT)|| (!OWM_METRIC && (int)itemp >= ENGLISH_HOT))
    color = EPD_RED;
  gfx.setTextColor(color);
  gfx.setCursor(gfx.width()/3 + (gfx.width()/3-getStringLength(String(itemp)))/2,58);
  gfx.print(itemp);
  gfx.setTextColor(EPD_BLACK);

  // draw temperature degree as a circle (not available as font character
  gfx.drawCircle(gfx.width()/3 + (gfx.width()/3 + getStringLength(String(itemp)))/2 + 8, 58-30,4,color);
  gfx.drawCircle(gfx.width()/3 + (gfx.width()/3 + getStringLength(String(itemp)))/2 + 8, 58-30,3,color);

  // draw moon
  // draw Moon Phase
  float moonphase = getMoonPhase(owcdata.observationTime);
  int moonage = 29.5305882 * moonphase;
  //Serial.println("moon age: " + String(moonage));
  // convert to appropriate icon
  String moonstr = String((char)((int)'A' + (int)(moonage*25./30)));
  gfx.setFont(&moon_phases20pt7b);
  // font lines look a little thin at this size, drawing it a few times to thicken the lines
  gfx.setCursor(2*gfx.width()/3 + (gfx.width()/3-getStringLength(moonstr))/2,56);
  gfx.print(moonstr);  
  gfx.setCursor(2*gfx.width()/3 + (gfx.width()/3-getStringLength(moonstr))/2+1,56);
  gfx.print(moonstr);  
  gfx.setCursor(2*gfx.width()/3 + (gfx.width()/3-getStringLength(moonstr))/2,56-1);
  gfx.print(moonstr);  

  // draw moon phase name
  int currentphase = moonphase * 28. + .5;
  gfx.setFont(); // system font (smallest available)
  gfx.setCursor(2*gfx.width()/3 + max(0,(gfx.width()/3 - getStringLength(moonphasenames[currentphase]))/2),62);
  gfx.print(moonphasenames[currentphase]);


  displayForecastDays(owcdata, owfdata, count);
  gfx.display();
  gfx.powerDown();
  neopixel.setPixelColor(0, neopixel.Color(0, 0, 0));
  neopixel.show(); 
  
}

void displayCurrentConditions(OpenWeatherMapCurrentData &owcdata)
{
  gfx.powerUp();
  gfx.clearBuffer();
  neopixel.setPixelColor(0, neopixel.Color(0, 255, 0));
  neopixel.show();  

  gfx.setTextColor(EPD_BLACK);
  displayHeading(owcdata);

  // weather icon
  String wicon = owclient.getMeteoconIcon(owcdata.icon);
  gfx.setFont(&meteocons48pt7b);
  gfx.setCursor((gfx.width()/2-getStringLength(wicon))/2,156);
  gfx.print(wicon);

  // weather main description
  gfx.setFont(&FreeSans9pt7b);
  gfx.setCursor(gfx.width()/2 + (gfx.width()/2-getStringLength(owcdata.main))/2,160);
  gfx.print(owcdata.main);

  // temperature
  gfx.setFont(&FreeSansBold24pt7b);
  int itemp = owcdata.temp + .5;
  int color = EPD_BLACK;
  if((OWM_METRIC && (int)itemp >= METRIC_HOT)|| (!OWM_METRIC && (int)itemp >= ENGLISH_HOT))
    color = EPD_RED;
  gfx.setTextColor(color);
  gfx.setCursor(gfx.width()/2 + (gfx.width()/2-getStringLength(String(itemp)))/2,130);
  gfx.print(itemp);
  gfx.setTextColor(EPD_BLACK);
  
  // draw temperature degree as a circle (not available as font character
  gfx.drawCircle(gfx.width()/2 + (gfx.width()/2 + getStringLength(String(itemp)))/2 + 10, 130-26,4,color);
  gfx.drawCircle(gfx.width()/2 + (gfx.width()/2 + getStringLength(String(itemp)))/2 + 10, 130-26,3,color);
  
  gfx.display();
  gfx.powerDown();
  neopixel.setPixelColor(0, neopixel.Color(0, 0, 0));
  neopixel.show(); 
}

void displaySunMoon(OpenWeatherMapCurrentData &owcdata)
{
  
  gfx.powerUp();
  gfx.clearBuffer();
  neopixel.setPixelColor(0, neopixel.Color(0, 255, 0));
  neopixel.show();  

  gfx.setTextColor(EPD_BLACK);
  displayHeading(owcdata);

  // draw Moon Phase
  float moonphase = getMoonPhase(owcdata.observationTime);
  int moonage = 29.5305882 * moonphase;
  // convert to appropriate icon
  String moonstr = String((char)((int)'A' + (int)(moonage*25./30)));
  gfx.setFont(&moon_phases36pt7b);
  gfx.setCursor((gfx.width()/3-getStringLength(moonstr))/2,140);
  gfx.print(moonstr);

  // draw moon phase name
  int currentphase = moonphase * 28. + .5;
  gfx.setFont(&FreeSans9pt7b);
  gfx.setCursor(gfx.width()/3 + max(0,(gfx.width()*2/3 - getStringLength(moonphasenames[currentphase]))/2),110);
  gfx.print(moonphasenames[currentphase]);

  // draw sunrise/sunset

  // sunrise/sunset times
  // sunrise

  time_t local = owcdata.sunrise + owcdata.timezone + 30;  // round to nearest minute
  struct tm *timeinfo = gmtime(&local);
  char strbuff[80];
  strftime(strbuff,80,"%I",timeinfo);
  String datestr = String(atoi(strbuff));
  strftime(strbuff,80,":%M %p",timeinfo);
  datestr = datestr + String(strbuff) + " - ";
  // sunset
  local = owcdata.sunset + owcdata.timezone + 30; // round to nearest minute
  timeinfo = gmtime(&local);
  strftime(strbuff,80,"%I",timeinfo);
  datestr = datestr + String(atoi(strbuff));
  strftime(strbuff,80,":%M %p",timeinfo);
  datestr = datestr + String(strbuff);

  gfx.setFont(&FreeSans9pt7b);
  int datestrlen = getStringLength(datestr);
  int xpos = (gfx.width() - datestrlen)/2;
  gfx.setCursor(xpos,166);
  gfx.print(datestr);

  // draw sunrise icon
  // sun icon is "B"
  String wicon = "B";
  gfx.setFont(&meteocons16pt7b);
  gfx.setCursor(xpos - getStringLength(wicon) - 12,174);
  gfx.print(wicon);

  // draw sunset icon
  // sunset icon is "A"
  wicon = "A";
  gfx.setCursor(xpos + datestrlen + 12,174);
  gfx.print(wicon);

  gfx.display();
  gfx.powerDown();
  neopixel.setPixelColor(0, neopixel.Color(0, 0, 0));
  neopixel.show(); 
}

void setup() {
  neopixel.begin();
  neopixel.show();
  
  gfx.begin();
  Serial.println("ePaper display initialized");
  gfx.setRotation(2);
  gfx.setTextWrap(false);

}

void loop() {
  char data[4000];
  static uint32_t timer = millis();
  static uint8_t lastbutton = 1;
  static bool firsttime = true;

  int button = readButtons();
  
  // update weather data at specified interval or when button 4 is pressed
  if((millis() >= (timer + 1000*60*UPDATE_INTERVAL)) || (button == 4) || firsttime)
  {
    Serial.println("getting weather data");
    firsttime = false;
    timer = millis();
    int retry = 6;
    while(!wifi_connect())
    {
      delay(5000);
      retry--;
      if(retry < 0)
      {
        displayError("Can not connect to WiFi, press reset to restart");
        while(1);      
      }
    }
    String urlc = owclient.buildUrlCurrent(OWM_KEY,OWM_LOCATION);
    Serial.println(urlc);
    retry = 6;
    do
    {
      retry--;
      wget(urlc,80,data);
      if(strlen(data) == 0 && retry < 0)
      {
        displayError("Can not get weather data, press reset to restart");
        while(1);      
      }
    }
    while(strlen(data) == 0);
    Serial.println("data retrieved:");
    Serial.println(data);
    retry = 6;
    while(!owclient.updateCurrent(owcdata,data))
    {
      retry--;
      if(retry < 0)
      {
        displayError(owclient.getError());
        while(1);
      }
      delay(5000);
    }
  
    String urlf = owclient.buildUrlForecast(OWM_KEY,OWM_LOCATION);
    Serial.println(urlf);
    wget(urlf,80,data);
    Serial.println("data retrieved:");
    Serial.println(data);
    if(!owclient.updateForecast(owfdata[0],data,0))
    {
      displayError(owclient.getError());
      while(1);
    }
    if(!owclient.updateForecast(owfdata[1],data,2))
    {
      displayError(owclient.getError());
      while(1);
    }
    if(!owclient.updateForecast(owfdata[2],data,4))
    {
      displayError(owclient.getError());
      while(1);
    }

    switch(lastbutton)
    {
      case 1:        
        displayAllWeather(owcdata,owfdata,3);
        break;
      case 2:
        displayCurrentConditions(owcdata);
        break;
      case 3:
        displaySunMoon(owcdata);
        break;
    }
  }

  if (button == 0) {
    return;
  }

  Serial.print("Button "); Serial.print(button); Serial.println(" pressed");

  if (button == 1) {
    displayAllWeather(owcdata,owfdata,3);
    lastbutton = button;
  }
  if (button == 2) {
    //displayForecast(owcdata,owfdata,3);
    displayCurrentConditions(owcdata);
    lastbutton = button;
  }
  if (button == 3) {
    displaySunMoon(owcdata);
    lastbutton = button;
  }
  
  // wait until button is released
  while (readButtons()) {
    delay(10);
  }

}

