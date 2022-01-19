// GUItool: begin automatically generated code
AudioSynthWaveform       wave0;          //xy=502.74795150756836,82.7552137374878
AudioSynthWaveform       wave1;      //xy=504.28649139404297,117.86524295806885
AudioSynthWaveform       wave2;      //xy=503.2865982055664,153.0081024169922
AudioSynthWaveform       wave3;      //xy=502.8580284118653,188.86524295806885
AudioMixer4              mixer0;         //xy=633.7151184082031,100.00811004638672
AudioEffectEnvelope      env0;           //xy=758.612813949585,54.04482841491699
AudioFilterStateVariable filter0;        //xy=888.6010780334473,60.850419998168945
AudioMixer4              mixerA;         //xy=1010.7359161376953,171.30673599243164
AudioMixer4              mixerL;      //xy=1196.8192749023438,210.86235809326172
AudioMixer4              mixerR;     //xy=1198.2637329101562,277.8345947265625
AudioOutputAnalogStereo  audioOut;       //xy=1360.3193969726562,250.61236572265625
AudioConnection          patchCord1(wave0, 0, mixer0, 0);
AudioConnection          patchCord2(wave3, 0, mixer0, 3);
AudioConnection          patchCord3(wave2, 0, mixer0, 2);
AudioConnection          patchCord4(wave1, 0, mixer0, 1);
AudioConnection          patchCord5(mixer0, env0);
AudioConnection          patchCord6(env0, 0, filter0, 0);
AudioConnection          patchCord7(filter0, 0, mixerA, 0);
AudioConnection          patchCord8(mixerA, 0, mixerL, 0);
AudioConnection          patchCord9(mixerA, 0, mixerR, 0);
AudioConnection          patchCord10(mixerL, 0, audioOut, 0);
AudioConnection          patchCord11(mixerR, 0, audioOut, 1);
// GUItool: end automatically generated code
