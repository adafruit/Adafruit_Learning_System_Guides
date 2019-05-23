#include "Arduino.h"

// display size information
#define X_MIN  0
#define X_MAX  7
#define Y_MIN  0
#define Y_MAX 15

class Paint{
  private:
    // cursor coordinates
    uint8_t cursorX;
    uint8_t cursorY;  
    // cursor visibility and flash control
    bool cursorVisible;
    uint8_t flashDisableCounter;
    uint8_t canvas[16];
    uint8_t activeCanvas[16];
    
    void turnOnCursor();
    void turnOffCursor();
    bool readCanvas(uint8_t x, uint8_t y);
    
  public: 
    Paint(int8_t x, int8_t y);
    void flashCursor();                    // flash changes the visiblity (bool cursorVisible) of the cursor by calling turnOnCursor and turnOffCursor
    void moveCursor(int8_t dx, int8_t dy);
    void clearCanvas();
    void draw();
    
    uint8_t* getActiveCanvas();
};
