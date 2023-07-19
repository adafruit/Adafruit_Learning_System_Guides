// SPDX-FileCopyrightText: 2023 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_LIS3DH.h>
#include <Adafruit_TestBed.h>
#include <WiFi.h>
#include <WiFiAP.h>
#include <Adafruit_Protomatter.h>


extern Adafruit_TestBed TB;
Adafruit_LIS3DH lis = Adafruit_LIS3DH();

uint8_t mcp1_matrix_pins[8] = {45, 21, 37, 39, 38, 40, 41, 42};  // A, E, B2, G2, R2, B1, G1, R1
uint8_t mcp2_matrix_pins[8] = {12, 14, 47, 2, 255, 35, 48, 36}; // A0, OE, LAT, CLK, NC, D, C, B
#define LIGHT_SENSOR 5

int32_t total_time;

bool matrixpinsOK = false, accelOK = false, gpioOK = false, jstOK = false, wifiOK = false, testMode = false, lightOK = false;
uint8_t j=0;

uint8_t rgbPins[]  = {42, 41, 40, 38, 39, 37};
uint8_t addrPins[] = {45, 36, 48, 35, 21};
uint8_t clockPin   = 2;
uint8_t latchPin   = 47;
uint8_t oePin      = 14;
Adafruit_Protomatter matrix(
  64,          // Width of matrix (or matrix chain) in pixels
  4,           // Bit depth, 1-6
  1, rgbPins,  // # of matrix chains, array of 6 RGB pins for each
  4, addrPins, // # of address pins (height is inferred), array of pins
  clockPin, latchPin, oePin, // Other matrix control pins
  false);      // No double-buffering here (see "doublebuffer" example)


void setup() {
  Serial.begin(115200);    
  //while (!Serial) delay(10);

  TB.ledPin = LED_BUILTIN;
  TB.neopixelPin = PIN_NEOPIXEL;
  TB.neopixelNum = 1;
  TB.begin();

  total_time = millis();

  WiFi.softAPIP();
  WiFi.softAP("Matrix Portal ESP32-S3", "adafruit");

  if (! testMode) {
    // Initialize matrix...
    ProtomatterStatus status = matrix.begin();
    Serial.print("Protomatter begin() status: ");
    Serial.println((int)status);
    if(status != PROTOMATTER_OK) {
      // DO NOT CONTINUE if matrix setup encountered an error.
      for(;;);
    }
    // Make four color bars (red, green, blue, white) with brightness ramp:
    for(int x=0; x<matrix.width(); x++) {
      uint8_t level = x * 256 / matrix.width(); // 0-255 brightness
      matrix.drawPixel(x, matrix.height() - 4, matrix.color565(level, 0, 0));
      matrix.drawPixel(x, matrix.height() - 3, matrix.color565(0, level, 0));
      matrix.drawPixel(x, matrix.height() - 2, matrix.color565(0, 0, level));
      matrix.drawPixel(x, matrix.height() - 1,
                       matrix.color565(level, level, level));
    }
    // You'll notice the ramp looks smoother as bit depth increases
    // (second argument to the matrix constructor call above setup()).
  
    // Simple shapes and text, showing GFX library calls:
    matrix.drawCircle(12, 10, 9, matrix.color565(255, 0, 0));
    matrix.drawRect(14, 6, 17, 17, matrix.color565(0, 255, 0));
    matrix.drawTriangle(32, 9, 41, 27, 23, 27, matrix.color565(0, 0, 255));
    matrix.println("ADAFRUIT"); // Default text color is white
    if (matrix.height() > 32) {
      matrix.setCursor(0, 32);
      matrix.println("64 pixel"); // Default text color is white
      matrix.println("matrix"); // Default text color is white
    }
  
    // AFTER DRAWING, A show() CALL IS REQUIRED TO UPDATE THE MATRIX!
  
    matrix.show(); // Copy data to matrix buffers
  }
  pinMode(LIGHT_SENSOR, INPUT);
}



void loop() {
  if (!testMode) {
    if (j == 64) {
      TB.printI2CBusScan();
    }
    
    if (j == 255) {
      TB.setColor(WHITE);
      pinMode(13, OUTPUT);
      digitalWrite(13, HIGH);
      Serial.println("scan start");
      // WiFi.scanNetworks will return the number of networks found
      int n = WiFi.scanNetworks();
      Serial.println("scan done");
      if (n == 0) {
        Serial.println("no networks found");
      } else {
        Serial.print(n);
        Serial.println(" networks found");
        for (int i = 0; i < n; ++i) {
            // Print SSID and RSSI for each network found
            Serial.print(i + 1);
            Serial.print(": ");
            Serial.print(WiFi.SSID(i));
            Serial.print(" (");
            Serial.print(WiFi.RSSI(i));
            Serial.print(")");
            Serial.println((WiFi.encryptionType(i) == WIFI_AUTH_OPEN)?" ":"*");
            delay(10);
        }
      }
      Serial.println("");
      digitalWrite(13, LOW);
    }

    TB.setColor(TB.Wheel(j++));
    delay(10);
    return;
  }
  delay(100);

}
