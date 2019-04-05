// Trellis M4 Audio Workshop
// shows how to alter pitch with accelerometer
// Waveform Mod

#include <Audio.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_ADXL343.h>
#include "Adafruit_NeoTrellisM4.h"
#include <elapsedMillis.h>

Adafruit_ADXL343 accel = Adafruit_ADXL343(123, &Wire1);

// The NeoTrellisM4 object is a keypad and neopixel strip subclass
// that does things like auto-update the NeoPixels and stuff!
Adafruit_NeoTrellisM4 trellis = Adafruit_NeoTrellisM4();
// Paste your Audio System Design Tool code below this line:
// GUItool: begin automatically generated code
AudioSynthWaveform       waveform1;      //xy=592.7221984863281,187.38888549804688
AudioOutputAnalogStereo  audioOutput;          //xy=777.0833129882812,189.08334350585938
AudioConnection          patchCord1(waveform1, 0, audioOutput, 0);
AudioConnection          patchCord2(waveform1, 0, audioOutput, 1);
// GUItool: end automatically generated code


int xbend = 64;
int ybend = 64;
int last_xbend = 64;
int last_ybend = 64;

int count=1;

void setup() {
  trellis.begin();
  trellis.show();  // Initialize w all pixels off
  trellis.setBrightness(255);

  if(!accel.begin()) {
  Serial.println("No accelerometer found");
  while(1);
}
  AudioMemory(10);
  // Initialize processor and memory measurements
  AudioProcessorUsageMaxReset();
  AudioMemoryUsageMaxReset();
  Serial.begin(115200);
  waveform1.begin(WAVEFORM_SAWTOOTH);
  delay(1000);
}


void loop() {
  waveform1.frequency(110 + (ybend * 2));
  waveform1.amplitude(0.05);
  wait(5);
}

void wait(unsigned int milliseconds){
  elapsedMillis msec=0;
  while (msec <= milliseconds){
    trellis.tick();
    while(trellis.available()) {
      keypadEvent e = trellis.read();
      Serial.print((int)e.bit.KEY);
      int keyindex = e.bit.KEY;
      if(e.bit.EVENT == KEY_JUST_PRESSED){
        Serial.println(" pressed");
        trellis.setPixelColor(keyindex, Wheel(keyindex * 255 / 32)); // rainbow!
        }
      else if(e.bit.EVENT == KEY_JUST_RELEASED){
        Serial.println(" released");
        trellis.setPixelColor(keyindex, 0);
        }
     }

   // Check for accelerometer
    sensors_event_t event;
    accel.getEvent(&event);

    //check if it's been moved a decent amount
    if (abs(event.acceleration.x) < 2.0) {  // 2.0 m/s^2
    // don't make any bend unless they've really started moving it
     xbend = 64;
   }
    else {
      if (event.acceleration.x > 0) {
      xbend = ofMap(event.acceleration.x, 2.0, 10.0, 63, 0, true);  // 2 ~ 10 m/s^2 is upward bend
    }
    else {
        xbend = ofMap(event.acceleration.x, -2.0, -10.0, 64, 127, true);  // -2 ~ -10 m/s^2 is downward bend
      }
    }
    if (xbend != last_xbend) {
      Serial.print("X mod: "); Serial.println(xbend);
      last_xbend = xbend;
    }

    if (abs(event.acceleration.y) < 2.0) {  // 2.0 m/s^2
     ybend = 64;
   }
    else {
      if (event.acceleration.y > 0) {
      ybend = ofMap(event.acceleration.y, 2.0, 10.0, 63, 0, true);  // 2 ~ 10 m/s^2 is upward bend
    }
    else {
        ybend = ofMap(event.acceleration.y, -2.0, -10.0, 64, 127, true);  // -2 ~ -10 m/s^2 is downward bend
      }
    }
    if (ybend != last_ybend) {
      Serial.print("Y mod: "); Serial.println(ybend);
      last_ybend = ybend;
    }
  }
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

// floating point map
float ofMap(float value, float inputMin, float inputMax, float outputMin, float outputMax, bool clamp) {
    float outVal = ((value - inputMin) / (inputMax - inputMin) * (outputMax - outputMin) + outputMin);

    if (clamp) {
      if (outputMax < outputMin) {
        if (outVal < outputMax)  outVal = outputMax;
        else if (outVal > outputMin)  outVal = outputMin;
      } else {
        if (outVal > outputMax) outVal = outputMax;
        else if (outVal < outputMin)  outVal = outputMin;
      }
    }
    return outVal;

}
