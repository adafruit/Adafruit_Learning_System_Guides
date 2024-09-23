// SPDX-FileCopyrightText: 2024 ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Arduino.h>

#define IROUT 9
#define IRIN  2

volatile unsigned long pulseCount = 0;

#if defined(ARDUINO_RASPBERRY_PI_PICO)
#include "hardware/pwm.h"
void countPulse() {
  pulseCount++;
}
#else
void countPulse() {
  pulseCount++;
}
#endif

void setup() {
  Serial.begin(115200);
  pinMode(IRIN, INPUT); // Assuming the input signal is connected to pin 2

  attachInterrupt(digitalPinToInterrupt(IRIN), countPulse, RISING);
  pinMode(IROUT, OUTPUT);

}

bool testFreq(uint32_t freq) {
  uint32_t temp = 0;

  Serial.print(freq); Serial.println(" Hz");
  setFrequency(freq); // Set the initial frequency to the specified value
  pulseCount = 0;
  delay(100);
  temp = pulseCount;
  Serial.print("\tCounted "); Serial.print(temp);
  Serial.println(" pulses");
  if ((temp > (freq / 10) + (freq / 100)) || (temp < (freq / 10) - (freq / 100))) {
    return false;
  }
  return true;
}

void loop() {
  Serial.println("----------------------");
  if (!testFreq(30000)) return;
  if (!testFreq(40000)) return;
  if (!testFreq(50000)) return;
  if (!testFreq(60000)) return;

}

void setFrequency(unsigned long frequency) {
#if defined(__AVR__)
  unsigned long ocrValue;
  byte csBits = 0;

  // Disable interrupts
  noInterrupts();

  // Reset Timer1 Control Registers
  TCCR1A = 0;
  TCCR1B = 0;
  TCNT1 = 0; // Reset counter

  // Set Timer1 to CTC mode (Clear Timer on Compare Match)
  TCCR1B |= (1 << WGM12);

  // Determine best prescaler and OCR1A value for the desired frequency
  if (frequency > 4000) { // Can use no prescaler if frequency is high enough
    csBits = (1 << CS10); // No prescaler
    ocrValue = 16000000 / (2 * frequency) - 1;
  } else if (frequency > 500) {
    csBits = (1 << CS11); // Prescaler 8
    ocrValue = 2000000 / (2 * frequency) - 1;
  } else if (frequency > 60) {
    csBits = (1 << CS11) | (1 << CS10); // Prescaler 64
    ocrValue = 250000 / (2 * frequency) - 1;
  } else {
    csBits = (1 << CS12); // Prescaler 256
    ocrValue = 62500 / (2 * frequency) - 1;
  }

  // Handle boundary conditions for OCR1A
  if (ocrValue > 65535) ocrValue = 65535; // Cap at maximum for 16-bit timer
  if (ocrValue < 1) ocrValue = 1; // Ensure OCR1A is at least 1

  OCR1A = ocrValue;
  TCCR1B |= csBits; // Set the prescaler
  TCCR1A |= (1 << COM1A0); // Toggle OC1A on Compare Match

  // Re-enable interrupts
  interrupts();

#elif defined(ARDUINO_RASPBERRY_PI_PICO)
  // Set PWM frequency for the RP2040
  gpio_set_function(IROUT, GPIO_FUNC_PWM);
  uint slice_num = pwm_gpio_to_slice_num(IROUT);
  pwm_set_wrap(slice_num, 125000000 / frequency);
  pwm_set_chan_level(slice_num, PWM_CHAN_A, 125000000 / (2 * frequency));
  pwm_set_enabled(slice_num, true);

#endif
}
