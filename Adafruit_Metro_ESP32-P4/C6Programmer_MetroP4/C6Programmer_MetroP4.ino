// SPDX-FileCopyrightText: 2026 ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Adafruit Metro ESP32-P4: USB Serial/JTAG to onboard C6 ROM loader.
// Use esptool --chip esp32c6 --baud 115200 --before no-reset --after no-reset.
// Validated with Espressif ESP-Hosted 2.12.11:
// https://espressif.github.io/arduino-esp32/hosted/esp32c6-v2.12.11.bin

const uint8_t C6_ENABLE = PIN_C6_ENABLE;
const uint8_t C6_BOOT = PIN_C6_BOOT;
const uint8_t C6_RX = PIN_C6_RX;  // P4 receives the C6 TX signal.
const uint8_t C6_TX = PIN_C6_TX;  // P4 sends to the C6 RX signal.
HardwareSerial c6(1);
bool bridgeActive = false;

// Reset the C6 with BOOT held low so it starts in ROM download mode.
static void enterBridge(bool announce) {
  pinMode(C6_ENABLE, OUTPUT);
  digitalWrite(C6_ENABLE, LOW);
  pinMode(C6_BOOT, OUTPUT);
  digitalWrite(C6_BOOT, LOW);
  delay(100);
  digitalWrite(C6_ENABLE, HIGH);
  delay(100);
  pinMode(C6_BOOT, INPUT_PULLUP);

  if (announce) {
    Serial.println("C6 ROM bridge ready at 115200 baud");
    Serial.flush();
  } else {
    // Automatic mode: drop the C6 ROM boot banner and any partial esptool
    // packets that arrived during the reset, so the stream starts clean.
    while (c6.available()) c6.read();
    while (Serial.available()) Serial.read();
  }
  bridgeActive = true;
}

void setup() {
  // USB delivers a whole esptool packet much faster than the 115200-baud UART.
  // Hold even a fully SLIP-escaped 16 KiB flash block while UART drains it.
  Serial.setRxBufferSize(65536);
  Serial.setTxBufferSize(8192);
  Serial.begin(115200);
  delay(250);

  Serial.println("Adafruit Metro ESP32-P4: C6 programmer v3 START");

  c6.setRxBufferSize(8192);
  c6.begin(115200, SERIAL_8N1, C6_RX, C6_TX);
  Serial.println("Commands: r=restart P4, p=enter C6 ROM-loader bridge at 115200 baud");
  Serial.println("Or just run esptool; the bridge starts automatically.");
}

void loop() {
  if (!bridgeActive) {
    if (Serial.available()) {
      int command = Serial.read();
      if (command == 'r') {
        Serial.println("Restarting P4");
        Serial.flush();
        delay(100);
        ESP.restart();
      } else if (command == 'p') {
        enterBridge(true);
      } else if (command == 0xC0) {
        // Start of an esptool SLIP packet: enter the bridge silently.
        enterBridge(false);
      }
    }
    delay(1);
    return;
  }

  uint8_t buffer[256];
  size_t count = 0;
  while (Serial.available() && count < sizeof(buffer)) {
    buffer[count++] = Serial.read();
  }
  if (count) {
    c6.write(buffer, count);
  }
  count = 0;
  while (c6.available() && count < sizeof(buffer)) {
    buffer[count++] = c6.read();
  }
  if (count) {
    Serial.write(buffer, count);
  }
  delay(1);
}
