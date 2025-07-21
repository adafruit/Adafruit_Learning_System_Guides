// SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// LM73100 IMON Current Monitoring

const int IMON_PIN = A0;           // IMON connected to analog pin A0
const float RIMON = 1500.0;        // RIMON resistor value in ohms (1.5kΩ)
const float GIMON = 2.5;           // GIMON typical value in μA/A (from datasheet, typical is 2.5)
const float VREF = 5.0;            // Arduino reference voltage (5V for most Arduinos)
const int ADC_RESOLUTION = 1024;

void setup() {
  Serial.begin(9600);
  pinMode(IMON_PIN, INPUT);
  
  Serial.println("LM73100 Current Monitor Started");
  Serial.println("================================");
  Serial.print("RIMON: ");
  Serial.print(RIMON);
  Serial.println(" ohms");
  Serial.print("GIMON: ");
  Serial.print(GIMON);
  Serial.println(" μA/A");
  Serial.println("================================\n");
}

void loop() {
  int adcValue = analogRead(IMON_PIN);
  float vimon = (adcValue * VREF) / ADC_RESOLUTION;
  float iout_A = vimon / (RIMON * GIMON);
  float iout_mA = iout_A * 1000.0;

  Serial.print("ADC Value: ");
  Serial.print(adcValue);
  Serial.print(" | VIMON: ");
  Serial.print(vimon, 3);
  Serial.print(" V | Output Current: ");
  Serial.print(iout_mA, 2);
  Serial.print(" mA (");
  Serial.print(iout_A, 3);
  Serial.println(" A)");
  
  delay(500);  // Read every 500ms
}
