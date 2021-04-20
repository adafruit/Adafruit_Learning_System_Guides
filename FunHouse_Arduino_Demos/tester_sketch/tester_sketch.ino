#include <Adafruit_DotStar.h>
#include <Adafruit_GFX.h>    // Core graphics library
#include <Adafruit_ST7789.h> // Hardware-specific library for ST7789
#include <Adafruit_DPS310.h>
#include <Adafruit_AHTX0.h>
#include "funhouse_gfx.h"

#define BG_COLOR ST77XX_BLACK

// display!
Adafruit_ST7789 tft = Adafruit_ST7789(TFT_CS, TFT_DC, TFT_RESET);
// LEDs!
Adafruit_DotStar pixels(NUM_DOTSTAR, PIN_DOTSTAR_DATA, PIN_DOTSTAR_CLOCK, DOTSTAR_BRG);
// sensors!
Adafruit_DPS310 dps;
Adafruit_AHTX0 aht;

uint8_t LED_dutycycle = 0;
uint16_t firstPixelHue = 0;

int32_t touch_points[] = {0, 0, 0, 0, 0, 0, 7000, 14000, 20000, 25000, 25000, 25000, 25000, 25000};

char runtest = 0x0;

void setup() {
  Serial.begin(115200);
  delay(100);
  
  pixels.begin(); // Initialize pins for output
  pixels.show();  // Turn all LEDs off ASAP
  pixels.setBrightness(20);

  pinMode(BUTTON_DOWN, INPUT_PULLDOWN);
  pinMode(BUTTON_SELECT, INPUT_PULLDOWN);
  pinMode(BUTTON_UP, INPUT_PULLDOWN);
  
  tft.init(240, 240);                // Initialize ST7789 screen
  pinMode(TFT_BACKLIGHT, OUTPUT);
  digitalWrite(TFT_BACKLIGHT, LOW); // Backlight off

  tft.setTextSize(2);
  tft.setTextColor(ST77XX_YELLOW);
  tft.setTextWrap(false);
  
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(SPEAKER, OUTPUT);

  ledcSetup(0, 2000 * 80, 8);
  ledcAttachPin(LED_BUILTIN, 0);

  ledcSetup(1, 2000 * 80, 8);
  ledcAttachPin(SPEAKER, 1);
  ledcWrite(1, 0);

  aht.begin();
  dps.begin_I2C();

  tft.fillScreen(0x0);
  tft.drawRGBBitmap(0, 62, funhouse_crop, 236, 115);
  digitalWrite(TFT_BACKLIGHT, HIGH);
  for (int i=0; i<1000; i++) {
    delay(1);
    if (Serial.available() && (runtest != 0xAF)) {
       runtest = Serial.read();
       break;
    }    
  }
  tft.fillScreen(BG_COLOR);
}



void loop() {
  if (Serial.available() && runtest!=0xAF) {
     runtest = Serial.read();
     tft.fillScreen(BG_COLOR);
  }

  if (runtest == 0xAF) {
     runTest();
     return;
  }


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
    tft.setTextColor(0x808080);
  } else {
    Serial.println("DOWN pressed");
    tft.setTextColor(ST77XX_WHITE);
  }
  tft.print("DOWN ");

  if (! digitalRead(BUTTON_SELECT)) {  
    tft.setTextColor(0x808080);
  } else {
    Serial.println("SELECT pressed");
    tft.setTextColor(ST77XX_WHITE);
  }
  tft.print("SEL ");
  
  if (! digitalRead(BUTTON_UP)) {  
    tft.setTextColor(0x808080);
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
    tft.setTextColor(0x808080, BG_COLOR);
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
    tft.setTextColor(0x808080, BG_COLOR);
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
    tft.setTextColor(0x808080, BG_COLOR);
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
     tone(SPEAKER, 988, 100);  // tone1 - B5
     tone(SPEAKER, 1319, 200); // tone2 - E6
     delay(100);
     //tone(SPEAKER, 2000, 100);
  }
  
  /************************** LEDs */
  // pulse red LED
  ledcWrite(0, LED_dutycycle);
  LED_dutycycle += 32;
  
  // rainbow dotstars
  for (int i=0; i<pixels.numPixels(); i++) { // For each pixel in strip...
      int pixelHue = firstPixelHue + (i * 65536L / pixels.numPixels());
      pixels.setPixelColor(i, pixels.gamma32(pixels.ColorHSV(pixelHue)));
  }
  pixels.show(); // Update strip with new contents
  firstPixelHue += 256;  
}














bool dpsOK=false, ahtOK=false, ct6OK=false, ct7OK=false, ct8OK=false, sliderOK=false;
bool jstA0OK=false, jstA1OK=false, jstA2OK, lightOK;
bool downOK=false, selOK=false, upOK=false;

void runTest() {
  /********************* sensors    */
  sensors_event_t humidity, temp, pressure;

  if (! dpsOK) {
    // check DPS!
    tft.setCursor(0, 0);
    tft.setTextColor(ST77XX_YELLOW, BG_COLOR);
    tft.print("DP310: ");

    if (! dps.begin_I2C()) {  
      tft.setTextColor(ST77XX_RED, BG_COLOR);
      tft.println("FAIL!");      
    } else {
      tft.setTextColor(ST77XX_GREEN, BG_COLOR);
      tft.println("OK!");
      dpsOK = true;
    }
  }

  if (! ahtOK) {
    // check AHT!
    tft.setCursor(0, 20);
    tft.setTextColor(ST77XX_YELLOW, BG_COLOR);
    tft.print("AHT20? ");
    
    if (! aht.begin()) {  
      tft.setTextColor(ST77XX_RED, BG_COLOR);
      tft.println("FAIL!");      
    } else {
      tft.setTextColor(ST77XX_GREEN, BG_COLOR);
      tft.println("OK!  "); 
      ahtOK = true;
    }
  }
  
  /************************** CAPACITIVE */
  uint16_t touchread;

  if (! ct6OK) {
    pinMode(6, OUTPUT);
    digitalWrite(6, LOW);
    delay(1);
    pinMode(6, INPUT);
    delay(10);
    tft.setCursor(0, 40);
    tft.setTextColor(ST77XX_YELLOW, BG_COLOR);
    tft.print("Captouch 6: ");
    touchread = touchRead(6);
    Serial.printf("CT 6 = %d\n", touchread);
    if (abs(touchread - touch_points[6]) > 5000 ) {  
      tft.setTextColor(ST77XX_RED, BG_COLOR);
      tft.println("FAIL!");   
    } else {
      tft.setTextColor(ST77XX_GREEN, BG_COLOR);
      tft.println("OK!  "); 
      ct6OK = true;
    }
  }
  
  if (! ct7OK) {
    pinMode(7, OUTPUT);
    digitalWrite(7, LOW);
    delay(1);
    pinMode(7, INPUT);
    delay(10);
    tft.setCursor(0, 60);
    tft.setTextColor(ST77XX_YELLOW, BG_COLOR);
    tft.print("Captouch 7: ");
    touchread = touchRead(7);
    Serial.printf("CT 7 = %d\n", touchread);
    if (abs(touchread - touch_points[7]) > 5000 ) {  
      tft.setTextColor(ST77XX_RED, BG_COLOR);
      tft.println("FAIL!");   
    } else {
      tft.setTextColor(ST77XX_GREEN, BG_COLOR);
      tft.println("OK!  "); 
      ct7OK = true;
    }
  }

  if (! ct8OK) {
    pinMode(8, OUTPUT);
    digitalWrite(8, LOW);
    delay(1);
    pinMode(8, INPUT);
    delay(10);
    tft.setCursor(0, 80);
    tft.setTextColor(ST77XX_YELLOW, BG_COLOR);
    tft.print("Captouch 8: ");
    touchread = touchRead(8);
    Serial.printf("CT 8 = %d\n", touchread);
    if (abs(touchread - touch_points[8]) > 5000 ) {  
      tft.setTextColor(ST77XX_RED, BG_COLOR);
      tft.println("FAIL!");   
    } else {
      tft.setTextColor(ST77XX_GREEN, BG_COLOR);
      tft.println("OK!  "); 
      ct8OK = true;
    }
  }

  if (! sliderOK) {
    tft.setCursor(0, 100);
    tft.setTextColor(ST77XX_YELLOW, BG_COLOR);
    tft.print("Slider: ");
    for (int i=9; i<=13; i++) {
      touchread = touchRead(i);
      delay(10);
      Serial.printf("CT %d = %d\n", i, touchread);
      if ((touchread < 15000) || (touchread > 35000)) { 
        tft.setTextColor(ST77XX_RED, BG_COLOR);
        tft.println("FAIL!");
        break;
      }
      if (i == 13) {
         tft.setTextColor(ST77XX_GREEN, BG_COLOR);
         tft.println("OK!  "); 
         sliderOK = true;
      }
    }
  }

  /************************** ANALOG READ */
  uint16_t analogread;
  if (! jstA0OK) {
    tft.setCursor(0, 120);
    tft.setTextColor(ST77XX_YELLOW, BG_COLOR);
    tft.print("JST A0: ");
    analogread = analogRead(A0);
    if (analogread < 7000 ) {  
      tft.setTextColor(ST77XX_RED, BG_COLOR);
      tft.println("FAIL!");
    } else {
       tft.setTextColor(ST77XX_GREEN, BG_COLOR);
       tft.println("OK!  "); 
       jstA0OK = true;
    }
    Serial.printf("Analog A0 reading: %d\n", analogread);
  }

  if (! jstA1OK) {
    tft.setCursor(0, 140);
    tft.setTextColor(ST77XX_YELLOW, BG_COLOR);
    tft.print("JST A1: ");
    analogread = analogRead(A1);
    if (abs(analogread - 5000) > 500 ) {  
      tft.setTextColor(ST77XX_RED, BG_COLOR);
      tft.println("FAIL!");
    } else {
       tft.setTextColor(ST77XX_GREEN, BG_COLOR);
       tft.println("OK!  "); 
       jstA1OK = true;
    }
    Serial.printf("Analog A1 reading: %d\n", analogread);
  }

  
  if (! jstA2OK) {
    tft.setCursor(0, 160);
    tft.setTextColor(ST77XX_YELLOW, BG_COLOR);
    tft.print("JST A2: ");
    analogread = analogRead(A2);
    if (abs(analogread - 2500) > 500 ) {  
      tft.setTextColor(ST77XX_RED, BG_COLOR);
      tft.println("FAIL!");
    } else {
       tft.setTextColor(ST77XX_GREEN, BG_COLOR);
       tft.println("OK!  "); 
       jstA2OK = true;
    }
    Serial.printf("Analog A2 reading: %d\n", analogread);
  }

  if (! lightOK) {
    tft.setCursor(0, 180);
    tft.setTextColor(ST77XX_YELLOW, BG_COLOR);
    tft.print("Light: ");

    digitalWrite(TFT_BACKLIGHT, LOW);
    delay(10);
    float backlightOff = analogRead(A3);
    digitalWrite(TFT_BACKLIGHT, HIGH);
    delay(10);
    float backlightOn = analogRead(A3);

    Serial.printf("Light sensor reading: %0.1f\n", backlightOn-backlightOff);
    if (backlightOn-backlightOff < 100) {
      tft.setTextColor(ST77XX_RED, BG_COLOR);
      tft.println("FAIL!");
    } else {
      tft.setTextColor(ST77XX_GREEN, BG_COLOR);
      tft.println("OK!  "); 
      lightOK = true;
    }
  }

  /****************** BUTTONS */
  tft.setCursor(0, 200);
  tft.setTextColor(ST77XX_YELLOW);
  tft.print("Buttons: ");
  if (digitalRead(BUTTON_DOWN)) {
    downOK = true;
    Serial.println("DOWN pressed");
  }
  if (downOK) {
    tft.setTextColor(ST77XX_GREEN, BG_COLOR);
  } else {
    tft.setTextColor(ST77XX_RED, BG_COLOR);
  }
  tft.print("DOWN ");

  if (digitalRead(BUTTON_SELECT)) {
    selOK = true;
    Serial.println("SELECT pressed");
  }
  if (selOK) {
    tft.setTextColor(ST77XX_GREEN, BG_COLOR);
  } else {
    tft.setTextColor(ST77XX_RED, BG_COLOR);
  }
  tft.print("SEL ");

  if (digitalRead(BUTTON_UP)) {
    upOK = true;
    Serial.println("UP pressed");
  }
  if (upOK) {
    tft.setTextColor(ST77XX_GREEN, BG_COLOR);
  } else {
    tft.setTextColor(ST77XX_RED, BG_COLOR);
  }
  tft.print("UP ");

  /************************** LEDs */
  // pulse red LED
  ledcWrite(0, LED_dutycycle);
  LED_dutycycle += 32;
  
  // rainbow dotstars
  for (int i=0; i<pixels.numPixels(); i++) { // For each pixel in strip...
      int pixelHue = firstPixelHue + (i * 65536L / pixels.numPixels());
      pixels.setPixelColor(i, pixels.gamma32(pixels.ColorHSV(pixelHue)));
  }
  pixels.show(); // Update strip with new contents
  firstPixelHue += 256;

  
  if (! (dpsOK && ahtOK && ct6OK && ct7OK && ct8OK && sliderOK && 
         jstA0OK && jstA1OK && jstA2OK && lightOK && downOK && selOK && upOK)) {
          return;
  }
         
  /************************** Beep! */

   Serial.println("** Beep! ***");
   tone(SPEAKER, 988, 100);  // tone1 - B5
   tone(SPEAKER, 1319, 200); // tone2 - E6

  tft.setCursor(0, 220);
  tft.setTextColor(ST77XX_GREEN, BG_COLOR);
  tft.println("** TEST COMPLETE **");
  Serial.println("TEST OK");
  while (1) {
    for (int i=0; i<pixels.numPixels(); i++) { // For each pixel in strip...
      int pixelHue = firstPixelHue + (i * 65536L / pixels.numPixels());
      pixels.setPixelColor(i, pixels.gamma32(pixels.ColorHSV(pixelHue)));
    }
    pixels.show(); // Update strip with new contents
    firstPixelHue += 256;
    delay(10);
  }
}


void tone(uint8_t pin, float frequecy, float duration) {
  ledcSetup(1, frequecy * 80, 8);
  ledcAttachPin(pin, 1);
  ledcWrite(1, 128);
  delay(duration);
  ledcWrite(1, 0);
}
