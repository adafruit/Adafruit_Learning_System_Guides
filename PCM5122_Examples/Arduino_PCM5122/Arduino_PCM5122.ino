// SPDX-FileCopyrightText: 2025 Ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*!
 *
 * Basic test example for the Adafruit PCM5122
 * 
 * Written by Limor 'ladyada' Fried with assistance from Claude Code
 * for Adafruit Industries.
 * 
 * MIT license, all text here must be included in any redistribution.
 */

#include <Adafruit_PCM51xx.h>
#include <I2S.h>
#include <math.h>

Adafruit_PCM51xx pcm;

#define pBCLK D9   // BITCLOCK - I2S clock
#define pWS   D10  // LRCLOCK - Word select
#define pDOUT D11  // DATA - I2S data

// Create I2S port
I2S i2s(OUTPUT);

const int frequency = 440; // frequency of square wave in Hz
const int amplitude = 500; // amplitude of square wave
const int sampleRate = 16000; // 16 KHz is a good quality

const int halfWavelength = (sampleRate / frequency); // half wavelength of square wave

int16_t sample = amplitude; // current sample value
int count = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);

  Serial.println(F("Adafruit PCM51xx Test"));

  // I2C mode (default)
  if (!pcm.begin()) {
    Serial.println(F("Could not find PCM51xx, check wiring!"));
    while (1) delay(10);
  }
  
  // Hardware SPI mode (uncomment to use)
  // if (!pcm.begin(10, &SPI)) {  // CS pin 10
  //   Serial.println(F("Could not find PCM51xx over SPI, check wiring!"));
  //   while (1) delay(10);
  // }
  
  // Software SPI mode (uncomment to use)  
  // if (!pcm.begin(10, 11, 12, 13)) {  // CS, MOSI, MISO, SCLK
  //   Serial.println(F("Could not find PCM51xx over software SPI, check wiring!"));
  //   while (1) delay(10);
  // }
  
  Serial.println(F("PCM51xx initialized successfully!"));

  // Set I2S format to I2S
  Serial.println(F("Setting I2S format"));
  pcm.setI2SFormat(PCM51XX_I2S_FORMAT_I2S);
  
  // Read and display current format
  pcm51xx_i2s_format_t format = pcm.getI2SFormat();
  Serial.print(F("Current I2S format: "));
  switch (format) {
    case PCM51XX_I2S_FORMAT_I2S:
      Serial.println(F("I2S"));
      break;
    case PCM51XX_I2S_FORMAT_TDM:
      Serial.println(F("TDM/DSP"));
      break;
    case PCM51XX_I2S_FORMAT_RTJ:
      Serial.println(F("Right Justified"));
      break;
    case PCM51XX_I2S_FORMAT_LTJ:
      Serial.println(F("Left Justified"));
      break;
    default:
      Serial.println(F("Unknown"));
      break;
  }
  
  // Set I2S word length to 32-bit
  Serial.println(F("Setting I2S word length"));
  pcm.setI2SSize(PCM51XX_I2S_SIZE_16BIT);
  
  // Read and display current word length
  pcm51xx_i2s_size_t size = pcm.getI2SSize();
  Serial.print(F("Current I2S word length: "));
  switch (size) {
    case PCM51XX_I2S_SIZE_16BIT:
      Serial.println(F("16 bits"));
      break;
    case PCM51XX_I2S_SIZE_20BIT:
      Serial.println(F("20 bits"));
      break;
    case PCM51XX_I2S_SIZE_24BIT:
      Serial.println(F("24 bits"));
      break;
    case PCM51XX_I2S_SIZE_32BIT:
      Serial.println(F("32 bits"));
      break;
    default:
      Serial.println(F("Unknown"));
      break;
  }

  // Set error detection bits
  if (!pcm.ignoreFSDetect(true) || !pcm.ignoreBCKDetect(true) || !pcm.ignoreSCKDetect(true) || 
      !pcm.ignoreClockHalt(true) || !pcm.ignoreClockMissing(true) || !pcm.disableClockAutoset(false) || 
      !pcm.ignorePLLUnlock(true)) {
    Serial.println(F("Error detection failed to configure"));
  }
  
  // Enable PLL
  Serial.println(F("Enabling PLL"));
  pcm.enablePLL(true);
  
  // Check PLL status
  bool pllEnabled = pcm.isPLLEnabled();
  Serial.print(F("PLL enabled: "));
  Serial.println(pllEnabled ? F("Yes") : F("No"));
  
  // Set PLL reference to BCK
  Serial.println(F("Setting PLL reference"));
  pcm.setPLLReference(PCM51XX_PLL_REF_BCK);
  
  // Read and display current PLL reference
  pcm51xx_pll_ref_t pllRef = pcm.getPLLReference();
  Serial.print(F("Current PLL reference: "));
  switch (pllRef) {
    case PCM51XX_PLL_REF_SCK:
      Serial.println(F("SCK"));
      break;
    case PCM51XX_PLL_REF_BCK:
      Serial.println(F("BCK"));
      break;
    case PCM51XX_PLL_REF_GPIO:
      Serial.println(F("GPIO"));
      break;
    default:
      Serial.println(F("Unknown"));
      break;
  }

  // Set DAC clock source to PLL
  Serial.println(F("Setting DAC source"));
  pcm.setDACSource(PCM51XX_DAC_CLK_PLL);
  
  // Read and display current DAC source
  pcm51xx_dac_clk_src_t dacSource = pcm.getDACSource();
  Serial.print(F("Current DAC source: "));
  switch (dacSource) {
    case PCM51XX_DAC_CLK_MASTER:
      Serial.println(F("Master clock (auto-select)"));
      break;
    case PCM51XX_DAC_CLK_PLL:
      Serial.println(F("PLL clock"));
      break;
    case PCM51XX_DAC_CLK_SCK:
      Serial.println(F("SCK clock"));
      break;
    case PCM51XX_DAC_CLK_BCK:
      Serial.println(F("BCK clock"));
      break;
    default:
      Serial.println(F("Unknown"));
      break;
  }  

  // Test auto mute (default turn off)
  Serial.println(F("Setting auto mute"));
  pcm.setAutoMute(false);
  
  // Read and display current auto mute status
  bool autoMuteEnabled = pcm.getAutoMute();
  Serial.print(F("Auto mute: "));
  Serial.println(autoMuteEnabled ? F("Enabled") : F("Disabled"));
  
  // Test mute (default do not mute)
  Serial.println(F("Setting mute"));
  pcm.mute(false);
  
  // Read and display current mute status
  bool muteEnabled = pcm.isMuted();
  Serial.print(F("Mute: "));
  Serial.println(muteEnabled ? F("Enabled") : F("Disabled"));

  // Check DSP boot status and power state
  Serial.print(F("DSP boot done: "));
  Serial.println(pcm.getDSPBootDone() ? F("Yes") : F("No"));
  
  pcm51xx_power_state_t powerState = pcm.getPowerState();
  Serial.print(F("Power state: "));
  switch (powerState) {
    case PCM51XX_POWER_POWERDOWN:
      Serial.println(F("Powerdown"));
      break;
    case PCM51XX_POWER_WAIT_CP_VALID:
      Serial.println(F("Wait for CP voltage valid"));
      break;
    case PCM51XX_POWER_CALIBRATION_1:
    case PCM51XX_POWER_CALIBRATION_2:
      Serial.println(F("Calibration"));
      break;
    case PCM51XX_POWER_VOLUME_RAMP_UP:
      Serial.println(F("Volume ramp up"));
      break;
    case PCM51XX_POWER_RUN_PLAYING:
      Serial.println(F("Run (Playing)"));
      break;
    case PCM51XX_POWER_LINE_SHORT:
      Serial.println(F("Line output short / Low impedance"));
      break;
    case PCM51XX_POWER_VOLUME_RAMP_DOWN:
      Serial.println(F("Volume ramp down"));
      break;
    case PCM51XX_POWER_STANDBY:
      Serial.println(F("Standby"));
      break;
    default:
      Serial.println(F("Unknown"));
      break;
  }
  
  // Check PLL lock status
  bool pllLocked = pcm.isPLLLocked();
  Serial.print(F("PLL locked: "));
  Serial.println(pllLocked ? F("Yes") : F("No"));
  
  // Set volume to -6dB on both channels
  Serial.println(F("Setting volume"));
  pcm.setVolumeDB(-6.0, -6.0);
  
  // Read and display current volume
  float leftVol, rightVol;
  pcm.getVolumeDB(&leftVol, &rightVol);
  Serial.print(F("Current volume - Left: "));
  Serial.print(leftVol, 1);
  Serial.print(F("dB, Right: "));
  Serial.print(rightVol, 1);
  Serial.println(F("dB"));

  // Initialize I2S peripheral
  Serial.println("Initializing I2S...");
  i2s.setBCLK(pBCLK);
  i2s.setDATA(pDOUT);
  i2s.setBitsPerSample(16);
  
  // Start I2S at the sample rate
  if (!i2s.begin(sampleRate)) {
    Serial.println("Failed to initialize I2S!");
  }
  
}

void loop() {
  if (count % halfWavelength == 0) {
    // invert the sample every half wavelength count multiple to generate square wave
    sample = -1 * sample;
  }

  // write the same sample twice, once for left and once for the right channel
  i2s.write(sample);
  i2s.write(sample);

  // increment the counter for the next sample
  count++;
}
