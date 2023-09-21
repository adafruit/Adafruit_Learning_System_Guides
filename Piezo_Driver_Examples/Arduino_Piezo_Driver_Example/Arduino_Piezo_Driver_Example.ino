// SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#define PIEZO_PIN  5      // Pin connected to the piezo buzzer.

int toneFreq[] = {262, 294, 330, 349, 392, 440, 494, 523};
int toneCount = 8;

void setup() {
  Serial.begin(115200);
  Serial.println("Piezo Tone Example");
}

void loop() {

  for (int i=0; i < toneCount; i++) {
    Serial.print("Playing frequency: ");
    Serial.println(toneFreq[i]);
    tone(PIEZO_PIN, toneFreq[i]);
    delay(250);  // Pause for half a second.
    noTone(PIEZO_PIN);
    delay(50);
  }
  Serial.println();
  delay(1000);

}
