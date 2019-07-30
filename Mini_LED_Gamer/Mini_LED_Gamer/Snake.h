#include "Arduino.h"

class Snake {
  private:
    uint8_t foodX; //(0-7)
    uint8_t foodY; //(0-15)
    uint16_t snakeLength;
    int8_t snakeHeadX;
    int8_t snakeHeadY;
    int8_t snakeHeadDX;
    int8_t snakeHeadDY;
    uint8_t snakeBoard[16][8];
    uint8_t activeSnakeBoard[16];
    unsigned long lastSnakeMoveTime;
    bool allowToChangeDirection;
    
    void placeFood();
    bool moveSnake();  // return true if move is valid
    void gameOver();
    
  public:
    bool gameRunning;
    void init();
    void run();
    void changeDirection(int8_t dx, int8_t dy);  // should not run twice 
    uint8_t* getActiveBoard();
};
