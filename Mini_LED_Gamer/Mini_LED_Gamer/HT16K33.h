#include "Arduino.h"

#define DISP_REGISTER 0x00
#define KEYS_REGISTER 0x40
#define MAX_BRIGHTNESS 12
#define MIN_BRIGHTNESS 0
#define INITIAL_BRIGHTNESS 1

class HT16K33 {
  private:
    uint8_t i2c_addr;
    uint8_t brightness;
    uint8_t buffer[16];
    
    // all four variables are updated in readButtons()
    uint8_t previousButtonState;  // stored in MSB First format: B7, ... , B0
    uint8_t currentButtonState;   // stored in MSB First format: B7, ... , B0
    uint8_t buttonFirstPress;     // stored in MSB First format: B7, ... , B0
    uint16_t buttonHoldTime[8];    // stored in LSB First format: B0, ... , B7
    
    uint16_t* transposeMatrix(uint8_t* matrix);
    void sendCommand(uint8_t c);
    void setBrightness(uint8_t b);
    
  public:
    HT16K33(uint8_t _addr);
    void init();
    void increaseBrightness();
    void decreaseBrightness();
    
    void storeToBuffer(uint8_t* matrix);
    void refreshDisplay();
    void clearDisplay();
    void readButtons();  // only reads the first byte of the key scan register becasue only the first 7 keys are used on this device
    bool getButtonFirstPress(uint8_t i);
    uint16_t getButtonHoldTime(uint8_t i);
    bool allowToMove(uint8_t i, uint16_t time, uint8_t rate);
};
