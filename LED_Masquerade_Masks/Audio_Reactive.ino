// Sound level sketch for Adafruit microphone amplifier.
// For the GEMMA sequin masquerade mask.

#define SAMPLE_WINDOW 33 // Sample window width in mS (33 mS = ~30 Hz)
#define LED_PIN        0 // DIGITAL pin # where LEDs are connected
#define MIC_PIN       A1 // ANALOG pin # where microphone "OUT" is connected

void setup() {
  pinMode(LED_PIN, OUTPUT);
}

void loop() {
  // Listen to mic for short interval, recording min & max signal
  unsigned int signalMin = 1023, signalMax = 0;
  unsigned long startTime = millis();
  while((millis() - startTime) < SAMPLE_WINDOW) {
    int sample = analogRead(MIC_PIN);
    if(sample < signalMin) signalMin = sample;
    if(sample > signalMax) signalMax = sample;
  }
  int peakToPeak = signalMax - signalMin; // Max - min = peak-peak amplitude
  int n = (peakToPeak - 10) / 4;          // Remove low-level noise, lower gain
  if(n > 255)    n = 255;                 // Limit to valid PWM range
  else if(n < 0) n = 0;
  analogWrite(LED_PIN, n);                // And send to LEDs as PWM level
}
