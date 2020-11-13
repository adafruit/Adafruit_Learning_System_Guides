#include <Adafruit_NeoPixel.h>

Adafruit_NeoPixel pixels = Adafruit_NeoPixel(4, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

void setup() {
  //Initialize serial
  Serial.begin(115200);

  pinMode(BUTTON_A, INPUT_PULLUP);
  pinMode(BUTTON_B, INPUT_PULLUP);
  pinMode(BUTTON_C, INPUT_PULLUP);
  pinMode(BUTTON_D, INPUT_PULLUP);

  // Neopixel power
  pinMode(NEOPIXEL_POWER, OUTPUT);
  digitalWrite(NEOPIXEL_POWER, LOW); // on

  pixels.begin();
  pixels.setBrightness(50);
  pixels.fill(0xFF00FF);
  pixels.show(); // Initialize all pixels to 'off'
}

void loop() {
  if (! digitalRead(BUTTON_A)) {
    Serial.println("Button A pressed");
    digitalWrite(NEOPIXEL_POWER, LOW); // on
    pixels.fill(0xFF0000);
    pixels.show();
  }
  else if (! digitalRead(BUTTON_B)) {
    Serial.println("Button B pressed");
    digitalWrite(NEOPIXEL_POWER, LOW); // on
    pixels.fill(0x00FF00);
    pixels.show();
  }
  else if (! digitalRead(BUTTON_C)) {
    Serial.println("Button C pressed");
    digitalWrite(NEOPIXEL_POWER, LOW); // on
    pixels.fill(0x0000FF);
    pixels.show();
  }
  else if (! digitalRead(BUTTON_D)) {
    Serial.println("Button D pressed");
    digitalWrite(NEOPIXEL_POWER, LOW); // on
    pixels.fill(0xFF00FF);
    pixels.show();
  }
  else {
    // No buttons pressed! turn em off
    digitalWrite(NEOPIXEL_POWER, HIGH);
  }
}
