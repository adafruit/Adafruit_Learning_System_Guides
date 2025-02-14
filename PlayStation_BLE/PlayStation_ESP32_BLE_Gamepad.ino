// SPDX-FileCopyrightText: 2024 John Park for Adafruit Industries
//
// SPDX-License-Identifier: MIT
/*
 * Feather ESP32 Bluetooth LE gamepad https://github.com/lemmingDev/ESP32-BLE-Gamepad
 * Deep sleep with wake on START button press
 * https://randomnerdtutorials.com/esp32-deep-sleep-arduino-ide-wake-up-sources/

 * OTA WiFi uploads
 * https://docs.espressif.com/projects/arduino-esp32/en/latest/ota_web_update.html
 * Sketch > Compile binary, then http://esp32.local/?userid=admin&pwd=admin 
 * pick compiled .bin, upload.
 */

#include <Arduino.h>
#include <BleGamepad.h> 
#include <Adafruit_NeoPixel.h>

#include <esp_wifi.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <Update.h>

bool web_ota = false;

int sleepSeconds = 30; // how long is it inactive before going to sleep

const char* host = "esp32";
const char* ssid = "xxxxxxx";  // your WiFi SSID here
const char* password = "xxxxxxxx";  // your WiFi password here
WebServer server(80);

/*
 * Login page
 */

const char* loginIndex =
 "<form name='loginForm'>"
    "<table width='20%' bgcolor='A09F9F' align='center'>"
        "<tr>"
            "<td colspan=2>"
                "<center><font size=4><b>ESP32 Login Page</b></font></center>"
                "<br>"
            "</td>"
            "<br>"
            "<br>"
        "</tr>"
        "<tr>"
             "<td>Username:</td>"
             "<td><input type='text' size=25 name='userid'><br></td>"
        "</tr>"
        "<br>"
        "<br>"
        "<tr>"
            "<td>Password:</td>"
            "<td><input type='Password' size=25 name='pwd'><br></td>"
            "<br>"
            "<br>"
        "</tr>"
        "<tr>"
            "<td><input type='submit' onclick='check(this.form)' value='Login'></td>"
        "</tr>"
    "</table>"
"</form>"
"<script>"
    "function check(form)"
    "{"
    "if(form.userid.value=='admin' && form.pwd.value=='admin')"
    "{"
    "window.open('/serverIndex')"
    "}"
    "else"
    "{"
    " alert('Error Password or Username')/*displays error message*/"
    "}"
    "}"
"</script>";

/*
 * Server Index Page
 */

const char* serverIndex =
"<script src='https://ajax.googleapis.com/ajax/libs/jquery/3.2.1/jquery.min.js'></script>"
"<form method='POST' action='#' enctype='multipart/form-data' id='upload_form'>"
   "<input type='file' name='update'>"
        "<input type='submit' value='Update'>"
    "</form>"
 "<div id='prg'>progress: 0%</div>"
 "<script>"
  "$('form').submit(function(e){"
  "e.preventDefault();"
  "var form = $('#upload_form')[0];"
  "var data = new FormData(form);"
  " $.ajax({"
  "url: '/update',"
  "type: 'POST',"
  "data: data,"
  "contentType: false,"
  "processData:false,"
  "xhr: function() {"
  "var xhr = new window.XMLHttpRequest();"
  "xhr.upload.addEventListener('progress', function(evt) {"
  "if (evt.lengthComputable) {"
  "var per = evt.loaded / evt.total;"
  "$('#prg').html('progress: ' + Math.round(per*100) + '%');"
  "}"
  "}, false);"
  "return xhr;"
  "},"
  "success:function(d, s) {"
  "console.log('success!')"
 "},"
 "error: function (a, b, c) {"
 "}"
 "});"
 "});"
 "</script>";

////////////////////////////////////// GAMEPAD 
#define numOfButtons 12
// sleep wake button definition (also update line in setup(): 'esp_sleep_enable_ext0_wakeup(GPIO_NUM_4,0);')
#define BUTTON_PIN_BITMASK 0x10 // start button on RTC GPIO pin 4 which is 0x10 (2^4 in hex)
// RTC_DATA_ATTR int bootCount = 0;

BleGamepad bleGamepad("ItsyController", "Adafruit", 100);  // name, manufacturer, batt level to start
byte previousButtonStates[numOfButtons];
byte currentButtonStates[numOfButtons];

// ItsyBitsy EPS32: 13, 12, 14, 33, 32, 7, 5, 27, 15, 20, 8, 22, 21, 19, 36, 37, 38, 4, 26, 25
// RTC IO: 13, 12, 14, 33, 32, 27, 15, 36, 37, 38, 4, 26, 25
// pins that act funny: 5, 37, 22
byte buttonPins[numOfButtons] =      { 13, 12, 14, 33, 32,  7,  27,  15,  21,  19,   4, 26 }; // ItsyBitsy
byte physicalButtons[numOfButtons] = {  1,  2,  4,  5,  7,  8,  15,  16,  13,  14,  12, 11 }; // controller assignments
//                                     b0, b1, b3, b4, b6, b7, b14, b15, b12, b13, b10, b11 
// gampad: O/b0, X/b1, ^/b3, []]/b4, l_trig/b6, r_trig/b7, up/b14 , down/b15 , left/b12 , right/b13, select/b11, start/b10

int last_button_press = millis();
int sleepTime = (sleepSeconds * 1000);  

Adafruit_NeoPixel pixel(1, 0, NEO_GRB + NEO_KHZ800);  // Itsy on-board NeoPixel

void setup() 
{
  Serial.begin(115200);
  delay(500);
  
  //Print the wakeup reason for ESP32
  // print_wakeup_reason();
  esp_sleep_enable_ext0_wakeup(GPIO_NUM_4,0); //1 = High, 0 = Low

  for (byte currentPinIndex = 0; currentPinIndex < numOfButtons; currentPinIndex++) 
  {
        pinMode(buttonPins[currentPinIndex], INPUT_PULLUP);
        previousButtonStates[currentPinIndex] = HIGH;
        currentButtonStates[currentPinIndex] = HIGH;
  }

  bleGamepad.begin();
  delay(100);
  pixel.begin();
  pixel.clear();

  if (web_ota) {

    // Connect to WiFi network
    WiFi.begin(ssid, password);
    Serial.println("");

    // Wait for connection for 20 seconds, then move on
    unsigned long startTime = millis(); // Get the current time
    while (!(WiFi.status() == WL_CONNECTED) && ((millis() - startTime) < 2000)) {
      delay(500);
      Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED) {

      Serial.println("");
      Serial.print("Connected to ");
      Serial.println(ssid);
      Serial.print("IP address: ");
      Serial.println(WiFi.localIP());

      /*use mdns for host name resolution*/
      if (!MDNS.begin(host)) { //http://esp32.local
        Serial.println("Error setting up MDNS responder!");
        while (1) {
          delay(1000);
        }
      }
      Serial.println("mDNS responder started");
      /*return index page which is stored in serverIndex */
      server.on("/", HTTP_GET, []() {
        server.sendHeader("Connection", "close");
        server.send(200, "text/html", loginIndex);
      });
      server.on("/serverIndex", HTTP_GET, []() {
        server.sendHeader("Connection", "close");
        server.send(200, "text/html", serverIndex);
      });
      /*handling uploading firmware file */
      server.on("/update", HTTP_POST, []() {
        server.sendHeader("Connection", "close");
        server.send(200, "text/plain", (Update.hasError()) ? "FAIL" : "OK");
        ESP.restart();
      }, []() {
        HTTPUpload& upload = server.upload();
        if (upload.status == UPLOAD_FILE_START) {
          Serial.printf("Update: %s\n", upload.filename.c_str());
          if (!Update.begin(UPDATE_SIZE_UNKNOWN)) { //start with max available size
            Update.printError(Serial);
          }
        } else if (upload.status == UPLOAD_FILE_WRITE) {
          /* flashing firmware to ESP*/
          if (Update.write(upload.buf, upload.currentSize) != upload.currentSize) {
            Update.printError(Serial);
          }
        } else if (upload.status == UPLOAD_FILE_END) {
          if (Update.end(true)) { //true to set the size to the current progress
            Serial.printf("Update Success: %u\nRebooting...\n", upload.totalSize);
          } else {
            Update.printError(Serial);
          }
        }
      });
      server.begin();
    }
    else {
      Serial.println("");
      Serial.println("WiFi connection timed out, you may need to update SSID/password. Moving on now.");
    }
  }
}

void loop() 
{
  if (web_ota) {
    server.handleClient();
    delay(1);
  }

  if (bleGamepad.isConnected()) 
  {
    pixel.setPixelColor(0, 0x000033);
    pixel.show();

    for (byte currentIndex = 0; currentIndex < numOfButtons; currentIndex++)
        {
            currentButtonStates[currentIndex] = digitalRead(buttonPins[currentIndex]);

            if (currentButtonStates[currentIndex] != previousButtonStates[currentIndex])
            {
                last_button_press = millis();  // update last_button_press for sleep timing

                if (currentButtonStates[currentIndex] == LOW)
                {
                    bleGamepad.press(physicalButtons[currentIndex]);
                }
                else
                {
                    bleGamepad.release(physicalButtons[currentIndex]);
                }
            }
        }

        if (currentButtonStates != previousButtonStates)
        {
            for (byte currentIndex = 0; currentIndex < numOfButtons; currentIndex++)
            {
                previousButtonStates[currentIndex] = currentButtonStates[currentIndex];
            }

            bleGamepad.sendReport();
        }
      if (millis() - last_button_press > sleepTime) {
          server.stop();
          delay(300);
          esp_wifi_stop();
          delay(300);
          esp_deep_sleep_start();
        }
    }
}
