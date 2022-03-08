// SPDX-FileCopyrightText 2018 Dave Astels for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*********************************************************************
Written by Dave Astels.
MIT license, check LICENSE for more information
All text above must be included in any redistribution
*********************************************************************/

#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <RTClib.h>
#include <WiFi101.h>
#include <ArduinoJson.h>
#include <Adafruit_NeoPixel.h>
#include "Adafruit_MQTT.h"
#include "Adafruit_MQTT_Client.h"

#include "arduino_secrets.h"

#define BUTTON_A 9
#define BUTTON_B 6
#define BUTTON_C 5
#define MOTION_PIN 10
#define LIGHT_PIN A1
#define NEOPIXEL_PIN A5

#define ROOM_ID "4"

#define OLED_RESET 4
Adafruit_SSD1306 display(OLED_RESET);

Adafruit_NeoPixel pixel = Adafruit_NeoPixel(1, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);

RTC_DS3231 rtc;

WiFiClient client;

// Setup MQTT
#define AIO_SERVER      "io.adafruit.com"
#define AIO_SERVERPORT  1883

Adafruit_MQTT_Client mqtt(&client, AIO_SERVER, AIO_SERVERPORT, AIO_USER, AIO_KEY);
Adafruit_MQTT_Publish photocell_feed(&mqtt, AIO_USER "/feeds/hue-controller.hue-photocell");
Adafruit_MQTT_Publish motion_feed(&mqtt, AIO_USER "/feeds/hue-controller.hue-motion");
Adafruit_MQTT_Publish control_feed(&mqtt, AIO_USER "/feeds/hue-controller.hue-control");

DynamicJsonDocument jsonBuffer(8500);

const char *hue_ip = NULL;
uint8_t *light_numbers = NULL;
boolean last_motion = false;

DateTime *sunrise = NULL;
DateTime *sunset = NULL;

// hardcoded day start/end times

DateTime wakeup = DateTime(0, 0, 0, 8, 0, 0);
DateTime bedtime = DateTime(0, 0, 0, 23, 30, 0);

boolean need_sunrise_sunset_times = false;

//#define TRACE 1

void init_log()
{
#ifdef TRACE
  Serial.begin(9600);
  while (!Serial) {}
  Serial.println("Starting");
#endif
}

void log(const char *msg)
{
#ifdef TRACE
  Serial.print(msg);
#endif
}

void log(const int i)
{
#ifdef TRACE
  Serial.print(i);
#endif
}

void logln(const char *msg)
{
#ifdef TRACE
  Serial.println(msg);
#endif
}


const char *fetch_hue_ip() {
  logln("Getting HUE IP");
  display.println("Getting HUE IP");
  if (!client.connectSSL("www.meethue.com", 443)) {
    logln("COULD NOT CONNECT");
    display.println("COULD NOT CONNECT");
    return NULL;
  } 
  client.println("GET /api/nupnp HTTP/1.1");
  client.println("Host: www.meethue.com");
  client.println("Connection: close");
  if (!client.println()) {
    client.stop();
    logln("CONNECTION ERROR");
    display.println("CONNECTION ERROR");
    return NULL;
  }

  char status[32] = {0};
  client.readBytesUntil('\r', status, sizeof(status));
  if (strcmp(status, "HTTP/1.1 200 OK") != 0) {
    client.stop();
    logln(status);
    display.println(status);
    return NULL;
  }

  char endOfHeaders[] = "\r\n\r\n";
  if (!client.find(endOfHeaders)) {
    client.stop();
    display.println("Getting HUE IP");
    logln("HEADER ERROR");
    display.println("HEADER ERROR");
    return NULL;
  }

  auto error = deserializeJson(jsonBuffer, client);
  client.stop();

  if (error) {
    logln("JSON PARSE ERROR");
    display.println("JSON PARSE ERROR");
    return NULL;
  }

  return strdup(jsonBuffer["internalipaddress"]);
}


boolean fetch_sunrise_sunset(long *sunrise, long *sunset)
{
  logln("Contacting DarkSky");
  display.println("Contacting DarkSky");
  if (!client.connectSSL("api.darksky.net", 443)) {
    logln("COULD NOT CONNECT");
    display.println("COULD NOT CONNECT");
    return false;
  }

  client.print("GET /forecast/");
  client.print(DARKSKY_KEY);
  client.print("/42.9837,-81.2497?units=ca&exclude=currently,minutely,hourly,alerts,flags&language=en");
  client.println(" HTTP/1.1");

  client.print("Host: ");
  client.println("api.darksky.net");
  client.println("Connection: close");
  if (!client.println()) {
    client.stop();
    logln("CONNECTION ERROR");
    display.println("CONNECTION ERROR");
    return false;
  }

  char status[32] = {0};
  client.readBytesUntil('\r', status, sizeof(status));
  if (strcmp(status, "HTTP/1.1 200 OK") != 0) {
    client.stop();
    display.println(status);
    return false;
  }

  char endOfHeaders[] = "\r\n\r\n";
  if (!client.find(endOfHeaders)) {
    client.stop();
    logln("HEADER ERROR");
    display.println("HEADER ERROR");
    return false;
  }

  auto error = deserializeJson(jsonBuffer, client);
  client.stop();

  if (error) {
    logln("JSON PARSE ERROR");
    display.println("JSON PARSE ERROR");
    return NULL;
  }

  long start_of_day = jsonBuffer["daily"]["data"][0]["time"];
  long raw_sunrise_time = jsonBuffer["daily"]["data"][0]["sunriseTime"];
  long raw_sunset_time = jsonBuffer["daily"]["data"][0]["sunsetTime"];

  *sunrise = raw_sunrise_time - start_of_day;
  *sunset = raw_sunset_time - start_of_day;

  return true;
}


boolean update_sunrise_sunset()
{
  long sunrise_seconds, sunset_seconds;
  if (!fetch_sunrise_sunset(&sunrise_seconds, &sunset_seconds)) {
    return false;
  }
  
  if (sunrise) {
    delete sunrise;
  }
  sunrise = new DateTime(0, 0, 0, sunrise_seconds / 3600, (sunrise_seconds / 60) % 60, 0);

  if (sunset) {
    delete sunset;
  }
  sunset = new DateTime(0, 0, 0, sunset_seconds / 3600, (sunset_seconds / 60) % 60, 0);

  return true;
}

uint8_t *lights_for_group(const char *group_number)
{
  logln("Finding lights");
  display.println("Finding lights");
  if (!client.connect(hue_ip, 80)) {
    display.println("COULD NOT CONNECT");
    return NULL;
  } 

  client.print("GET /api/");
  client.print(HUE_USER);
  client.print("/groups/");
  client.print(group_number);
  client.println(" HTTP/1.1");

  client.print("Host: ");
  client.println(hue_ip);
  client.println("Connection: close");
  if (!client.println()) {
    client.stop();
    display.println("CONNECTION ERROR");
    return NULL;
  }

  char status[32] = {0};
  client.readBytesUntil('\r', status, sizeof(status));
  if (strcmp(status, "HTTP/1.1 200 OK") != 0) {
    client.stop();
    display.println(status);
    return NULL;
  }

  char endOfHeaders[] = "\r\n\r\n";
  if (!client.find(endOfHeaders)) {
    client.stop();
    display.println("HEADER ERROR");
    return NULL;
  }

  auto error = deserializeJson(jsonBuffer, client);
  client.stop();

  if (error) {
    logln("JSON PARSE ERROR");
    display.println("JSON PARSE ERROR");
    return NULL;
  }

  JsonArray lights = jsonBuffer["lights"];

  uint8_t *light_numbers = (uint8_t*)malloc(lights.size() + 1);
  light_numbers[0] = (uint8_t)lights.size();
  for (uint16_t i = 0; i < lights.size(); i++) {
    light_numbers[i+1] = (uint8_t)atoi((const char *)lights[i]);
  }
  return light_numbers;
}


void update_light(uint8_t light_number, boolean on_off, uint8_t brightness)
{
  if (!client.connect(hue_ip, 80)) {
    return;
  } 

  log("Turning light ");
  log(light_number);
  logln(on_off ? " on" : " off");

  log("PUT /api/");
  log(HUE_USER);
  log("/lights/");
  log(light_number);
  logln("/state HTTP/1.1");

  char content[32];
  sprintf(content, "{\"on\":%s,\"bri\":%d}", on_off ? "true" : "false", brightness);

  client.print("PUT /api/");
  client.print(HUE_USER);
  client.print("/lights/");
  client.print(light_number);
  client.println("/state HTTP/1.1");

  client.print("Host: ");
  client.println(hue_ip);

  client.println("Connection: close");

  client.print("Content-Type: ");
  client.println("application/json");
  client.println("User-Agent: FeatherM0Sender");
  client.print("Content-Length: ");
  client.println(strlen(content));
  client.println();

  client.println(content);
  client.stop();
}


void update_all_lights(uint8_t *light_numbers, boolean on_off, uint8_t brightness)
{
  if (light_numbers != NULL) {
    uint8_t num_lights = light_numbers[0];
    for (int i = 0; i < num_lights; i++) {
      update_light(light_numbers[i+1], on_off, brightness);
    }
  }
}


boolean is_between(DateTime *now, DateTime *start, DateTime *end)
{
  // now > start || now > end
  if (now->hour() < start->hour()) return false;
  if (now->hour() == start->hour() && now->minute() < start->minute()) return false;
  if (now->hour() > end->hour()) return false;
  if (now->hour() == end->hour() && now->minute() > end->minute()) return false;
  return true;
}


void MQTT_connect()
{
  if (mqtt.connected()) {
    return;
  }
  
  while (mqtt.connect() != 0) { // connect will return 0 for connected
    mqtt.disconnect();
    delay(5000);  // wait 5 seconds
  }
}


void setup()
{
  init_log();
  
  pinMode(BUTTON_A, INPUT_PULLUP);
  pinMode(BUTTON_B, INPUT_PULLUP);
  pinMode(BUTTON_C, INPUT_PULLUP);
  pinMode(MOTION_PIN, INPUT_PULLUP);
  
  
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);  // initialize with the I2C addr 0x3C (for the 128x32)
  display.display();
  delay(2000);
  display.setTextSize(1);
  display.setTextColor(WHITE);
  
  WiFi.setPins(8,7,4,2);

  // // attempt to connect to WiFi network:
  int status = WL_IDLE_STATUS;

  display.print(WIFI_SSID);
  while (status != WL_CONNECTED) {
    display.print(".");
    delay(500);
    status = WiFi.begin(WIFI_SSID, WIFI_PASS);
  }

  if (! rtc.begin()) {
    while (1);
  }

  if (rtc.lostPower()) {
    rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
  }

  // Clear the buffer.
  display.clearDisplay();
  display.setCursor(0, 0);

  hue_ip = fetch_hue_ip();
  if (hue_ip == NULL) {
    while (true) {
    }
  }
  light_numbers = lights_for_group(ROOM_ID);
  if (light_numbers == NULL) {
    while (true) {
    }
  }
  
  pixel.begin();
  pixel.setPixelColor(0, 0, 0, 0);
  pixel.show();

  if (!update_sunrise_sunset()) {
    sunrise = new DateTime(0, 0, 0, 7, 0, 0);
    sunset = new DateTime(0, 0, 0, 16, 30, 0);
  }
}

long ping_time = 0;
void ping_if_time(DateTime now)
{
  if (now.secondstime() >= ping_time) {
    ping_time = now.secondstime() + 250;
    if (!mqtt.ping()) {
      logln("No MQTT ping");
      mqtt.disconnect();
    }
  }
}


void loop()
{
  display.clearDisplay();
  display.setCursor(0, 0);
  
  DateTime now = rtc.now();
  ping_if_time(now);
  MQTT_connect();


  boolean is_motion = digitalRead(MOTION_PIN);
  int32_t light_level = analogRead(LIGHT_PIN);
  char buf[22];
  sprintf(buf, "%d/%02d/%02d   %02d:%02d:%02d", now.year(), now.month(), now.day(), now.hour(), now.minute(), now.second());

  if (now.hour() == 0) {
    if (need_sunrise_sunset_times) {
      if (!update_sunrise_sunset()) {
        while (true) {
        }
      }
      need_sunrise_sunset_times = false;
    }
  } else {
    need_sunrise_sunset_times = true;
  }
  
  boolean motion_started = is_motion && !last_motion;
  boolean motion_ended = !is_motion && last_motion;
  last_motion = is_motion;

  if (motion_started) {
    logln("Publishing motion start");
    if (!motion_feed.publish((const char*)"started")) {
      logln("\n***** MQTT motion publish failed\n");
    }     
    if (!photocell_feed.publish(light_level)) {
      logln("\n***** MQTT photocell publish failed\n");
    }
    pixel.setPixelColor(0, 16, 0, 0);
  } else if (motion_ended) {
    if (!motion_feed.publish((const char*)"ended")) {
          logln("\n***** MQTT motion publish failed\n");
    }
    pixel.setPixelColor(0, 0, 0, 0);
  }
  pixel.show();
    
  display.println(buf);
  if (is_motion) {
    display.print("  ");
  } else {
    display.print("No");
  }
  display.print(" Motion  Light: ");
  display.println(light_level);
  display.print(is_between(&now, sunrise, sunset) ? "Light" : "Dark");
  display.println(" out now");
  display.print("You should be ");
  display.println(is_between(&now, &wakeup, &bedtime) ? "awake" : "asleep");
  display.display();

  if (!digitalRead(BUTTON_A) || (motion_started && (light_level < 50 || !is_between(&now, sunrise, sunset)))) {
    if (!control_feed.publish((const char*)"on")) {
      logln("\n***** MQTT control publish failed\n");
    }
    update_all_lights(light_numbers, true, is_between(&now, &wakeup, &bedtime) ? 100 : 10);
  }
  if (!digitalRead(BUTTON_C) || motion_ended) {
    if (!control_feed.publish((const char*)"off")) {
      logln("\n*****MQTT control publish failed\n");
    }
    update_all_lights(light_numbers, false, 0);
  }
  
  delay(400);
}
