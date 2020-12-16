// This program does a test of all the PyPortal Titano hardware 
// so you can get an example of how to read
// sensors, touchscreen, and display stuff!

#include "SPI.h"
#include "Adafruit_GFX.h"
#include "Adafruit_HX8357.h"
#include <Adafruit_SPIFlash.h>
#include "TouchScreen.h"
#include <SdFat.h>
#include <WiFiNINA.h>
#include "click.h"

#define RED_LED       13
#define TFT_RESET     24
#define TFT_BACKLIGHT 25
#define LIGHT_SENSOR  A2
#define SD_CS         32       
#define SPKR_SHUTDOWN 50

#define TFT_D0        34 // Data bit 0 pin (MUST be on PORT byte boundary)
#define TFT_WR        26 // Write-strobe pin (CCL-inverted timer output)
#define TFT_DC        10 // Data/command pin
#define TFT_CS        11 // Chip-select pin
#define TFT_RST       24 // Reset pin
#define TFT_RD         9 // Read-strobe pin
#define TFT_BACKLIGHT 25

// PyPortal Titano
Adafruit_HX8357 tft = Adafruit_HX8357(tft8bitbus, TFT_D0, TFT_WR, TFT_DC, TFT_CS, TFT_RST, TFT_RD);

Adafruit_FlashTransport_QSPI flashTransport(PIN_QSPI_SCK, PIN_QSPI_CS, PIN_QSPI_IO0, PIN_QSPI_IO1, PIN_QSPI_IO2, PIN_QSPI_IO3);
Adafruit_SPIFlash flash(&flashTransport);

#define YP A4  // must be an analog pin, use "An" notation!
#define XM A7  // must be an analog pin, use "An" notation!
#define YM A6   // can be a digital pin
#define XP A5   // can be a digital pin
TouchScreen ts = TouchScreen(XP, YP, XM, YM, 300);
#define X_MIN  760
#define X_MAX  320
#define Y_MIN  875
#define Y_MAX  193

Adafruit_GFX_Button soundBtn = Adafruit_GFX_Button();
SdFat SD;

char text[25]=" ";

void setup() {
  Serial.begin(115200);
  //while (!Serial);

  Serial.println("All Test!");

  pinMode(RED_LED, OUTPUT);
  pinMode(TFT_BACKLIGHT, OUTPUT);
  digitalWrite(TFT_BACKLIGHT, HIGH);

  pinMode(TFT_RESET, OUTPUT);
  digitalWrite(TFT_RESET, HIGH);
  delay(10);
  digitalWrite(TFT_RESET, LOW);
  delay(10);
  digitalWrite(TFT_RESET, HIGH);
  delay(10);

  tft.begin();

  tft.fillScreen(HX8357_BLACK);
  tft.setTextSize(2);
  tft.setTextColor(HX8357_GREEN);
  tft.setTextWrap(true);
  tft.setCursor(0, 0);

  tft.print("QSPI Flash...");
  if (!flash.begin()){
    Serial.println("Could not find flash on QSPI bus!");
    tft.setTextColor(HX8357_RED);
    tft.println("FAILED");
    while (1);
  }
  Serial.println("Reading QSPI ID");
  Serial.print("JEDEC ID: 0x"); Serial.println(flash.getJEDECID(), HEX);
  tft.setTextColor(HX8357_GREEN);
  tft.print("QSPI Flash JEDEC 0x"); tft.println(flash.getJEDECID(), HEX);

  /*************** SD CARD */
  tft.setCursor(0, 48);
  tft.print("SD Card...");
  if (!SD.begin(SD_CS)) {
    Serial.println("Card init. failed!");
    tft.setTextColor(HX8357_RED);
    tft.println("FAILED");
    tft.setTextColor(HX8357_GREEN);
  } else {
    tft.println("OK!");
  }

  /*************** WiFi Module */
    
  tft.setCursor(0, 64);
  tft.print("WiFi Module...");
  WiFi.status();
  delay(100);
  if (WiFi.status() == WL_NO_MODULE) {
    Serial.println("ESP32 SPI not found");
    tft.setTextColor(HX8357_RED);
    tft.println("FAILED");
    tft.setTextColor(HX8357_GREEN);
  } else {
    Serial.println("ESP32 SPI mode found");
    tft.println("OK!");
  }

 
  soundBtn.initButton(&tft, 150, 280, 150, 50, HX8357_WHITE, HX8357_YELLOW, HX8357_BLACK, "Sound", 2);
  soundBtn.drawButton();

  analogWriteResolution(12);
  analogWrite(A0, 128);
  pinMode(SPKR_SHUTDOWN, OUTPUT);
  digitalWrite(SPKR_SHUTDOWN, LOW);
}

void loop() {
  digitalWrite(RED_LED, HIGH);
  tft.setTextColor(HX8357_WHITE);
  // read light sensor
  tft.fillRect(160, 100, 240, 16, HX8357_BLACK);
  tft.setCursor(0, 100);
  uint16_t light = analogRead(LIGHT_SENSOR);
  Serial.print("light sensor: "); Serial.println(light);
  tft.print("Light sensor: "); tft.println(light);

  // externals
  tft.fillRect(40, 130, 60, 34, HX8357_BLUE);
  tft.setCursor(0, 132);
  float d3 = (float)analogRead(A1) * 3.3 / 1024;
  float d4 = (float)analogRead(A3) * 3.3 / 1024;
  Serial.print("STEMMA: "); 
  Serial.print(d3,1); Serial.print(", ");
  Serial.print(d4,1); Serial.println();
  tft.print("D3: "); tft.println(d3,1);
  tft.print("D4: "); tft.println(d4,1); 

  tft.fillRect(80, 164, 240, 16, HX8357_BLACK);
  tft.setCursor(0, 164);
  tft.print("Touch: ");
  
  TSPoint p = ts.getPoint();
  // we have some minimum pressure we consider 'valid'
  // pressure of 0 means no pressing!
  if (p.z > (ts.pressureThreshhold +200)) {
     Serial.print("X = "); Serial.print(p.x);
     Serial.print("\tY = "); Serial.print(p.y);
     Serial.print("\tPressure = "); Serial.println(p.z);
     
     // map touchscreen coordinates to screen coordinates
     int16_t x = map(p.x, X_MIN, X_MAX, 320, 0); // inverted X compared to screen
     int16_t y = map(p.y, Y_MIN, Y_MAX, 0, 480);
     // raw position
     //int16_t tx = p.x;
     //int16_t ty = p.y;
     //tft.print("("); tft.print(tx); tft.print(", "); tft.print(ty); tft.println(")");
     tft.fillRect(10, 180, 240, 16, HX8357_BLACK);
     tft.print("X:"); 
     tft.print(itoa(x,text,10)); tft.print(" Y:"); 
     tft.print(itoa(y,text,10)); tft.print(" Z:");
     tft.print(itoa(p.z,text,10));
     //tft.println(")");
     
    if (soundBtn.contains(x, y)) {
      Serial.println("Ding!");
      soundBtn.press(true);
    } else {
      soundBtn.press(false);
    }
  } else {
    soundBtn.press(false);
  }
  if (soundBtn.justPressed()) {
    soundBtn.drawButton(true);
    digitalWrite(SPKR_SHUTDOWN, HIGH);

    uint32_t i, prior, usec = 1000000L / SAMPLE_RATE;
    prior = micros();
    for (uint32_t i=0; i<sizeof(clickaudio); i++) {
      uint32_t t;
      while((t = micros()) - prior < usec);
      analogWrite(A0, (uint16_t)clickaudio[i]);
      prior = t;
    }
    digitalWrite(SPKR_SHUTDOWN, LOW);
  }
  if (soundBtn.justReleased()) {
    soundBtn.drawButton(false);
  }
  digitalWrite(RED_LED, LOW);
  delay(20);
}
