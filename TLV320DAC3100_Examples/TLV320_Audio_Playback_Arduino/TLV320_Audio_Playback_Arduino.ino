// SPDX-FileCopyrightText: 2023 Ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*
  This example plays a 'raw' PCM file from memory to I2S
*/

#include <Adafruit_TLV320DAC3100.h>
#include <I2S.h>
#include <math.h>

#include "startup.h" // audio file in flash

Adafruit_TLV320DAC3100 codec;  // Create codec object

// Create the I2S port using a PIO state machine
I2S i2s(OUTPUT);

// GPIO pin numbers on Feather RP2040
#define pBCLK D9 // BITCLOCK
#define pWS   D10 // LRCLOCK
#define pDOUT D11 // DATA

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);
  Serial.println("I2S playback demo");
}

void loop() {
}

void setup1() {
  Serial.begin(115200);
  
  while (!Serial) delay(10);
  Serial.println("\n\nTLV320DAC3100 Sine Tone Test");
  // Start I2C communication with codec
  Serial.println("Initializing codec...");
  if (!codec.begin()) {
    Serial.println("Failed to initialize codec!");
  }
  codec.reset();
  // Step 1: Set codec interface to I2S with 16-bit data
  Serial.println("Configuring codec interface...");
  if (!codec.setCodecInterface(TLV320DAC3100_FORMAT_I2S, TLV320DAC3100_DATA_LEN_16)) {
    Serial.println("Failed to configure codec interface!");
  }
  
  // Step 2: Configure clock - using PLL with BCLK as input
  Serial.println("Configuring codec clocks...");
  if (!codec.setCodecClockInput(TLV320DAC3100_CODEC_CLKIN_PLL) ||
      !codec.setPLLClockInput(TLV320DAC3100_PLL_CLKIN_BCLK)) {
    Serial.println("Failed to configure codec clocks!");
  }
  
  // Step 3: Set up PLL - these values work well for 44.1kHz sample rate
  if (!codec.setPLLValues(1, 1, 8, 0)) {
    Serial.println("Failed to configure PLL values!");
  }
  
  // Step 4: Configure DAC dividers
  if (!codec.setNDAC(true, 8) ||
      !codec.setMDAC(true, 2) ||
      !codec.setDOSR(128)) {
    Serial.println("Failed to configure DAC dividers!");
  }
  
  // Step 5: Power up PLL
  if (!codec.powerPLL(true)) {
    Serial.println("Failed to power up PLL!");
  }
  
  // Step 6: Configure DAC path - power up both left and right DACs
  Serial.println("Configuring DAC path...");
  if (!codec.setDACDataPath(true, true, 
                           TLV320_DAC_PATH_NORMAL,
                           TLV320_DAC_PATH_NORMAL,
                           TLV320_VOLUME_STEP_1SAMPLE)) {
    Serial.println("Failed to configure DAC data path!");
  }
  
  // Step 7: Route DAC output to headphone
  if (!codec.configureAnalogInputs(TLV320_DAC_ROUTE_MIXER, // Left DAC to mixer
                                   TLV320_DAC_ROUTE_MIXER, // Right DAC to mixer
                                   false, false, false,    // No AIN routing
                                   false)) {               // No HPL->HPR
    Serial.println("Failed to configure DAC routing!");
  }
  
  // Step 8: Unmute DAC and set volume (higher for testing)
  Serial.println("Setting DAC volume...");
  if (!codec.setDACVolumeControl(
          false, false, TLV320_VOL_INDEPENDENT) || // Unmute both channels
      !codec.setChannelVolume(false, 18) ||        // Left DAC +0dB
      !codec.setChannelVolume(true, 18)) {         // Right DAC +0dB
    Serial.println("Failed to configure DAC volume control!");
  }
  

  if (!codec.setChannelVolume(false, 12.0) ||
      !codec.setChannelVolume(true, 12.0)) {
    Serial.println("Failed to set DAC channel volumes!");
  }
  
  if (!codec.enableSpeaker(true) ||                // Dis/Enable speaker amp
      !codec.configureSPK_PGA(TLV320_SPK_GAIN_6DB, // Set gain to 6dB
                              true) ||             // Unmute
      !codec.setSPKVolume(true, 0)) { // Enable and set volume to 0dB
    Serial.println("Failed to configure speaker output!");
  }

  // Initialize I2S peripheral
  Serial.println("Initializing I2S...");
  i2s.setBCLK(pBCLK);
  i2s.setDATA(pDOUT);
  i2s.setBitsPerSample(16);

}

void loop1() {
  // the main loop will tell us when it wants us to play!
    play_i2s(startupAudioData, sizeof(startupAudioData), startupSampleRate);
    delay(1000);
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
    uint16_t sample = (uint16_t)data[i] << 6; // our data is 10 bit but we want 16 bit so we add some gain
    // write the same sample twice, once for left and once for the right channel
    i2s.write(sample);
    i2s.write(sample);
  }
  i2s.end();
}
