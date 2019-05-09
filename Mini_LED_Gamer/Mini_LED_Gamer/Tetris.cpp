#include "Tetris.h"
#include "Tetris_Tetrominoes.h"

void Tetris::run(){
  if (gameRunning) {
    // if piece has not landed,
    if (!checkIfLanded()) {
      // and the timeInterval has passed, move the piece down, and return
      if (millis()>lastMoveTime+timeInterval) {
        movePiece(0,1);
        return;
      }
    }
    // if the piece has landed,
    else {
      // and some lines are cleared, generate a new piece and return (start dropping again)
      if (clearLines()){
        generatePiece();
        return;
      }
      // and no line is cleared, give the player some time (400ms) to adjust the piece
      else {
        while (millis()<(lastLandedTime+400));
        // if the piece is quickly adjusted during the buffer period, return (start dropping again)
        if (!checkIfLanded()) return; 
        else {
          convertActiveToDead();
          generatePiece();
        }
      }
    }
  }
}

void Tetris::init() {
  for (uint8_t i=0;i<16;i++) {
    deadTetrisBoard[i]=0;
    activeTetrisBoard[i]=0;
  }
  generatePiece();
  totalLinesCleared=0;
  timeInterval=800;
  moveDisabled=false;
  gameRunning=true;
}

void Tetris::gameOver() {
  gameRunning=false;
  moveDisabled=true;
  Serial.println("Game Over");
}

void Tetris::generatePiece() {
  uint8_t i = random(7);
  currentPiece = (uint8_t*)piecesGenerated[i];
  currentPieceX = 0;
  currentPieceY = -2;
  if (!mergeTetrisBoard()) gameOver();
  lastMoveTime=millis();
}

void Tetris::movePiece(int8_t dx, int8_t dy) {
  currentPieceX+=dx;
  currentPieceY+=dy;
  if (!mergeTetrisBoard()) {
    currentPieceX-=dx;
    currentPieceY-=dy;
    mergeTetrisBoard();
    return;
  }
  if (dy==1) lastMoveTime=millis();
}

void Tetris::rotatePiece(){
  uint8_t* temp = currentPiece;
  for (uint8_t i=0;i<19;i++) {
    if (pieces[i]==currentPiece) {
      currentPiece=(uint8_t*)piecesRotated[i];
      if (!mergeTetrisBoard()) {
        currentPiece=temp;
        mergeTetrisBoard();
      }
      return;
    }
  }
}

void Tetris::dropPiece() {
  moveDisabled=true;
  while (!checkIfLanded()) movePiece(0,1);
  moveDisabled=false;
}

// Does not take care of the currentPiece out-of-bounds
bool Tetris::mergeTetrisBoard() {
  for (uint8_t i=0;i<16;i++) activeTetrisBoard[i]=deadTetrisBoard[i];
  for (int8_t y=0;y<4;y++) {
    for (int8_t x=0;x<8;x++) {
      bool b0 = (currentPiece[y]>>(7-x))&1;  // current piece has 1 at (x,y)
      if (b0 && (y+currentPieceY)>=0){  // the top bound is treated separately because we want the piece to be able to rotate at the very top
        bool b1 = ((y+currentPieceY)>15) || ((x+currentPieceX)<0) || ((x+currentPieceX)>7);  // b1: out of bounds
        if (b1 || (deadTetrisBoard[y+currentPieceY]>>(7-(x+currentPieceX)))&1) {  // deadTetrisBoard has 1 at (x+cx,y+cy)
          // out of bounds, or conflict between deadTetrisBoard and currentPiece
          // revert activeTetrisBoard back to deadTetrisBoard
          for (uint8_t i=0;i<16;i++) activeTetrisBoard[i] = deadTetrisBoard[i];
          return false;  
        }
        else {
          // if there is no conflict, then write 1 to (x+cx,y+cy) on activeTetrisBoard
          activeTetrisBoard[y+currentPieceY] |= _BV(7-(x+currentPieceX));
        }
      }
    }
  }
  return true;
}

uint8_t* Tetris::getActiveBoard(){
  return activeTetrisBoard;
}

bool Tetris::checkIfLanded() {
  for (int8_t y=0;y<4;y++) {
    for (int8_t x=0;x<8;x++) {
      bool b0 = (currentPiece[y]>>(7-x))&1;  // current piece has 1 at (x,y)
      if (b0) {
        bool b1 = (y+currentPieceY == Y_MAX);
        if (b1 || (deadTetrisBoard[y+currentPieceY+1]>>(7-(x+currentPieceX)))&1){ // deadTetrisBoard has 1 at (x+cx,y+cy+1)
          lastLandedTime=millis();
          return true;
        }
      }
    }
  }
  return false;
}

void Tetris::flashClearedLines(uint8_t* temp){
  moveDisabled=true;
  for (uint8_t n=0;n<2;n++) {
    for (uint8_t i=0;i<16;i++) activeTetrisBoard[i]=deadTetrisBoard[i];
    unsigned long time=millis();
    while (millis()<(time+100));
    for (uint8_t i=0;i<16;i++) activeTetrisBoard[i]=temp[i];
    time=millis();
    while (millis()<(time+100));
  }
  moveDisabled=false;
}

void Tetris::convertActiveToDead(){
  for (uint8_t i=0;i<16;i++) deadTetrisBoard[i]=activeTetrisBoard[i];
}

bool Tetris::clearLines(){
  uint8_t temp[16];
  uint8_t linesCleared=0;
  for (uint8_t i=0;i<16;i++) {
    uint8_t val = activeTetrisBoard[i];
    if (val==255) {
      temp[i]=0;
      linesCleared++;
    }
    else temp[i]=val;
  } 
  // if no line is cleared, return now, give the player some more time before convertActiveToDead()
  if (linesCleared==0)  return false;
  
  // if lines are cleared, convertActiveToDead(), add cleared lines to the total, then flash
  convertActiveToDead();
  totalLinesCleared+=linesCleared;
  timeInterval = 800-totalLinesCleared*15;
  flashClearedLines(temp);
  // Take out all the 0s from the deadTetrisBoard
  for (uint8_t i=0;i<16;i++) deadTetrisBoard[i]=0;
  int8_t n=15;
  for (int8_t i=15;i>=0;i--) {
    if (temp[i]) {
      deadTetrisBoard[n]=temp[i];
      n--;
    }
  }
  return true;
}
