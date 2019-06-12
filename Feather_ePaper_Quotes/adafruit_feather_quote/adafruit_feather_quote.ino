/***************************************************
 * Quote Display for Adafruit ePaper FeatherWings
 * For use with Adafruit tricolor and monochrome ePaper FeatherWings
 * 
 * Adafruit invests time and resources providing this open source code.
 * Please support Adafruit and open source hardware by purchasing
 * products from Adafruit!
 * 
 * Written by Dan Cogliano for Adafruit Industries
 * Copyright (c) 2019 Adafruit Industries
 * 
 * Notes: 
 * Update the secrets.h file with your WiFi details
 * Uncomment the ePaper display type you are using below.
 * Change the SLEEP setting to define the time between quotes
 */
 
#include <Adafruit_GFX.h>    // Core graphics library
#include <HTTPClient.h>
#include <ArduinoJson.h>     //https://github.com/bblanchon/ArduinoJson
#include <Adafruit_EPD.h>
#include "secrets.h"

// define the # of seconds to sleep before waking up and getting a new quote
#define SLEEP 3600 // 1 hour in seconds

// WiFi timeout in seconds
#define WIFI_TIMEOUT 30

// What fonts do you want to use?
#include <Fonts/FreeSans9pt7b.h>
//#include <Fonts/FreeSans12pt7b.h> // a font option for larger screens

// qfont is the font for the quote
const GFXfont *qfont = &FreeSans9pt7b;
//const GFXfont *qfont = &FreeSans12pt7b;

// afont is the font for the author's name
const GFXfont *afont = &FreeSans9pt7b;
//const GFXfont *afont = &FreeSans12pt7b;

// ofont is the font for the origin of the feed
const GFXfont *ofont = NULL;

// font to use if qfont is too large
// NULL means use the system font (which is small)
const GFXfont *smallfont = NULL;


// ESP32 settings
#define SD_CS       14
#define SRAM_CS     32
#define EPD_CS      15
#define EPD_DC      33 
#define LEDPIN      13
#define LEDPINON    HIGH
#define LEDPINOFF   LOW 

#define EPD_RESET   -1 // can set to -1 and share with microcontroller Reset!
#define EPD_BUSY    -1 // can set to -1 to not use a pin (will wait a fixed delay)

// Uncomment the following line if you are using 2.13" tricolor 212*104 EPD
//Adafruit_IL0373 epd(212, 104 ,EPD_DC, EPD_RESET, EPD_CS, SRAM_CS, EPD_BUSY);
// Uncomment the following line if you are using 2.13" monochrome 250*122 EPD
Adafruit_SSD1675 epd(250, 122, EPD_DC, EPD_RESET, EPD_CS, SRAM_CS, EPD_BUSY);

// get string length in pixels
// set text font prior to calling this
int getStringLength(const char *str, int strlength = 0)
{
  char buff[1024];
  int16_t x, y;
  uint16_t w, h;
  if(strlength == 0)
  {
    strcpy(buff, str);
  }
  else
  {
    strncpy(buff, str, strlength);
    buff[strlength] = '\0';
  }
  epd.getTextBounds(buff, 0, 0, &x, &y, &w, &h);
  return(w);  
}

// word wrap routine
// first time send string to wrap
// 2nd and additional times: use empty string
// returns substring of wrapped text.
char *wrapWord(const char *str, int linesize)
{
  static char buff[255];
  int linestart = 0;
  static int lineend = 0;
  static int bufflen = 0;
  if(strlen(str) == 0)
  {
    // additional line from original string
    linestart = lineend + 1;
    lineend = bufflen;
    Serial.println("existing string to wrap, starting at position " + String(linestart) + ": " + String(&buff[linestart]));
  }
  else
  {
    Serial.println("new string to wrap: " + String(str));
    memset(buff,0,sizeof(buff));
    // new string to wrap
    linestart = 0;
    strcpy(buff,str);
    lineend = strlen(buff);
    bufflen = strlen(buff);
  }
  uint16_t w;
  int lastwordpos = linestart;
  int wordpos = linestart + 1;
  while(true)
  {
    while(buff[wordpos] == ' ' && wordpos < bufflen)
      wordpos++;
    while(buff[wordpos] != ' ' && wordpos < bufflen)
      wordpos++;
    if(wordpos < bufflen)
      buff[wordpos] = '\0';
    w = getStringLength(&buff[linestart]);
    if(wordpos < bufflen)
      buff[wordpos] = ' ';
    if(w > linesize)
    {
      buff[lastwordpos] = '\0';
      lineend = lastwordpos;
      return &buff[linestart];
    }
    else if(wordpos >= bufflen)
    {
      // first word too long or end of string, send it anyway
      buff[wordpos] = '\0';
      lineend = wordpos;
      return &buff[linestart];        
    }
    lastwordpos = wordpos;
    wordpos++;
  }
}

// return # of lines created from word wrap
int getLineCount(const char *str, int scrwidth)
{
  int linecount = 0;
  String line = wrapWord(str,scrwidth);

  while(line.length() > 0)
  {
    linecount++;
    line = wrapWord("",scrwidth);
  }
  return linecount;  
}

int getLineHeight(const GFXfont *font = NULL)
{
  int height;
  if(font == NULL)
  {
    height = 12;
  }
  else
  {
    height = (uint8_t)pgm_read_byte(&font->yAdvance);
  }
  return height;
}

// Retrieve page response from given URL
String getURLResponse(String url)
{
  HTTPClient http;
  String jsonstring = "";
  Serial.println("getting url: " + url);
  if(http.begin(url))
  {
    Serial.print("[HTTP] GET...\n");
    // start connection and send HTTP header
    int httpCode = http.GET();

    // httpCode will be negative on error
    if (httpCode > 0) {
      // HTTP header has been sent and Server response header has been handled
      Serial.println("[HTTP] GET... code: " + String(httpCode));

      // file found at server
      if (httpCode == HTTP_CODE_OK || httpCode == HTTP_CODE_MOVED_PERMANENTLY) {
      jsonstring = http.getString();
      // use this string for testing very long quotes
      //jsonstring = "[{\"text\":\"Don't worry about what anybody else is going to do… The best way to predict the future is to invent it. Really smart people with reasonable funding can do just about anything that doesn't violate too many of Newton's Laws!\",\"author\":\"Alan Kay\"}]";
      Serial.println(jsonstring);
    }
    } else {
      Serial.println("[HTTP] GET... failed, error: " + http.errorToString(httpCode));
    }
    http.end();
  }
  else {
    Serial.println("[HTTP] Unable to connect");
  }
  return jsonstring;
}

void getQuote(String &quote, String &author)
{
  StaticJsonDocument<1024> doc;
  String url = "https://www.adafruit.com/api/quotes.php";
  String jsonquote = getURLResponse(url);
  if(jsonquote.length() > 0)
  {
    // remove start and end brackets, jsonBuffer is confused by them
    jsonquote = jsonquote.substring(1,jsonquote.length()-1);
    Serial.println("using: " + jsonquote);
    DeserializationError error = deserializeJson(doc, jsonquote);
    if (error) 
    {
      Serial.println("json parseObject() failed");
      Serial.println("bad json: " + jsonquote);
      quote = "json parseObject() failed";
    }
    else
    {
      String tquote = doc["text"];
      String tauthor = doc["author"];
      quote = tquote;
      author = tauthor;
    }
  }
  else
  {
    quote = "Error retrieving URL";
  }
}

void printQuote(String &quote)
{
  int x = 0;
  int y = 0;
  bool bsmallfont = false;
  epd.setTextColor(EPD_BLACK);
  epd.setFont(qfont);
  epd.setTextSize(1);

  int scrwidth = epd.width() - 8;
  Serial.println("Screen width is " + String(scrwidth));
  Serial.println("Screen height is " + String(epd.height()));
  int linecount = getLineCount(quote.c_str(),scrwidth);
  int lineheightquote = getLineHeight(qfont);
  int lineheightauthor = getLineHeight(afont);
  int lineheightother = getLineHeight(ofont);
  int maxlines = (epd.height() - (lineheightauthor + lineheightother)) / lineheightquote;
  Serial.println("maxlines is " + String(maxlines));
  Serial.println("line height is " +String(lineheightquote));
  Serial.println("linecount is " +String(linecount));
  int topmargin = 0;
  if(linecount > maxlines)
  {
    // too long for default font size
    // next attempt, reduce lineheight to .8 size
    lineheightquote = .8 * lineheightquote;
    maxlines = (epd.height() - (lineheightauthor + lineheightother)) / lineheightquote;
    if(linecount > maxlines)
    {
      // next attempt, use small font
      epd.setFont(smallfont);
      bsmallfont = true;
      epd.setTextSize(1);
      lineheightquote = getLineHeight(smallfont);
      maxlines = (epd.height() - (lineheightauthor + lineheightother)) / lineheightquote;
      linecount = getLineCount(quote.c_str(),scrwidth);
      if(linecount > maxlines)
      {
        // final attempt, last resort is to reduce the lineheight to make it fit
        lineheightquote = (epd.height() - (lineheightauthor + lineheightother)) / linecount;
      }
    }
    Serial.println("maxlines has changed to " + String(maxlines));
    Serial.println("line height has changed to " +String(lineheightquote));
    Serial.println("linecount has changed to " +String(linecount));
  }
  if(linecount <= maxlines)
  {

    topmargin = (epd.height() - (lineheightauthor + lineheightother) - linecount*lineheightquote)/2;
    if(!bsmallfont)
      topmargin+=lineheightquote-4;
    //Serial.println("topmargin = " + String(topmargin));
  }
  String line = wrapWord(quote.c_str(),scrwidth);

  int counter = 0;
  epd.setTextColor(EPD_BLACK);
  while(line.length() > 0)
  {
    counter++;
    Serial.println("printing line " + String(counter) + ": '" + line + String("'"));
    epd.setCursor(x +4, y + topmargin);
    epd.print(line);
    y += lineheightquote;
    line = wrapWord("",scrwidth);
  }
}

void printAuthor(String author)
{
  epd.setTextColor(EPD_BLACK);
  epd.setFont(afont);
  int lineheightauthor = getLineHeight(afont);
  int lineheightother = getLineHeight(ofont);
  int x = getStringLength(author.c_str());
  // draw line above author
  epd.drawLine(epd.width() - x - 10, epd.height() - (lineheightauthor + lineheightother) + 2, epd.width(), epd.height() - (lineheightauthor + lineheightother) + 2, EPD_RED);
  epd.drawLine(epd.width() - x - 10, epd.height() - (lineheightauthor + lineheightother) + 2, epd.width() - x - 10,epd.height() - lineheightother - lineheightauthor/3, EPD_RED);
  epd.drawLine(0, epd.height() - lineheightother - lineheightauthor/3, epd.width() - x - 10,epd.height() - lineheightother - lineheightauthor/3, EPD_RED);
  // draw author text
  int cursorx = epd.width() - x - 4;
  int cursory = epd.height() - lineheightother - 2;
  if(afont == NULL)
  {
    cursory = epd.height() - lineheightother - lineheightauthor - 2 ;
  }
  epd.setCursor(cursorx, cursory);
  epd.print(author);
}

void printOther(String other)
{
  epd.setFont(ofont);
  int lineheightother = getLineHeight(ofont);
  int ypos = epd.height() - 2;
  if (ofont == NULL)
    ypos = epd.height() - (lineheightother - 2);
  epd.setTextColor(EPD_BLACK);
  epd.setCursor(4,ypos);
  epd.print(other);
}

void setup() {
  Serial.begin(115200);
  //while(!Serial);

  pinMode(LEDPIN, OUTPUT);
  digitalWrite(LEDPIN, LEDPINON);

  epd.begin();
  Serial.println("ePaper display initialized");
  epd.clearBuffer();
  epd.setTextWrap(false);

  Serial.print("Connecting to WiFi ");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int counter = 0;
  while (WiFi.status() != WL_CONNECTED && counter < WIFI_TIMEOUT) {
    delay(1000);
    Serial.print(".");
    counter++;
  }
  
  String quote, author;
  if(WiFi.status() == WL_CONNECTED)
  {
    Serial.println("connected");
    getQuote(quote, author);  
  }
  else
  {
    quote = "WiFi connection timed out, try again later";
    Serial.println(quote);
  }
  
  printQuote(String("\"") + quote + String("\""));
  printAuthor(author);
  printOther("adafruit.com/quotes");
  
  epd.display();
  Serial.println("done, going to sleep...");
  // power down ePaper display
  epd.powerDown();
  // put microcontroller to sleep, wake up after specified time
  ESP.deepSleep(SLEEP * 1e6);
}

void loop() {
  // should never get here, setup() puts the CPU to sleep
}
