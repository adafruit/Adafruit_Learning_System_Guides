#include "Arduino.h"

// display size information
#define X_MIN  0
#define X_MAX  7
#define Y_MIN  0
#define Y_MAX 15
#define WIDTH  8
#define HEIGHT 16

class Tetris{
  private:
    // Stores the dead blocks with 1 representing a dead block, and 0 a blank grid 
    uint8_t deadTetrisBoard[16];
    // deadTetrisBoard and the currentPiece is merged to form activeTetrisBoard, 
    uint8_t activeTetrisBoard[16];
    // Piece variables
    uint8_t* currentPiece;
    int8_t currentPieceX;  // tracks the X coordinate of the (currentPiece[0]>>7) 
    int8_t currentPieceY;  // tracks the Y coordinate of the (currentPiece[0]>>7)
    // Game variables
    bool moveDisabled;
    uint8_t totalLinesCleared;
    uint16_t timeInterval;
    unsigned long lastMoveTime;
    unsigned long lastLandedTime;
    
    void generatePiece();  // randomly generate a piece from piecesGenerated
    bool checkIfLanded();
    bool clearLines();  // returns false if no line is cleared
    void flashClearedLines(uint8_t* temp);
    void convertActiveToDead();
    // merges the deadTetrisBoard and the currentPiece to form the activeTetrisBoard
    // unsuccessful merge = currentPiece out of bounds or collision between currentPiece and deadTetrisBoard
    bool mergeTetrisBoard();
    void gameOver();  

  public:
    bool gameRunning; 
    void init();
    void run();
    void movePiece(int8_t dx, int8_t dy);
    void rotatePiece();  
    void dropPiece();
    uint8_t* getActiveBoard();
};
