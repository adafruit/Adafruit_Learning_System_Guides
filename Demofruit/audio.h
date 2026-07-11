// SPDX-FileCopyrightText: 2026 John Park with Claude Opus 4.8 for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// audio.h — shared MOD music for the Fruit Jam Demoscene Sampler
// TLV320DAC3100 codec + arduino-pico I2S (PIO/DMA) + pocketmod.
//
// Usage: smpAudioInit(data, size) once after display init;
//        smpAudioPump() every loop pass (non-blocking — renders only
//        what the DMA FIFO can accept, then returns).
// Core0 only: never call from core1.

#pragma once
#include <Wire.h>
#include <I2S.h>
#include <Adafruit_TLV320DAC3100.h>

extern "C" {
#include "pocketmod.h"   // implementation in pocketmod.c (compiled as C)
}

#define SMP_AUDIO_RATE   22050
#define SMP_AUDIO_GAIN   0.6f   // fixed — downstream amps own the volume knob
#define SMP_TLV_RESET    22     // shared peripheral reset (TLV320 + ESP32-C6)
#define SMP_AUDIO_CHUNK  32     // stereo frames per render slice

// Onboard speaker is OFF by default. To enable it, jumper the A1 pad
// (GPIO41) on the Fruit Jam's GPIO header to GND. Read once at init with an
// internal pull-up: jumpered = LOW = speaker on; open = HIGH = speaker off.
// (The board's jack has no usable insertion-detect wiring, so this hardware
// jumper replaces auto-muting — see project notes.)
#define SMP_SPK_JUMPER_PIN  A1

static Adafruit_TLV320DAC3100 _smpCodec;
static I2S                    _smpI2S(OUTPUT);
static pocketmod_context      _smpMod;
static bool                   _smpAudioOK = false;
static float                  _smpChunk[SMP_AUDIO_CHUNK * 2];

// returns false on any failure — sampler runs silent rather than halting
static bool smpAudioInit(const void *modData, unsigned modSize) {
  pinMode(SMP_TLV_RESET, OUTPUT);
  digitalWrite(SMP_TLV_RESET, LOW);
  delay(100);
  digitalWrite(SMP_TLV_RESET, HIGH);
  delay(10);

  if (!_smpCodec.begin()) { Serial.println("audio: codec.begin failed"); return false; }

  // Read the speaker-enable jumper first: A1 (GPIO41) tied to GND = speaker on;
  // left open (default) = speaker fully off. Determines whether we power the
  // class-D speaker amp at all below. Headphone output is always configured.
  pinMode(SMP_SPK_JUMPER_PIN, INPUT_PULLUP);
  delayMicroseconds(50);                       // let the pull-up settle
  bool speakerOn = (digitalRead(SMP_SPK_JUMPER_PIN) == LOW);

  bool ok =
    _smpCodec.setCodecInterface(TLV320DAC3100_FORMAT_I2S,
                                TLV320DAC3100_DATA_LEN_16) &&
    _smpCodec.setCodecClockInput(TLV320DAC3100_CODEC_CLKIN_PLL) &&
    _smpCodec.setPLLClockInput(TLV320DAC3100_PLL_CLKIN_BCLK) &&
    _smpCodec.setPLLValues(1, 2, 32, 0) &&
    _smpCodec.setNDAC(true, 8) && _smpCodec.setMDAC(true, 2) &&
    _smpCodec.powerPLL(true) &&
    _smpCodec.setDACDataPath(true, true, TLV320_DAC_PATH_NORMAL,
                             TLV320_DAC_PATH_NORMAL,
                             TLV320_VOLUME_STEP_1SAMPLE) &&
    _smpCodec.configureAnalogInputs(TLV320_DAC_ROUTE_MIXER,
                                    TLV320_DAC_ROUTE_MIXER,
                                    false, false, false, false) &&
    _smpCodec.setDACVolumeControl(false, false, TLV320_VOL_INDEPENDENT) &&
    _smpCodec.setChannelVolume(false, 18) &&
    _smpCodec.setChannelVolume(true, 18) &&
    _smpCodec.configureHeadphoneDriver(true, true,
                                       TLV320_HP_COMMON_1_35V, false) &&
    _smpCodec.configureHPL_PGA(0, true) &&
    _smpCodec.configureHPR_PGA(0, true) &&
    _smpCodec.setHPLVolume(true, 6) &&
    _smpCodec.setHPRVolume(true, 6) &&
    _smpCodec.enableSpeaker(speakerOn) &&                     // power amp only if on
    _smpCodec.configureSPK_PGA(TLV320_SPK_GAIN_6DB, speakerOn) && // unmute only if on
    _smpCodec.setSPKVolume(speakerOn, 0);                    // route only if on
  if (!ok) { Serial.println("audio: codec config failed"); return false; }

  Serial.print("audio: onboard speaker ");
  Serial.println(speakerOn ? "ON (A1 jumpered to GND)"
                           : "OFF (jumper A1->GND to enable)");

  _smpI2S.setBCLK(26);          // LRCLK = BCLK+1 = 27 per board layout
  _smpI2S.setDATA(24);
  _smpI2S.setBitsPerSample(16);
  _smpI2S.setBuffers(8, 256);   // 8 x 256 words = 2048 stereo frames ~ 93ms
  if (!_smpI2S.begin(SMP_AUDIO_RATE)) {
    Serial.println("audio: i2s.begin failed"); return false;
  }

  if (!pocketmod_init(&_smpMod, modData, (int)modSize, SMP_AUDIO_RATE)) {
    Serial.println("audio: pocketmod_init failed (not a 4ch MOD?)");
    return false;
  }
  _smpAudioOK = true;
  Serial.println("audio: running");
  return true;
}

// Non-blocking: render and queue audio only while the FIFO has room.
static void smpAudioPump() {
  if (!_smpAudioOK) return;
  const int chunkBytes = SMP_AUDIO_CHUNK * 2 * (int)sizeof(int16_t);
  while (_smpI2S.availableForWrite() >= chunkBytes) {
    int bytes  = pocketmod_render(&_smpMod, _smpChunk, sizeof(_smpChunk));
    int frames = bytes / (int)(2 * sizeof(float));
    if (frames <= 0) break;
    for (int f = 0; f < frames; f++) {
      float l = _smpChunk[f*2]     * SMP_AUDIO_GAIN;
      float r = _smpChunk[f*2 + 1] * SMP_AUDIO_GAIN;
      if (l > 1.0f) l = 1.0f; if (l < -1.0f) l = -1.0f;
      if (r > 1.0f) r = 1.0f; if (r < -1.0f) r = -1.0f;
      _smpI2S.write16((int16_t)(l * 32767.0f), (int16_t)(r * 32767.0f));
    }
  }
}
