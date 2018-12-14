/*
  Audio Library on Trellis M4
  Demo of the audio sweep function.
  The user specifies the amplitude,
  start and end frequencies (which can sweep up or down)
  and the length of time of the sweep.
   */

#include <Audio.h>
// Paste your Audio System Design Tool code below this line:
// GUItool: begin automatically generated code
AudioSynthToneSweep      tonesweep1;     //xy=531.0833129882812,166.08334350585938
AudioOutputAnalogStereo  audioOutput;          //xy=727.0833129882812,166.08334350585938
AudioConnection          patchCord1(tonesweep1, 0, audioOutput, 0);
AudioConnection          patchCord2(tonesweep1, 0, audioOutput, 1);
// GUItool: end automatically generated code

float t_ampx = 0.05;  // Amplitude
int t_lox = 10;  // Low frequency
int t_hix = 22000;  // High frequency
float t_timex = 10; // Length of time of the sweep in seconds


void setup(void) {

  Serial.begin(9600);
  //while (!Serial) ;
  delay(3000);

  AudioMemory(6);

  Serial.println("setup done");

  if(!tonesweep1.play(t_ampx,t_lox,t_hix,t_timex)) {
    Serial.println("AudioSynthToneSweep - begin failed");
    while(1);
  }
  // wait for the sweep to end
  while(tonesweep1.isPlaying());

  // and now reverse the sweep
  if(!tonesweep1.play(t_ampx,t_hix,t_lox,t_timex)) {
    Serial.println("AudioSynthToneSweep - begin failed");
    while(1);
  }
  // wait for the sweep to end
  while(tonesweep1.isPlaying());
  Serial.println("Done");
}

void loop(void){
}
