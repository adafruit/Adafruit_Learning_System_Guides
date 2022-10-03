// SPDX-FileCopyrightText: Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*
CHEEKMATE: secret message receiver using WiFi, Adafruit IO and
a haptic buzzer. Periodically polls an Adafruit IO dashboard,
converting new messages to Morse code.

WiFi & Adafruit IO credentials are in the accompanying config.h file.
*/

#include <AdafruitIO_WiFi.h>
#include <Adafruit_NeoPixel.h>
#include <Adafruit_DRV2605.h>
#include "config.h" // SET UP WIFI AND ADAFRUIT IO CREDENTIALS HERE

AdafruitIO_WiFi   io(IO_USERNAME, IO_KEY, WIFI_SSID, WIFI_PASS);
AdafruitIO_Feed  *feed = io.feed(FEED_NAME, FEED_OWNER);
Adafruit_NeoPixel led(1, PIN_NEOPIXEL);
Adafruit_DRV2605  drv;
char              message[51];
int               rep = REPS; // Act as though message is already played out

// Runs once at startup
void setup() {
  Serial.begin(115200);

  led.begin();
  led.setBrightness(LED_BRIGHTNESS);
  led.show();

  // Wire1 is the "extra" I2C interface on the QT Py ESP32-S2's
  // STEMMA connector. If adapting to a different board, you might
  // want &Wire for the sole or primary I2C interface.
  drv.begin(&Wire1);
  drv.setRealtimeValue(BUZZ);

  feed->onMessage(handleMessage); // Set up message handler for feed

  Serial.print("Connecting to Adafruit IO");
  io.connect();
  while(io.status() < AIO_CONNECTED) { // Wait for connection
    Serial.write('.');
    delay(500);
  }
  Serial.println(io.statusText());

  buzz_on();
  delay(750); // Long buzz indicates everything is OK
  buzz_off();
}

// Runs repeatedly until reset or power-off
void loop() {
  io.run(); // Must periodically call Adafruit IO event manager
  // Play last message up to REPS times. If a new message has come
  // along in the interim, old message may repeat less than this,
  // and new message resets the count.
  if (rep < REPS) {
    play(message);
    delay(MEDIUM_GAP);
    rep++;
  }
}

// Turn on LED and haptic motor 
void buzz_on() {
  led.setPixelColor(0, LED_COLOR);
  led.show();
  drv.setMode(DRV2605_MODE_REALTIME);
}

// Turn off LED and haptic motor
void buzz_off() {
  led.setPixelColor(0, 0);
  led.show();
  drv.setMode(DRV2605_MODE_INTTRIG);
}

// Convert a string to Morse code, output to both the onboard LED
// and the haptic motor.
void play(char *str) {
  while(char c = toupper(*str++)) { // Upper-caseify each character of string...
    int i=0;
    // Scan Morse dictionary (in config.h) for a match
    for (; i<NUM_SYMBOLS && morse[i].symbol != c; i++);
    if (i < NUM_SYMBOLS) { // Found one!
      char mark;
      for (int j=0; mark = morse[i].mark[j]; j++) {
        buzz_on();
        delay(mark == '-' ? DASH_LENGTH : DOT_LENGTH);
        buzz_off();
        delay(SYMBOL_GAP);
      }
      delay(CHARACTER_GAP - SYMBOL_GAP);
    } else { // Not in dictionary, prob. a space
      delay(MEDIUM_GAP);
    }
  }
}

// Called when feed receives a message.
void handleMessage(AdafruitIO_Data *data) {
  // Limit incoming message to fit char buffer + NUL
  strncpy(message, data->toChar(), sizeof message - 1);
  Serial.printf("Received '%s'\n", message);
  rep = 0; // Reset the message repeat counter
}
