#include "i2c.h"
#include "HT16K33.h"

HT16K33::HT16K33(uint8_t _addr) {
  i2c_addr=_addr;
}

void HT16K33::init() {
  i2cInit();
  clearDisplay();
  sendCommand(0x21);
  sendCommand(0x81);
  setBrightness(INITIAL_BRIGHTNESS);
}

void HT16K33::sendCommand(uint8_t c) {
  writeRegister(i2c_addr, c);
}

void HT16K33::setBrightness(uint8_t b) {
  brightness=b;
  sendCommand(0xE0 | brightness);
}

void HT16K33::increaseBrightness() {
  if (brightness<MAX_BRIGHTNESS) {
    brightness++;
    setBrightness(brightness);
  }
}

void HT16K33::decreaseBrightness() {
  if (brightness>MIN_BRIGHTNESS) {
    brightness--;
    setBrightness(brightness);
  }
}

void HT16K33::storeToBuffer(uint8_t* matrix) {
  for (uint8_t i=0;i<16;i++) buffer[i]=matrix[i];
}

void HT16K33::refreshDisplay() {
  uint16_t transposedBuffer[8];
  for (uint8_t i=0;i<8;i++) {
    uint16_t val=0;
    for (uint8_t j=0;j<16;j++)  {
      uint8_t bitVal=(buffer[j]>>i)&1;
      uint8_t shiftVal=j;
      val+=(bitVal<<shiftVal);
    }
    transposedBuffer[i]=val;
  }
  writeRegisters(i2c_addr, DISP_REGISTER, 8, transposedBuffer);
}

void HT16K33::clearDisplay() {
  uint16_t zero[8] = {0};
  writeRegisters(i2c_addr, DISP_REGISTER, 8, zero);
}

void HT16K33::readButtons() {
  previousButtonState = currentButtonState;
  currentButtonState = readRegister(i2c_addr, KEYS_REGISTER);
  
  for (uint8_t i=0;i<8;i++) {
    if ( !((previousButtonState>>i)&1) && ((currentButtonState>>i)&1) ) buttonFirstPress|=_BV(i);
    else buttonFirstPress&=~_BV(i);
    
    if ( ((previousButtonState>>i)&1) && ((currentButtonState>>i)&1) ) {
      if (buttonHoldTime[i]<0xFFFF) buttonHoldTime[i]+=1;
    }
    else buttonHoldTime[i]=0;
  }
}

bool HT16K33::getButtonFirstPress(uint8_t i) {
  return (buttonFirstPress>>i)&1;
}

uint16_t HT16K33::getButtonHoldTime(uint8_t i) {
  return buttonHoldTime[i];
}

bool HT16K33::allowToMove(uint8_t i, uint16_t time, uint8_t rate) {
  // if first press, or hold time >time (time/50=sec) and %rate=0 (to reduce the rate) 
  return (getButtonFirstPress(i) || (getButtonHoldTime(i)>time && getButtonHoldTime(i)%rate==0));
}
