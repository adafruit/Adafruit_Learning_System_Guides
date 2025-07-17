// 16-bit Adafruit_GFX-compatible framebuffer for RP2350 HSTX

#include <Adafruit_dvhstx.h>

// initialize display with HSTX DVI CowBell pinout
DVHSTX16 display({14, 12, 18, 16}, DVHSTX_RESOLUTION_320x240);

void setup() {
  Serial.begin(115200);
  // while(!Serial);
  if (!display.begin()) { // Blink LED if insufficient RAM
    pinMode(LED_BUILTIN, OUTPUT);
    for (;;)
      digitalWrite(LED_BUILTIN, (millis() / 500) & 1);
  }
  Serial.println("display initialized");
}

void loop() {
  // Draw random lines
  display.drawLine(random(display.width()), random(display.height()),
                   random(display.width()), random(display.height()),
                   random(65536));
  sleep_ms(1);
}
