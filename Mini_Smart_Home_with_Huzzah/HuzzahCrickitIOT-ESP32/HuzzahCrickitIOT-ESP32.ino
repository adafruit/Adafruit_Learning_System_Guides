// SPDX-FileCopyrightText: 2019 Anne Barela for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <WiFi.h>
#include <PubSubClient.h>
#include "config.h"
#include <Adafruit_Crickit.h>
#include <seesaw_servo.h>
#include <seesaw_motor.h>
#include <seesaw_neopixel.h>
 
#define NEOPIX_PIN (20)                  /* Neopixel pin */
#define NEOPIX_NUMBER_OF_PIXELS (7)
#define LUX CRICKIT_SIGNAL1
#define PIR CRICKIT_SIGNAL3
#define DOOR CRICKIT_SIGNAL5
#define chip_name "CrickitOIT_1"

Adafruit_Crickit crickit;
seesaw_Servo myservo(&crickit);  // create servo object to control a servo
seesaw_Motor motor_a(&crickit);
seesaw_NeoPixel strip = seesaw_NeoPixel(NEOPIX_NUMBER_OF_PIXELS, NEOPIX_PIN, NEO_GRB + NEO_KHZ800);

//****************************** MQTT TOPICS

//***** Door Lock
#define MQTTlock "house/lock"
//***** Window Fan
#define MQTTfan "house/fan"
#define MQTTfanSpeed "house/fan/speed"
//***** RGB LED 1
#define MQTTled1 "house/led/one"
#define MQTTled1Bright "house/led/one/brightness"
#define MQTTled1Color "house/led/one/color"
//***** RGB LED 2
#define MQTTled2 "house/led/two"
#define MQTTled2Bright "house/led/two/brightness"
#define MQTTled2Color "house/led/two/color"
//***** RGB LED 3
#define MQTTled3 "house/led/three"
#define MQTTled3Bright "house/led/three/brightness"
#define MQTTled3Color "house/led/three/color"
//***** RGB LED 4
#define MQTTled4 "house/led/four"
#define MQTTled4Bright "house/led/four/brightness"
#define MQTTled4Color "house/led/four/color"
//***** RGB LED 5
#define MQTTled5 "house/led/five"
#define MQTTled5Bright "house/led/five/brightness"
#define MQTTled5Color "house/led/five/color"
//***** Light Level Sensor 
#define MQTTlux "house/lux"
//***** Temperature and Humidity Sensor 
#define MQTTtemp "house/temperature"
#define MQTThumid "house/humidity"
//***** Motion Sensor 
#define MQTTpir "house/motion"
//***** Door Sensor 
#define MQTTdoor "house/door"

//****************************** Connection Settings
WiFiClient espClient;
PubSubClient client(espClient);
long lastMsg = 0;
char msg[50];
int value = 0;
char message_buff[100];

//****************************** RGB LEDs
int R[5];
int G[5];
int B[5];
bool LEDstate[5];

//****************************** Sensor Smoothing
const int numReadings = 30;
int lux_R[numReadings];      // the readings from the lux input
int temp_R[numReadings];      // the readings from the temperature input
int humid_R[numReadings];      // the readings from the humidity input
int readIndex = 0;              // the index of the current reading
int total = 0;                  // the running total
int Lux_A = 0;                // the average

/****************************** Define Global Veriables  ***************************************/


void setup() {
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);

  if(!crickit.begin()){
    Serial.println("ERROR!");
    while(1);
  }
  else Serial.println("Crickit started");

  crickit.pinMode(LUX, INPUT);
  crickit.pinMode(PIR, INPUT_PULLUP);
  crickit.pinMode(DOOR, INPUT_PULLUP);
  
  myservo.attach(CRICKIT_SERVO1);  // attaches the servo to CRICKIT_SERVO1 pin
  motor_a.attach(CRICKIT_MOTOR_A1, CRICKIT_MOTOR_A2);
  strip.begin();           // INITIALIZE NeoPixel strip object (REQUIRED)
  strip.show(); // Initialize all pixels to 'off'
  //strip.setPixelColor(1, strip.Color(0, 0, 255));
  for(uint16_t i=0; i<5; i++) {
    R[i] = 255;
    G[i] = 255;
    B[i] = 255;
  }
  for (int thisReading = 0; thisReading < numReadings; thisReading++) {
    lux_R[thisReading] = 0;
  }
}

void setup_wifi() {


  delay(10);
  // We start by connecting to a WiFi network
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());

}

void callback(char* topic, byte* payload, unsigned int length) {
  int i = 0;
  char message_buff[100];
  String StrPayload;
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  for (i = 0; i < length; i++) {
    message_buff[i] = payload[i];
  }
  message_buff[i] = '\0';
  StrPayload = String(message_buff);
  int IntPayload = StrPayload.toInt();
  Serial.print(StrPayload);
  
  if (String(topic) == MQTTlock) {
    if (StrPayload == "UNLOCK") {
      myservo.write(180);
    }
    if (StrPayload == "LOCK") {
      myservo.write(0);
    }
  }

  if (String(topic) == MQTTfan) {
    if (StrPayload == "OFF") {
      motor_a.throttle(0);
    }
    if (StrPayload == "ON") {
      motor_a.throttle(1);
    }
  }

  if (String(topic) == MQTTfanSpeed) {
    if (StrPayload == "low") {
      motor_a.throttle(0.4);
    }
    if (StrPayload == "medium") {
      motor_a.throttle(0.6);
    }
    if (StrPayload == "high") {
      motor_a.throttle(1);
    }
  }

  //.................. Light 1 ......................//
  if (String(topic) == MQTTled1) {
    if (StrPayload == "OFF") {
      LEDstate[0] = false;
      strip.setPixelColor(0, strip.Color(0, 0, 0));
    }
    if (StrPayload == "ON") {
      if (!LEDstate[0]) {
        strip.setPixelColor(0, strip.Color(R[0], G[0], B[0]));
        LEDstate[0] = true;
      }
    }
  }
  if (String(topic) == MQTTled1Bright) {
    int r = map(R[0], 0, 255, 0, IntPayload);
    int g = map(G[0], 0, 255, 0, IntPayload);
    int b = map(B[0], 0, 255, 0, IntPayload);
    strip.setPixelColor(0, strip.Color(r, g, b));
  }
  if (String(topic) == MQTTled1Color) {
    R[0] = StrPayload.substring(0, StrPayload.indexOf(',')).toInt();
    G[0] = StrPayload.substring(StrPayload.indexOf(',') + 1, StrPayload.lastIndexOf(',')).toInt();
    B[0] = StrPayload.substring(StrPayload.lastIndexOf(',') + 1).toInt();
    strip.setPixelColor(0, strip.Color(R[0], G[0], B[0]));
  }
  strip.show();
  //.................. Light 2 ......................//
  if (String(topic) == MQTTled2) {
    if (StrPayload == "OFF") {
      LEDstate[1] = false;
      strip.setPixelColor(1, strip.Color(0, 0, 0));
    }
    if (StrPayload == "ON") {
      if (!LEDstate[1]) {
        strip.setPixelColor(1, strip.Color(R[1], G[1], B[1]));
        LEDstate[1] = true;
      }
    }
  }
  if (String(topic) == MQTTled2Bright) {
    int r = map(R[1], 0, 255, 0, IntPayload);
    int g = map(G[1], 0, 255, 0, IntPayload);
    int b = map(B[1], 0, 255, 0, IntPayload);
    strip.setPixelColor(1, strip.Color(r, g, b));
  }
  if (String(topic) == MQTTled2Color) {
    R[1] = StrPayload.substring(0, StrPayload.indexOf(',')).toInt();
    G[1] = StrPayload.substring(StrPayload.indexOf(',') + 1, StrPayload.lastIndexOf(',')).toInt();
    B[1] = StrPayload.substring(StrPayload.lastIndexOf(',') + 1).toInt();
    strip.setPixelColor(1, strip.Color(R[1], G[1], B[1]));
  }
  strip.show();
  
  //.................. Light 3 ......................//
  if (String(topic) == MQTTled3) {
    if (StrPayload == "OFF") {
      LEDstate[2] = false;
      strip.setPixelColor(2, strip.Color(0, 0, 0));
    }
    if (StrPayload == "ON") {
      if (!LEDstate[2]) {
        strip.setPixelColor(2, strip.Color(R[2], G[2], B[2]));
        LEDstate[2] = true;
      }
    }
  }
  if (String(topic) == MQTTled3Bright) {
    int r = map(R[2], 0, 255, 0, IntPayload);
    int g = map(G[2], 0, 255, 0, IntPayload);
    int b = map(B[2], 0, 255, 0, IntPayload);
    strip.setPixelColor(2, strip.Color(r, g, b));
  }
  if (String(topic) == MQTTled3Color) {
    R[2] = StrPayload.substring(0, StrPayload.indexOf(',')).toInt();
    G[2] = StrPayload.substring(StrPayload.indexOf(',') + 1, StrPayload.lastIndexOf(',')).toInt();
    B[2] = StrPayload.substring(StrPayload.lastIndexOf(',') + 1).toInt();
    strip.setPixelColor(2, strip.Color(R[2], G[2], B[2]));
  }
  strip.show();
  
//.................. Light 4 ......................//
  if (String(topic) == MQTTled4) {
    if (StrPayload == "OFF") {
      LEDstate[3] = false;
      strip.setPixelColor(3, strip.Color(0, 0, 0));
    }
    if (StrPayload == "ON") {
      if (!LEDstate[3]) {
        strip.setPixelColor(3, strip.Color(R[3], G[3], B[3]));
        LEDstate[3] = true;
      }
    }
  }
  if (String(topic) == MQTTled4Bright) {
    int r = map(R[3], 0, 255, 0, IntPayload);
    int g = map(G[3], 0, 255, 0, IntPayload);
    int b = map(B[3], 0, 255, 0, IntPayload);
    strip.setPixelColor(3, strip.Color(r, g, b));
  }
  if (String(topic) == MQTTled4Color) {
    R[3] = StrPayload.substring(0, StrPayload.indexOf(',')).toInt();
    G[3] = StrPayload.substring(StrPayload.indexOf(',') + 1, StrPayload.lastIndexOf(',')).toInt();
    B[3] = StrPayload.substring(StrPayload.lastIndexOf(',') + 1).toInt();
    strip.setPixelColor(3, strip.Color(R[3], G[3], B[3]));
  }
  strip.show();
  
//.................. Light 5 ......................//
  if (String(topic) == MQTTled5) {
    if (StrPayload == "OFF") {
      LEDstate[4] = false;
      strip.setPixelColor(4, strip.Color(0, 0, 0));
    }
    if (StrPayload == "ON") {
      if (!LEDstate[4]) {
        strip.setPixelColor(4, strip.Color(R[4], G[4], B[4]));
        LEDstate[4] = true;
      }
    }
  }
  if (String(topic) == MQTTled5Bright) {
    int r = map(R[4], 0, 255, 0, IntPayload);
    int g = map(G[4], 0, 255, 0, IntPayload);
    int b = map(B[4], 0, 255, 0, IntPayload);
    strip.setPixelColor(4, strip.Color(r, g, b));
  }
  if (String(topic) == MQTTled5Color) {
    R[4] = StrPayload.substring(0, StrPayload.indexOf(',')).toInt();
    G[4] = StrPayload.substring(StrPayload.indexOf(',') + 1, StrPayload.lastIndexOf(',')).toInt();
    B[4] = StrPayload.substring(StrPayload.lastIndexOf(',') + 1).toInt();
    strip.setPixelColor(4, strip.Color(R[4], G[4], B[4]));
  }
  strip.show();
  Serial.println();
}

void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Attempt to connect
    if (client.connect(chip_name, mqtt_user, mqtt_password)) {
      Serial.println("connected");
      // Once connected, publish an announcement...
      client.publish(MQTTlock, "LOCK");
     // client.publish(MQTTfan, "OFF");
     // client.publish(MQTTled1Color, "255,255,255");
     // client.publish(MQTTled1, "OFF");
     // client.publish(MQTTled2Color, "255,255,255");
     // client.publish(MQTTled2, "OFF");
     // client.publish(MQTTled3Color, "255,255,255");
     // client.publish(MQTTled3, "OFF");
     // client.publish(MQTTled4Color, "255,255,255");
     // client.publish(MQTTled4, "OFF");
     // client.publish(MQTTled5Color, "255,255,255");
     // client.publish(MQTTled5, "OFF");
// ... and resubscribe
      client.subscribe(MQTTlock);
      client.subscribe(MQTTfan);
      client.subscribe(MQTTfanSpeed);
      client.subscribe(MQTTled1);
      client.subscribe(MQTTled1Bright);
      client.subscribe(MQTTled1Color);
      client.subscribe(MQTTled2);
      client.subscribe(MQTTled2Bright);
      client.subscribe(MQTTled2Color);
      client.subscribe(MQTTled3);
      client.subscribe(MQTTled3Bright);
      client.subscribe(MQTTled3Color);
      client.subscribe(MQTTled4);
      client.subscribe(MQTTled4Bright);
      client.subscribe(MQTTled4Color);
      client.subscribe(MQTTled5);
      client.subscribe(MQTTled5Bright);
      client.subscribe(MQTTled5Color);
      
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}

// Fill the dots one after the other with a color
void colorWipe(uint32_t c, uint8_t wait) {
  for(uint16_t i=0; i<NEOPIX_NUMBER_OF_PIXELS; i++) {
    strip.setPixelColor(i, c);
    strip.show();
    delay(wait);
  }
}

void loop() {

  if (!client.connected()) {
    reconnect();
  }
  
  //************** Lux Smoothing
  
  total = total - lux_R[readIndex]; //            subtract the last reading
  lux_R[readIndex] = crickit.analogRead(LUX);  // read from the sensor
  total = total + lux_R[readIndex];  //           add the reading to the total
  readIndex = readIndex + 1;  //                  advance to the next position in the array

  if (readIndex >= numReadings) {  //                if we're at the end of the array...
    readIndex = 0;    //                          ...wrap around to the beginning
    Lux_A = total / numReadings;  //                   calculate the average

    //int Lux = map(lightLux, 290, 590, 10, 960);
    Serial.print("Lux = ");
    Serial.println(Lux_A);

    snprintf (msg, 75, "%ld", Lux_A);
    Serial.println(msg);
    client.publish(MQTTlux, msg);

    delay(10);
    if (crickit.digitalRead(PIR)){
      Serial.println("Motion Sensor = MOVE");
      client.publish(MQTTpir, "MOVE");
    }else{
      Serial.println("Motion Sensor = STILL");
      client.publish(MQTTpir, "STILL");
    }
    delay(10); 
    if (crickit.digitalRead(DOOR)){
      Serial.println("Door = OPEN");
      client.publish(MQTTdoor, "OPEN");
    }else{
      Serial.println("Door = CLOSED");
      client.publish(MQTTdoor, "CLOSED");
    }
  }
  delay(10);        // delay in between reads for stability 
  client.loop();
}

