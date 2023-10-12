// SPDX-FileCopyrightText: 2021 Melissa LeBlanc-Williams for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_DotStar.h>
#include <Adafruit_GFX.h>    // Core graphics library
#include <Adafruit_ST7789.h> // Hardware-specific library for ST7789
#include <Adafruit_DPS310.h>
#include <Adafruit_AHTX0.h>

#define NUM_DOTSTAR 5
#define BG_COLOR ST77XX_BLACK
#define ST77XX_GREY 0x8410   // Colors are in RGB565 format

// display!
Adafruit_ST7789 tft = Adafruit_ST7789(TFT_CS, TFT_DC, TFT_RESET);
// LEDs!
Adafruit_DotStar pixels(NUM_DOTSTAR, PIN_DOTSTAR_DATA, PIN_DOTSTAR_CLOCK, DOTSTAR_BRG);
// sensors!
Adafruit_DPS310 dps;
Adafruit_AHTX0 aht;

uint8_t LED_dutycycle = 0;
uint16_t firstPixelHue = 0;

void setup() {
  //while (!Serial);
  Serial.begin(115200);
  delay(100);

  pixels.begin(); // Initialize pins for output
  pixels.show();  // Turn all LEDs off ASAP
  pixels.setBrightness(20);

  pinMode(BUTTON_DOWN, INPUT_PULLDOWN);
  pinMode(BUTTON_SELECT, INPUT_PULLDOWN);
  pinMode(BUTTON_UP, INPUT_PULLDOWN);

  //analogReadResolution(13);

  tft.init(240, 240);                // Initialize ST7789 screen
  pinMode(TFT_BACKLIGHT, OUTPUT);
  digitalWrite(TFT_BACKLIGHT, HIGH); // Backlight on

  tft.fillScreen(BG_COLOR);
  tft.setTextSize(2);
  tft.setTextColor(ST77XX_YELLOW);
  tft.setTextWrap(false);

  // check DPS!
  tft.setCursor(0, 0);
  tft.setTextColor(ST77XX_YELLOW);
  tft.print("DP310? ");


  if (! dps.begin_I2C()) {
    tft.setTextColor(ST77XX_RED);
    tft.println("FAIL!");
    while (1) delay(100);
  }
  tft.setTextColor(ST77XX_GREEN);
  tft.println("OK!");
  dps.configurePressure(DPS310_64HZ, DPS310_64SAMPLES);
  dps.configureTemperature(DPS310_64HZ, DPS310_64SAMPLES);

  // check AHT!
  tft.setCursor(0, 20);
  tft.setTextColor(ST77XX_YELLOW);
  tft.print("AHT20? ");

  if (! aht.begin()) {
    tft.setTextColor(ST77XX_RED);
    tft.println("FAIL!");
    while (1) delay(100);
  }
  tft.setTextColor(ST77XX_GREEN);
  tft.println("OK!");

  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(SPEAKER, OUTPUT);

#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 1, 1)
  ledcAttach(LED_BUILTIN, 2000, 8);
  ledcAttach(SPEAKER, 2000, 8);
  ledcWrite(SPEAKER, 0);
#else
  ledcSetup(0, 2000, 8);
  ledcAttachPin(LED_BUILTIN, 0);

  ledcSetup(1, 2000, 8);
  ledcAttachPin(SPEAKER, 1);
  ledcWrite(1, 0);
#endif
}



void loop() {


  /********************* sensors    */
  sensors_event_t humidity, temp, pressure;

  tft.setCursor(0, 0);
  tft.setTextColor(ST77XX_YELLOW, BG_COLOR);
  dps.getEvents(&temp, &pressure);

  tft.print("DP310: ");
  tft.print(temp.temperature, 0);
  tft.print(" C ");
  tft.print(pressure.pressure, 0);
  tft.print(" hPa");
  tft.println("              ");
  Serial.printf("DPS310: %0.1f *C  %0.2f hPa\n", temp.temperature, pressure.pressure);


  tft.setCursor(0, 20);
  tft.setTextColor(ST77XX_YELLOW, BG_COLOR);
  aht.getEvent(&humidity, &temp);

  tft.print("AHT20: ");
  tft.print(temp.temperature, 0);
  tft.print(" C ");
  tft.print(humidity.relative_humidity, 0);
  tft.print(" %");
  tft.println("              ");
  Serial.printf("AHT20: %0.1f *C  %0.2f rH\n", temp.temperature, humidity.relative_humidity);


  /****************** BUTTONS */
  tft.setCursor(0, 40);
  tft.setTextColor(ST77XX_YELLOW);
  tft.print("Buttons: ");
  if (! digitalRead(BUTTON_DOWN)) {
    tft.setTextColor(ST77XX_GREY);
  } else {
    Serial.println("DOWN pressed");
    tft.setTextColor(ST77XX_WHITE);
  }
  tft.print("DOWN ");

  if (! digitalRead(BUTTON_SELECT)) {
    tft.setTextColor(ST77XX_GREY);
  } else {
    Serial.println("SELECT pressed");
    tft.setTextColor(ST77XX_WHITE);
  }
  tft.print("SEL ");

  if (! digitalRead(BUTTON_UP)) {
    tft.setTextColor(ST77XX_GREY);
  } else {
    Serial.println("UP pressed");
    tft.setTextColor(ST77XX_WHITE);
  }
  tft.println("UP");

  /************************** CAPACITIVE */
  uint16_t touchread;

  tft.setCursor(0, 60);
  tft.setTextColor(ST77XX_YELLOW, BG_COLOR);
  tft.print("Captouch 6: ");
  touchread = touchRead(6);
  if (touchread < 10000 ) {
    tft.setTextColor(ST77XX_GREY, BG_COLOR);
  } else {
    tft.setTextColor(ST77XX_WHITE, BG_COLOR);
  }
  tft.print(touchread);
  tft.println("          ");
  Serial.printf("Captouch #6 reading: %d\n", touchread);

  tft.setCursor(0, 80);
  tft.setTextColor(ST77XX_YELLOW, BG_COLOR);
  tft.print("Captouch 7: ");
  touchread = touchRead(7);
  if (touchread < 20000 ) {
    tft.setTextColor(ST77XX_GREY, BG_COLOR);
  } else {
    tft.setTextColor(ST77XX_WHITE, BG_COLOR);
  }
  tft.print(touchread);
  tft.println("          ");
  Serial.printf("Captouch #7 reading: %d\n", touchread);


  tft.setCursor(0, 100);
  tft.setTextColor(ST77XX_YELLOW, BG_COLOR);
  tft.print("Captouch 8: ");
  touchread = touchRead(8);
  if (touchread < 20000 ) {
    tft.setTextColor(ST77XX_GREY, BG_COLOR);
  } else {
    tft.setTextColor(ST77XX_WHITE, BG_COLOR);
  }
  tft.print(touchread);
  tft.println("          ");
  Serial.printf("Captouch #8 reading: %d\n", touchread);


  /************************** ANALOG READ */
  uint16_t analogread;

  tft.setCursor(0, 120);
  tft.setTextColor(ST77XX_YELLOW, BG_COLOR);
  tft.print("Analog 0: ");
  analogread = analogRead(A0);
  if (analogread < 8000 ) {
    tft.setTextColor(ST77XX_WHITE, BG_COLOR);
  } else {
    tft.setTextColor(ST77XX_RED, BG_COLOR);
  }
  tft.print(analogread);
  tft.println("    ");
  Serial.printf("Analog A0 reading: %d\n", analogread);


  tft.setCursor(0, 140);
  tft.setTextColor(ST77XX_YELLOW, BG_COLOR);
  tft.print("Analog 1: ");
  analogread = analogRead(A1);
  if (analogread < 8000 ) {
    tft.setTextColor(ST77XX_WHITE, BG_COLOR);
  } else {
    tft.setTextColor(ST77XX_RED, BG_COLOR);
  }
  tft.print(analogread);
  tft.println("    ");
  Serial.printf("Analog A1 reading: %d\n", analogread);


  tft.setCursor(0, 160);
  tft.setTextColor(ST77XX_YELLOW, BG_COLOR);
  tft.print("Analog 2: ");
  analogread = analogRead(A2);
  if (analogread < 8000 ) {
    tft.setTextColor(ST77XX_WHITE, BG_COLOR);
  } else {
    tft.setTextColor(ST77XX_RED, BG_COLOR);
  }
  tft.print(analogread);
  tft.println("    ");
  Serial.printf("Analog A2 reading: %d\n", analogread);

  tft.setCursor(0, 180);
  tft.setTextColor(ST77XX_YELLOW, BG_COLOR);
  tft.print("Light: ");
  analogread = analogRead(A3);
  tft.setTextColor(ST77XX_WHITE, BG_COLOR);
  tft.print(analogread);
  tft.println("    ");
  Serial.printf("Light sensor reading: %d\n", analogread);

  /************************** Beep! */
  if (digitalRead(BUTTON_SELECT)) {
     Serial.println("** Beep! ***");
     fhtone(SPEAKER, 988.0, 100.0);  // tone1 - B5
     fhtone(SPEAKER, 1319.0, 200.0); // tone2 - E6
     delay(100);
     //fhtone(SPEAKER, 2000.0, 100.0);
  }

  /************************** LEDs */
  // pulse red LED
#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 1, 1)
  ledcWrite(LED_BUILTIN, LED_dutycycle);
#else
  ledcWrite(0, LED_dutycycle);
#endif
  LED_dutycycle += 32;

  // rainbow dotstars
  for (int i=0; i<pixels.numPixels(); i++) { // For each pixel in strip...
      int pixelHue = firstPixelHue + (i * 65536L / pixels.numPixels());
      pixels.setPixelColor(i, pixels.gamma32(pixels.ColorHSV(pixelHue)));
  }
  pixels.show(); // Update strip with new contents
  firstPixelHue += 256;
}


void fhtone(uint8_t pin, float frequency, float duration) {
#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 1, 1)
  ledcAttach(SPEAKER, frequency, 8);
  ledcWrite(SPEAKER, 128);
  delay(duration);
  ledcWrite(SPEAKER, 0);
#else
  ledcSetup(1, frequency, 8);
  ledcAttachPin(pin, 1);
  ledcWrite(1, 128);
  delay(duration);
  ledcWrite(1, 0);
#endif
}
