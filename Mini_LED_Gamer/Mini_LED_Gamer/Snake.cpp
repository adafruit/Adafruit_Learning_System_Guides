#include "Snake.h"

void Snake::run() {
  if (gameRunning) {
    if ((millis()-lastSnakeMoveTime)>((80-snakeLength)*(80-snakeLength)/20)) {
      if (!moveSnake()) gameOver();
      else lastSnakeMoveTime=millis();
    }
  }
}

void Snake::init() {
  for (uint8_t y=0;y<16;y++) {
    for (uint8_t x=0;x<8;x++) {
      snakeBoard[y][x]=0;
    }
  }
  snakeLength=3;
  snakeHeadX=random(4)+2;
  snakeHeadY=random(12)+2;
  uint8_t moveDirection=random(4);
  switch (moveDirection) {
    case 0:  // up
      snakeHeadDX=0;  snakeHeadDY=-1; break;
    case 1:  // down
      snakeHeadDX=0;  snakeHeadDY=1;  break;
    case 2:  // left
      snakeHeadDX=-1; snakeHeadDY=0;  break;
    case 3:  // right
      snakeHeadDX=1;  snakeHeadDY=0;
  }
  // Draw the snake of length=3
  snakeBoard[snakeHeadY][snakeHeadX]=3;
  snakeBoard[snakeHeadY-snakeHeadDY][snakeHeadX-snakeHeadDX]=2;
  snakeBoard[snakeHeadY-snakeHeadDY*2][snakeHeadX-snakeHeadDX*2]=1;
  placeFood();
  gameRunning=true;
}

void Snake::gameOver() {
  gameRunning=false;
  Serial.println("Game Over");
}

void Snake::placeFood() {
  foodX = random(8);
  foodY = random(16);
  while(snakeBoard[foodY][foodX]!=0) {
    foodX = random(8);
    foodY = random(16);
  }
  snakeBoard[foodY][foodX]=snakeLength+1;
}

bool Snake::moveSnake() {
  snakeHeadX = (snakeHeadX+snakeHeadDX+8) % 8;
  snakeHeadY = (snakeHeadY+snakeHeadDY+16)%16;
  uint8_t temp = snakeBoard[snakeHeadY][snakeHeadX];
  // if the new snakeHead is already occupied by part of the snake body, then return false, game over 
  if (temp>1 && temp<=snakeLength) return false;
  if (snakeHeadX == foodX && snakeHeadY == foodY) {
    snakeLength+=1;
    placeFood();
  }
  else {
    for (uint8_t y=0; y<16; y++) {
      for (uint8_t x=0; x<8; x++) {
        if (snakeBoard[y][x]>0 && snakeBoard[y][x]<=snakeLength) snakeBoard[y][x]-=1;
      }
    }
    snakeBoard[snakeHeadY][snakeHeadX]=snakeLength;
  }
  allowToChangeDirection=true;
  return true;
}

void Snake::changeDirection(int8_t dx, int8_t dy) {
  if (!allowToChangeDirection) return;
  if ((snakeHeadDX+dx==0 && dx!=0) || (snakeHeadDY+dy==0 && dy!=0)) return;
  snakeHeadDX=dx;
  snakeHeadDY=dy;
  allowToChangeDirection=false;
}

uint8_t* Snake::getActiveBoard(){
  for (int8_t y=0; y<16; y++) {
    uint8_t temp=0;
    for (int8_t x=0; x<8; x++) {
      if (snakeBoard[y][x]) temp |= _BV(7-x);
    }
    activeSnakeBoard[y]=temp;
  }
  return activeSnakeBoard;
}
