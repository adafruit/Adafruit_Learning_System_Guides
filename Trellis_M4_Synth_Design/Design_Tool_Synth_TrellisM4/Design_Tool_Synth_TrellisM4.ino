/* Audio library demonstration - pocket synth with C major scale and 4 wave types */
//each row is a different waveform, envelope, and effect set in major scale
// row 0 sine, soft attack, long release ADSR
// row 1 square, hard attack, moderate release, flanger effect
// row 2 sawtooth, hard attack, soft release, chorus effect
// row 3 triangle, medium attack, long release ADSR, multi tap delay

#include <Audio.h>
#include <Adafruit_NeoTrellisM4.h>

Adafruit_NeoTrellisM4 trellis = Adafruit_NeoTrellisM4();
// Paste your Audio System Design Tool code below this line:
// GUItool: begin automatically generated code
AudioSynthWaveform       wave0;          //xy=453.84613037109375,254.61540985107422
AudioSynthWaveform       wave1;          //xy=453.84613037109375,294.6154098510742
AudioSynthWaveform       wave2;          //xy=453.84613037109375,354.6154098510742
AudioSynthWaveform       wave3;          //xy=453.84613037109375,404.6154098510742
AudioEffectEnvelope      env0;           //xy=602.8461303710938,254.61540985107422
AudioEffectEnvelope      env1;           //xy=602.8461303710938,294.6154098510742
AudioEffectEnvelope      env2;           //xy=602.8461303710938,354.6154098510742
AudioEffectEnvelope      env3;           //xy=602.8461303710938,404.6154098510742
AudioEffectChorus        chorus1;        //xy=734.6796264648438,333.14093017578125
AudioEffectFlange        flange1;        //xy=737.7564392089844,284.6794891357422
AudioEffectDelay         delay1;         //xy=880.7692260742188,582.3077392578125
AudioMixer4              mixer1;         //xy=882.3076171875,284.6154327392578
AudioMixer4              mixerLeft;      //xy=1041.9999389648438,293.84617614746094
AudioMixer4              mixerRight;     //xy=1045.0768432617188,394.6153869628906
AudioOutputAnalogStereo  audioOut;       //xy=1212.8461303710938,354.6154098510742
AudioConnection          patchCord1(wave0, env0);
AudioConnection          patchCord2(wave1, env1);
AudioConnection          patchCord3(wave2, env2);
AudioConnection          patchCord4(wave3, env3);
AudioConnection          patchCord5(env0, 0, mixer1, 0);
AudioConnection          patchCord6(env1, flange1);
AudioConnection          patchCord7(env2, chorus1);
AudioConnection          patchCord8(env3, delay1);
AudioConnection          patchCord9(env3, 0, mixer1, 3);
AudioConnection          patchCord10(chorus1, 0, mixer1, 2);
AudioConnection          patchCord11(flange1, 0, mixer1, 1);
AudioConnection          patchCord12(delay1, 0, mixerLeft, 1);
AudioConnection          patchCord13(delay1, 1, mixerLeft, 2);
AudioConnection          patchCord14(delay1, 2, mixerRight, 1);
AudioConnection          patchCord15(delay1, 3, mixerRight, 2);
AudioConnection          patchCord16(mixer1, 0, mixerLeft, 0);
AudioConnection          patchCord17(mixer1, 0, mixerRight, 0);
AudioConnection          patchCord18(mixerLeft, 0, audioOut, 0);
AudioConnection          patchCord19(mixerRight, 0, audioOut, 1);
// GUItool: end automatically generated code

AudioSynthWaveform *waves[4] = {
&wave0, &wave1, &wave2, &wave3,
};
short wave_type[4] = {
  WAVEFORM_SINE,
  WAVEFORM_SQUARE,
  WAVEFORM_SAWTOOTH,
  WAVEFORM_TRIANGLE,
};
float cmaj_low[8] = { 130.81, 146.83, 164.81, 174.61, 196.00, 220.00, 246.94, 261.63 };
float cmaj_high[8] = { 261.6, 293.7, 329.6, 349.2, 392.0, 440.0, 493.9, 523.3 };
AudioEffectEnvelope *envs[4] = {
  &env0, &env1, &env2, &env3,
};
int n_chorus = 5;
#define CHORUS_DELAY_LENGTH (400*AUDIO_BLOCK_SAMPLES)
short chorusDelayline[CHORUS_DELAY_LENGTH];

#define FLANGER_DELAY_LENGTH (6*AUDIO_BLOCK_SAMPLES)
short flangerDelayline[FLANGER_DELAY_LENGTH];

void setup(){
  Serial.begin(115200);
  //while (!Serial);

  trellis.begin();
  trellis.setBrightness(255);

  AudioMemory(120);

  //Initialize the waveform nodes
  wave0.begin(0.85, 50, WAVEFORM_SINE);
  wave1.begin(0.4, 50, WAVEFORM_SQUARE);
  wave2.begin(0.6, 50, WAVEFORM_SAWTOOTH);
  wave3.begin(0.4, 50, WAVEFORM_TRIANGLE);

  // reduce the gain on some channels, so half of the channels
  // are "positioned" to the left, half to the right, but all
  // are heard at least partially on both ears
  mixerLeft.gain(0, 0.3);
  mixerLeft.gain(1, 0.1);
  mixerLeft.gain(2, 0.5);

  mixerRight.gain(0, 0.3);
  mixerRight.gain(1, 0.5);
  mixerRight.gain(2, 0.1);


  // set envelope parameters, for pleasing sound :-)
  env0.attack(300);
  env0.hold(2);
  env0.decay(30);
  env0.sustain(0.6);
  env0.release(1200);

  env1.attack(10);
  env1.hold(2);
  env1.decay(30);
  env1.sustain(0.6);
  env1.release(400);

  env2.attack(10);
  env2.hold(20);
  env2.decay(30);
  env2.sustain(0.6);
  env2.release(1000);

  env3.attack(10);
  env3.hold(2);
  env3.decay(30);
  env3.sustain(0.6);
  env3.release(600);

  // set delay parameters
  delay1.delay(0, 110);
  delay1.delay(1, 660);
  delay1.delay(2, 220);
  delay1.delay(3, 1220);

  // set effects parameters
  chorus1.begin(chorusDelayline, CHORUS_DELAY_LENGTH, n_chorus);
  flange1.begin(flangerDelayline, FLANGER_DELAY_LENGTH, FLANGER_DELAY_LENGTH/4, FLANGER_DELAY_LENGTH/4, .5);


  Serial.println("setup done");

  // Initialize processor and memory measurements
  AudioProcessorUsageMaxReset();
  AudioMemoryUsageMaxReset();
}

void noteOn(int num){
  int voice = num/8;
  float *scale;
  if(voice == 0 || voice == 1) scale = cmaj_low;
  else scale = cmaj_high;
  AudioNoInterrupts();
  waves[voice]->frequency(scale[num%8]);
  envs[voice]->noteOn();
  AudioInterrupts();
}

void noteOff(int num){
  int voice = num/8;
  envs[voice]->noteOff();
}

void loop() {
  trellis.tick();

  while(trellis.available())
  {
    keypadEvent e = trellis.read();
    int keyindex = e.bit.KEY;
    if(e.bit.EVENT == KEY_JUST_PRESSED){
        trellis.setPixelColor(keyindex, Wheel(keyindex * 255 / 32)); // rainbow!
        noteOn(keyindex);
      }
    else if(e.bit.EVENT == KEY_JUST_RELEASED){
        noteOff(keyindex);
        trellis.setPixelColor(keyindex, 0);
      }
   }
  delay(10);
}


// Input a value 0 to 255 to get a color value.
// The colours are a transition r - g - b - back to r.
uint32_t Wheel(byte WheelPos) {
  WheelPos = 255 - WheelPos;
  if(WheelPos < 85) {
    return Adafruit_NeoPixel::Color(255 - WheelPos * 3, 0, WheelPos * 3);
  }
  if(WheelPos < 170) {
    WheelPos -= 85;
    return Adafruit_NeoPixel::Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
  WheelPos -= 170;
  return Adafruit_NeoPixel::Color(WheelPos * 3, 255 - WheelPos * 3, 0);
}
