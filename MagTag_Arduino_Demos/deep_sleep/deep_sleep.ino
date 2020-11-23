#include <Adafruit_ThinkInk.h>
#include <Adafruit_NeoPixel.h>
#include "magtaglogo.h"

Adafruit_NeoPixel intneo = Adafruit_NeoPixel(4, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);
ThinkInk_290_Grayscale4_T5 display(EPD_DC, EPD_RESET, EPD_CS, -1, -1);

void setup() {
  //Initialize serial and wait for port to open:
  Serial.begin(115200);

  pinMode(BUTTON_A, INPUT_PULLUP);
  pinMode(BUTTON_B, INPUT_PULLUP);
  pinMode(BUTTON_C, INPUT_PULLUP);
  pinMode(BUTTON_D, INPUT_PULLUP);
  pinMode(13, OUTPUT);
  digitalWrite(13, LOW);
  
  // Neopixel power
  pinMode(NEOPIXEL_POWER, OUTPUT);
  pinMode(SPEAKER_SHUTDOWN, OUTPUT);
  digitalWrite(NEOPIXEL_POWER, LOW); // on
  digitalWrite(SPEAKER_SHUTDOWN, HIGH); // on

  intneo.begin();
  intneo.setBrightness(50);
  intneo.fill(100, 0, 100);
  intneo.show(); 

  display.begin(THINKINK_MONO);
  display.clearBuffer();
  display.drawBitmap(0, 38, magtaglogo_mono, MAGTAGLOGO_WIDTH, MAGTAGLOGO_HEIGHT, EPD_BLACK);
  display.display();
  delay(1500);
  display.powerDown();
  digitalWrite(EPD_RESET, LOW); // hardware power down mode
  
  digitalWrite(SPEAKER_SHUTDOWN, LOW); // off
  digitalWrite(NEOPIXEL_POWER, HIGH); // off
  esp_sleep_enable_timer_wakeup(1000000);
  esp_deep_sleep_start();
}

void loop() {
}
