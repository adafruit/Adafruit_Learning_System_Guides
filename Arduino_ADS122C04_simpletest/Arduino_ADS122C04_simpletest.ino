// SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*
 * Simple ADS122C04 example - reads all 4 single-ended analog inputs
 * and prints voltages to the Serial Monitor.
 *
 * If any inputs are floating, will read noise
 */

#include <Adafruit_ADS122C04.h>

Adafruit_ADS122C04 adc;

#ifdef ARDUINO_AVR_METRO
float voltage_ref = 5.0; // 5V from metro
#else
float voltage_ref = 3.3; // else assume 3.3V logic
#endif

// The four single-ended MUX settings (AINx vs AVSS)
const ads122c04_mux_t channels[] = {
  ADS122C04_MUX_AIN0,
  ADS122C04_MUX_AIN1,
  ADS122C04_MUX_AIN2,
  ADS122C04_MUX_AIN3
};

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);

  Serial.println("ADS122C04 4-Channel Single-Ended Test");

  if (!adc.begin()) {
    Serial.println("Failed to find ADS122C04 - check wiring!");
    while (1) delay(10);
  }
  Serial.println("ADS122C04 found!");

  // Use analog supply (AVDD-AVSS) as reference for full 0-5V range
  adc.setVoltageReference(ADS122C04_VREF_SUPPLY);
  Serial.print("Setting reference voltage to: ");
  Serial.print(voltage_ref);
  Serial.println("V");
  adc.setReferenceVoltage(voltage_ref);

  // Gain 1, PGA bypassed
  adc.setGain(ADS122C04_GAIN_1);
  adc.enablePGA(false);

  // Single-shot mode at 20 SPS
  adc.setContinuousMode(false);
  adc.setDataRate(ADS122C04_RATE_20SPS);

  Serial.println("Config: AVDD ref, gain=1, single-shot 20 SPS");
  Serial.println();
}

void loop() {
  for (uint8_t ch = 0; ch < 4; ch++) {
    // Select the channel
    adc.setMux(channels[ch]);

    // Trigger a single conversion
    adc.startSync();

    // Wait for data ready (at 20 SPS, conversion takes ~50ms)
    while (!adc.isDataReady()) {
      delay(1);
    }

    // Read raw ADC value, then convert to voltage
    int32_t raw = adc.readData();
    float voltage = adc.convertToVoltage(raw);

    Serial.print("A");
    Serial.print(ch);
    Serial.print(": ");

    if (isnan(voltage)) {
      Serial.print("READ ERROR");
    } else {
      Serial.print("raw=");
      Serial.print(raw);
      Serial.print(" -> ");
      Serial.print(voltage, 6);
      Serial.print(" V");
    }

    Serial.print("\t");
  }

  Serial.println();
  delay(500);
}
