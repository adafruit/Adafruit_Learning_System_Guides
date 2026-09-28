// SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Monster Eye on Qualia S3 with 2.1" round display
// Button Up changes the eye graphics
// Button Down toggles eyeball floating offscreen repeatedly  

#include <Adafruit_Monster_Eyes.h>
#include <Arduino_GFX_Library.h>

#define RGB_W 480
#define RGB_H 480
#define EYE_SCALE 2

// 2.1" round display
Arduino_XCA9554SWSPI expander(PCA_TFT_RESET, PCA_TFT_CS, PCA_TFT_SCK,
                              PCA_TFT_MOSI, &Wire, 0x3F);

Arduino_ESP32RGBPanel rgbpanel(
    TFT_DE, TFT_VSYNC, TFT_HSYNC, TFT_PCLK, TFT_R1, TFT_R2, TFT_R3, TFT_R4,
    TFT_R5, TFT_G0, TFT_G1, TFT_G2, TFT_G3, TFT_G4, TFT_G5, TFT_B1, TFT_B2,
    TFT_B3, TFT_B4, TFT_B5,
    1 /* HSYNC polarity */, 50 /* front porch */, 2 /* pulse width */,
    44 /* back porch */,
    1 /* VSYNC polarity */, 16 /* front porch */, 2 /* pulse width */,
    18 /* back porch */);

Arduino_RGB_Display gfx(
// 2.1" 480x480 round display
 RGB_W, RGB_H, &rgbpanel, 0 /* rotation */, true /* auto_flush */,
 &expander, GFX_NOT_DEFINED /* RST */, TL021WVC02_init_operations, sizeof(TL021WVC02_init_operations));

// update for config.eye files on your board
// should be in the base directory of CIRCUITPY
const char *eyeFiles[] = {
    "/hazel.eye",
    "/demon.eye",
    "/snake.eye",
};
const uint8_t eyeCount = sizeof(eyeFiles) / sizeof(eyeFiles[0]);
uint8_t eyeIndex = 0;

#define ROLL_DIR -1
#define ROLL_EVERY 5000  // Milliseconds between rolls
#define ROLL_OUT_MS 1000  // Time to slide up out of view
#define ROLL_HOLD_MS 250 // Time spent gone
#define ROLL_IN_MS 850   // Time to rise back into view
#define BUTTON_ACTIVE LOW // The board pulls the button lines high
#define DEBOUNCE_DELAY 50 // Raise if one press counts twice

enum RollState { IDLE, ROLL_AWAY, GONE, ROLL_BACK };
RollState rollState = IDLE;
uint32_t rollStart = 0;
int rollSpan = 0;         // Offset at which the eye is fully out of sight
bool rollEnabled = false; // Set true to start rolling from boot

// Ease in and out, the same curve the built-in saccades use.
static float ease(float t) {
  if (t < 0.0f)
    t = 0.0f;
  else if (t > 1.0f)
    t = 1.0f;
  return 3.0f * t * t - 2.0f * t * t * t;
}

struct Button {
  uint8_t pin;                    // Expander pin PCA_BUTTON_UP
  int state;                      // The debounced reading
  int lastReading;                // Previous raw reading
  unsigned long lastDebounceTime; // When the raw reading last changed

  // True once per press
  bool pressed() {
    const int reading = expander.digitalRead(pin);

    if (reading != lastReading) {
      lastDebounceTime = millis(); // Still bouncing restart the timer
    }

    bool fired = false;
    if ((millis() - lastDebounceTime) > DEBOUNCE_DELAY) {
      if (reading != state) {
        state = reading;
        if (state == BUTTON_ACTIVE)
          fired = true;
      }
    }

    lastReading = reading;
    return fired;
  }
};

Button btnUp = {PCA_BUTTON_UP, !BUTTON_ACTIVE, !BUTTON_ACTIVE, 0};
Button btnDown = {PCA_BUTTON_DOWN, !BUTTON_ACTIVE, !BUTTON_ACTIVE, 0};

Adafruit_Monster_Eyes eyes(&gfx, EYE_SCALE);

void setup() {
  Serial.begin(115200);
  // eyes.setVerbose(Serial);

  Wire.setClock(1000000);
  eyes.keepStorageMounted(true);
  eyes.setConfigFile(eyeFiles[eyeIndex]);

  if (!eyes.begin()) {
    Serial.print("Monster Eyes failed: ");
    Serial.println(eyes.errorString());
    while (1)
      delay(1000);
  }

  expander.pinMode(PCA_TFT_BACKLIGHT, OUTPUT);
  expander.digitalWrite(PCA_TFT_BACKLIGHT, HIGH);
  expander.pinMode(PCA_BUTTON_UP, INPUT);
  expander.pinMode(PCA_BUTTON_DOWN, INPUT);

  rollSpan = eyes.eyeSize() * ROLL_DIR;
  rollStart = millis();
}

void loop() {
  const uint32_t now = millis();
  const uint32_t since = now - rollStart;

  if (btnUp.pressed()) {
    eyeIndex = (eyeIndex + 1) % eyeCount;
    Serial.printf("\nButton: loading %s\n", eyeFiles[eyeIndex]);

    const uint32_t t0 = millis();
    if (!eyes.loadEye(eyeFiles[eyeIndex])) {
      Serial.print("  failed: ");
      Serial.println(eyes.errorString());
    } else {
      Serial.printf("  loaded in %lu ms\n", millis() - t0);
    }
    return;
  }

  if (btnDown.pressed()) {
    rollEnabled = !rollEnabled;
    Serial.printf("Eye roll %s\n", rollEnabled ? "ON" : "OFF");
    if (rollEnabled) {
      // Start one right away
      rollState = ROLL_AWAY;
      rollStart = now;
    }
  }
  switch (rollState) {
  case IDLE:
    if (rollEnabled && (since >= ROLL_EVERY)) {
      rollState = ROLL_AWAY;
      rollStart = now;
    }
    break;

  case ROLL_AWAY: // Out of sight
    eyes.setDrawOffset(0, (int)(rollSpan * ease((float)since / ROLL_OUT_MS)));
    if (since >= ROLL_OUT_MS) {
      rollState = GONE;
      rollStart = now;
    }
    break;

  case GONE:
    // Park just past the opposite edge
    eyes.setDrawOffset(0, -rollSpan);
    if (since >= ROLL_HOLD_MS) {
      rollState = ROLL_BACK;
      rollStart = now;
    }
    break;

  case ROLL_BACK: // Back into view from the opposite edge
    eyes.setDrawOffset(
        0, (int)(-rollSpan * (1.0f - ease((float)since / ROLL_IN_MS))));
    if (since >= ROLL_IN_MS) {
      eyes.setDrawOffset(0, 0); // Exactly centred again
      rollState = IDLE;
      rollStart = now;
    }
    break;
  }

  eyes.animate();
}
