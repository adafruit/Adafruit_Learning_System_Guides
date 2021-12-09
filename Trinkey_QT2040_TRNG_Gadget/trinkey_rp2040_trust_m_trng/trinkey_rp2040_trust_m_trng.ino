#include <Adafruit_NeoPixel.h>
#include "OPTIGATrustM.h"

//--| User Config |-----------------------------------------------
#define TRNG_FORMAT   2         // 0=raw, 1=CSV, 2=JSON
#define TRNG_LENGTH   8         // random number length in bytes, 8 to 256
#define TRNG_RATE     100       // generate new number ever X ms
#define BEAT_RATE     1000      // neopixel heart beat rate in ms, 0=none
#define BEAT_COLOR    0xADAF00  // neopixel heart beat color
//----------------------------------------------------------------

uint8_t trng[TRNG_LENGTH];
int current_time, last_trng, last_beat;

Adafruit_NeoPixel neopixel(1, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

void setup() 
{
  Serial.begin(115200); // USB CDC doesn't really care about baud rate
  
  if (trustM.begin()) {
    Serial.println("Failed to initialize Trust M.");
    neoPanic();
  }

  neopixel.begin();
  neopixel.fill(0);
  neopixel.show();

  last_trng = last_beat = millis();
}

void loop()
{
  current_time = millis();

  if (current_time - last_trng > TRNG_RATE) {
    trustM.getRandom(TRNG_LENGTH, trng);
    sendTRNG();
    last_trng = current_time;   
  }

  if ((BEAT_RATE) && (current_time - last_beat > BEAT_RATE)) {
    if (neopixel.getPixelColor(0)) {
      neopixel.fill(0);
    } else {
      neopixel.fill(BEAT_COLOR);
    }
    neopixel.show();
    last_beat = current_time;
  }
}

void sendTRNG() {
  if (TRNG_FORMAT) {
    // formatted string output (CSV, JSON)
    if (TRNG_FORMAT==2) Serial.print("{\"trng\": \"");
    for (uint16_t i=0; i<TRNG_LENGTH; i++) {
      Serial.print(trng[i]);
      if (i != TRNG_LENGTH - 1) Serial.print(", "); 
    }
    if (TRNG_FORMAT==2) Serial.print("\"}");
    Serial.println();
  } else {
    // raw output (bytes)
    Serial.write(trng, TRNG_LENGTH);
  }
}


void neoPanic() {
  while (1) {
    neopixel.fill(0xFF0000); neopixel.show(); delay(100);
    neopixel.fill(0x000000); neopixel.show(); delay(100);
  }
}
