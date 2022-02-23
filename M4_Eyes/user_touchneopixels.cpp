// SPDX-FileCopyrightText: 2019 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#if 0 // Change to 1 to enable this code (must enable ONE user*.cpp only!)

#include "globals.h"

static uint32_t lastTouchSample;
static uint32_t lastBehaviorChange;
static uint32_t lastWave;

static int currentBehavior = 0;

static int colorIndex  = 0;

const uint32_t SAMPLE_TIME = 50000;
const uint32_t TOUCH_SAMPLE_TIME = SAMPLE_TIME * 15;
static uint8_t currentStep = 100;
static int direction = -3;
static uint32_t lastColorShift;
const int N_HEARTBEAT_FRAMES = 20;
static uint8_t currentHeartBeatStep = 0;
static uint8_t heartbeat[] = { 80, 80, 80, 80, 20,
                              20, 120, 255, 255, 120,
                              80, 40, 20, 0, 0,
                              0, 0, 0, 0, 0 };

const int N_BREATH_IN_FRAMES = 45;
static uint8_t currentBreathStep = 0;
static uint16_t breathIn[] = { 7, 14, 21, 28, 35,
                            42, 49, 56, 63, 70,
                            77, 84, 91, 98, 105,
                            112, 119, 126, 133, 140,
                            147, 154, 161, 168, 175,
                            182, 189, 196, 203, 210,
                            217, 224, 231, 238, 255,
                            255, 255, 255, 255, 255,
                            255, 255, 255, 255, 255};

const int N_BREATH_OUT_FRAMES = 45;
static uint16_t breathOut[] = { 255, 255, 255, 255, 255, 255, 255, 255, 255, 
                                255, 255, 238, 231, 224, 217, 210, 203, 196, 
                                189, 182, 175, 168, 161, 154, 147, 140, 133, 
                                126, 119, 112, 105, 98, 91, 84, 77, 70, 63, 
                                56, 49, 42, 35, 28, 21, 14, 7};

static int breathFrames = N_BREATH_IN_FRAMES;
static uint16_t *breath = breathIn;

void setGradientPixelColor(uint16_t ledPosition, uint16_t step, float redRatio, float greenRatio, float blueRatio)
{
    float green = step * greenRatio;
    float red = step * redRatio;
    float blue = step * blueRatio;
    arcada.pixels.setPixelColor(ledPosition, red, green, blue);
}
 
void stepGreenBlackGradient(uint16_t ledPosition, uint16_t step) {
    setGradientPixelColor(ledPosition, step, 0, 1, 0);
}
 
void stepOrangeBlackGradient(uint16_t ledPosition, uint16_t step) {
    setGradientPixelColor(ledPosition, step, 1, 0.64453125, 0);
}
 
void stepPurpleBlackGradient(uint16_t ledPosition, uint16_t step) {
    setGradientPixelColor(ledPosition, step, 0.8815, 0.4028, 1);
}
 
void stepRedBlackGradient(uint16_t ledPosition, uint16_t step) {
    setGradientPixelColor(ledPosition, step, 1, 0, 0);
}
 
void stepYellowBlackGradient(uint16_t ledPosition, uint16_t step) {
    setGradientPixelColor(ledPosition, step, 1, 1, 0);
}
 
void stepWhiteBlackGradient(uint16_t ledPosition, uint16_t step) {
    setGradientPixelColor(ledPosition, step, 1, 1, 1);
}
 
void stepRedOrangeGradient(uint16_t ledPosition, uint16_t step) {
    int red = 255;
    float green = step * .647;
    int blue = 0;
    arcada.pixels.setPixelColor(ledPosition, red, green, blue);
}
 
void stepOrangeYellowGradient(uint16_t ledPosition, uint16_t step) {
    int red = 255;
    float green = 165 + (step % 90);
    int blue = 0;
    arcada.pixels.setPixelColor(ledPosition, red, green, blue);
}
 
void stepYellowGreenGradient(uint16_t ledPosition, uint16_t step) {
    int red = 255 - step * 2;
    float green = 255 - (step * 1.5);
    int blue = 0;
    arcada.pixels.setPixelColor(ledPosition, red, green, blue);
}
 
void stepGreenBlueGradient(uint16_t ledPosition, uint16_t step) {
    int red = 0;
    float green = 128 - step;
    int blue = step;
    arcada.pixels.setPixelColor(ledPosition, red, green, blue);
}
 
void stepBlueIndigoGradient(uint16_t ledPosition, uint16_t step) {
    int red = step;
    float green = 0;
    int blue = 255 - step;
    arcada.pixels.setPixelColor(ledPosition, red, green, blue);
}
 
void stepIndigoVioletGradient(uint16_t ledPosition, uint16_t step) {
    int red = 75+step;
    float green = step;
    int blue = 130+step;
    arcada.pixels.setPixelColor(ledPosition, red, green, blue);
}
 
void stepVioletRedGradient(uint16_t ledPosition, uint16_t step) {
    int red = 238+(step*.17);
    float green = 130 - step;
    int blue = 238 - (step * 2);
    arcada.pixels.setPixelColor(ledPosition, red, green, blue);
}

typedef void (*StepColorGradient)(uint16_t, uint16_t);

static uint16_t rainbowWalkLEDSteps[] = {5, 6, 1, 4};
const int N_RAINBOW_GRADIENTS = 7;
// ROY G BIV
static StepColorGradient rainbowWalkGradients[] = {  &stepRedOrangeGradient,
                                                     &stepOrangeYellowGradient,
                                                     &stepYellowGreenGradient,
                                                     &stepGreenBlueGradient,
                                                     &stepBlueIndigoGradient,
                                                     &stepIndigoVioletGradient,
                                                     &stepVioletRedGradient,
                                                  };
static uint32_t lastRainbowColorShift;

void advanceRainbowWalk(void) {
    uint16_t i;
    for(i = 0; i < arcada.pixels.numPixels(); i++) {
        rainbowWalkGradients[rainbowWalkLEDSteps[i]](i, currentStep);
    }
    currentStep = currentStep + 25;
    if(currentStep > 100) {
      currentStep = 0;
      for(i = 0; i < arcada.pixels.numPixels(); i++) {
        rainbowWalkLEDSteps[i] = rainbowWalkLEDSteps[i] + 1;
        if(rainbowWalkLEDSteps[i] >= N_RAINBOW_GRADIENTS) {
          rainbowWalkLEDSteps[i] = 0;
        }
      }
    }
    arcada.pixels.show();
}

static StepColorGradient breathGradient = &stepRedBlackGradient;

void advanceBreath(void)
{  
    uint16_t i;
    for(i = 0; i < arcada.pixels.numPixels(); i++) {
        breathGradient(i, breath[currentBreathStep]);
    }
    arcada.pixels.show();
    
    if(currentBreathStep == breathFrames - 1) {
        currentBreathStep = 0;
        if(breath == breathIn) {
          breath = breathOut;
          breathFrames = N_BREATH_OUT_FRAMES;
          breathGradient = &stepRedBlackGradient;
        }
        else {          
          breath = breathIn;
          breathFrames = N_BREATH_IN_FRAMES;
          breathGradient = &stepRedBlackGradient;
        }
    }
    else {
        currentBreathStep = currentBreathStep + 1;
    }
}
 
void advanceHalloweenGradients(void) {
    for(int i = 0; i < arcada.pixels.numPixels(); i++) {
        switch (colorIndex) {
            case 0:
                stepOrangeBlackGradient(i, currentStep);
                break;
            case 1:
                stepRedBlackGradient(i, currentStep);
                break;
            case 2:
                stepYellowBlackGradient(i, currentStep);
                break;
            default:
                stepWhiteBlackGradient(i, currentStep);
                break;
        }
    }
    arcada.pixels.show();

    if(currentStep <= 0) {
        direction = 3;
        // shift to next color
        colorIndex = colorIndex + 1;
        if(colorIndex >= arcada.pixels.numPixels()) {
            colorIndex = 0;
        }
    }
    else if(currentStep >= 100) {
        direction = -3;
    }
    currentStep = currentStep + direction;
}
 
void advanceHeartBeat(void) {
    int i;
    for(i = 0; i < arcada.pixels.numPixels(); i++) {
        stepRedBlackGradient(i, heartbeat[currentHeartBeatStep]);
    }
    arcada.pixels.show();
    
    if(currentHeartBeatStep == N_HEARTBEAT_FRAMES - 1) {
        currentHeartBeatStep = 0;
    } else {
        currentHeartBeatStep = currentHeartBeatStep + 1;
    }
}

void changeBehavior(int newBehavior, uint32_t timeOfChange) {  
    currentBehavior = newBehavior;
    lastBehaviorChange = timeOfChange;
}

void user_setup(void) {
  lastBehaviorChange, lastWave, lastColorShift, lastRainbowColorShift, lastTouchSample = micros();
  arcada.pixels.setBrightness(255);
  advanceHalloweenGradients();
  changeBehavior(0, micros());
}

void user_loop(void) {
  uint32_t elapsedSince = micros();
  if(elapsedSince - lastTouchSample > TOUCH_SAMPLE_TIME) {
    lastTouchSample = elapsedSince;
    uint8_t pressed_buttons = arcada.readButtons();
    uint8_t justpressed_buttons = arcada.justPressedButtons();
    
    if (justpressed_buttons & ARCADA_BUTTONMASK_UP){
      changeBehavior(0, elapsedSince);
    }
    else if(justpressed_buttons & ARCADA_BUTTONMASK_DOWN) {
      changeBehavior(1, elapsedSince);
    }
    else if(justpressed_buttons & ARCADA_BUTTONMASK_LEFT) {
      changeBehavior(2, elapsedSince);
    }
    else if(justpressed_buttons & ARCADA_BUTTONMASK_RIGHT) {
      changeBehavior(3, elapsedSince);
    }
  }
    
  if (elapsedSince - lastWave > SAMPLE_TIME) {
    lastWave = elapsedSince;
    switch (currentBehavior) {
      case 0:
        advanceHalloweenGradients();
        break;
      case 1:
        advanceHeartBeat();
        break;
      case 2:
        advanceBreath();
        break;
      case 3:
        advanceRainbowWalk();
        break;
      default:        
        arcada.pixels.fill(0, 0, 0);
        arcada.pixels.show();
        break;
    }

    if ((elapsedSince - lastBehaviorChange) > (SAMPLE_TIME * 1000)) {
      lastBehaviorChange = elapsedSince;
      currentBehavior++;
      currentBehavior %= 4;
    }
  }
}

#endif
