// SPDX-FileCopyrightText: 2023 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_NeoPixel.h>
#include <Adafruit_LIS3DH.h>
#include <Adafruit_Sensor.h>
#include <107-Arduino-Servo-RP2040.h>

Adafruit_NeoPixel strip(60, PIN_EXTERNAL_NEOPIXELS, NEO_GRB + NEO_KHZ800);

Adafruit_LIS3DH lis = Adafruit_LIS3DH();

static _107_::Servo servo_0;

uint8_t x = 0;

void setup() {
  // core1 setup
  Serial.begin(115200);

  if (! lis.begin(0x18)) {   // change this to 0x19 for alternative i2c address
    Serial.println("Couldnt start LIS3DH");
    while (1) yield();
  }

  lis.setRange(LIS3DH_RANGE_2_G);

  pinMode(PIN_EXTERNAL_POWER, OUTPUT);
  digitalWrite(PIN_EXTERNAL_POWER, HIGH);

  strip.begin();
  strip.show();
  strip.setBrightness(50);

  pinMode(PIN_EXTERNAL_BUTTON, INPUT_PULLUP);

  servo_0.attach(PIN_EXTERNAL_SERVO);
}

void loop() {

  delay(10);
  x++;
  for(int32_t i=0; i< strip.numPixels(); i++) {
      strip.setPixelColor(i, Wheel(((i * 256 / strip.numPixels()) + x) & 255));
  }
  strip.show();
  // Print X Y & Z accelerometer data
  if (x % 10 == 0) {
    // every 100ms
    sensors_event_t event;
    lis.getEvent(&event);
    /* Display the results (acceleration is measured in m/s^2) */
    Serial.print("Accel X: "); Serial.print(event.acceleration.x);
    Serial.print(" \tY: "); Serial.print(event.acceleration.y);
    Serial.print(" \tZ: "); Serial.print(event.acceleration.z);
    Serial.println(" m/s^2 ");
    Serial.println(x);
  }  
  // external button press disable external power
  if (! digitalRead(PIN_EXTERNAL_BUTTON)) {
    Serial.println("External button pressed");
    digitalWrite(PIN_EXTERNAL_POWER, LOW);
  }
  else {
    digitalWrite(PIN_EXTERNAL_POWER, HIGH);
  }

  if (x < 128) {
    // forward
    servo_0.writeMicroseconds(map(x, 0, 127, 1000, 2000));
  } else {  
    // and back
    servo_0.writeMicroseconds(map(x-128, 0, 127, 2000, 1000));
  }
  return;
  
}

uint32_t Wheel(byte WheelPos) {
  WheelPos = 255 - WheelPos;
  if(WheelPos < 85) {
    return strip.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  }
  if(WheelPos < 170) {
    WheelPos -= 85;
    return strip.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
  WheelPos -= 170;
  return strip.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
}

// audio runs on core 2!

#include <I2S.h>

#include "boot.h"
#include "hithere.h"

struct {
  const uint8_t *data;
  uint32_t       len;
  uint32_t       rate;
} sound[] = {
  hithereAudioData, sizeof(hithereAudioData), hithereSampleRate,
  bootAudioData   , sizeof(bootAudioData)   , bootSampleRate,
};
#define N_SOUNDS (sizeof(sound) / sizeof(sound[0]))

I2S i2s(OUTPUT);

uint8_t sndIdx = 0;


void setup1(void) {
  i2s.setBCLK(PIN_I2S_BIT_CLOCK);
  i2s.setDATA(PIN_I2S_DATA);
  i2s.setBitsPerSample(16);
}

void loop1() {
  Serial.printf("Core #2 Playing audio clip #%d\n", sndIdx);
  play_i2s(sound[sndIdx].data, sound[sndIdx].len, sound[sndIdx].rate);
  delay(5000);
  if(++sndIdx >= N_SOUNDS) sndIdx = 0;
}

void play_i2s(const uint8_t *data, uint32_t len, uint32_t rate) {

  // start I2S at the sample rate with 16-bits per sample
  if (!i2s.begin(rate)) {
    Serial.println("Failed to initialize I2S!");
    delay(500);
    i2s.end();
    return;
  }
  
  for(uint32_t i=0; i<len; i++) {
    uint16_t sample = (uint16_t)data[i] * 32;
    // write the same sample twice, once for left and once for the right channel
    i2s.write(sample);
    i2s.write(sample);
  }
  i2s.end();
}
