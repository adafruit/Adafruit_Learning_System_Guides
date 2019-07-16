#include "Paint.h"

Paint::Paint(int8_t x, int8_t y){
  cursorX=x;
  cursorY=y;
  for (uint8_t i=0;i<16;i++) canvas[i]=0;
}

void Paint::turnOffCursor(){
  activeCanvas[cursorY]&=~_BV(7-cursorX);
}

void Paint::turnOnCursor(){
  activeCanvas[cursorY]|=_BV(7-cursorX);
}

void Paint::flashCursor(){
  if (flashDisableCounter>0){
    flashDisableCounter--;
    return;
  }
  cursorVisible=!cursorVisible;  
}

void Paint::moveCursor(int8_t dx, int8_t dy){
  int8_t cursorX1 = cursorX+dx;
  int8_t cursorY1 = cursorY+dy;
  if (cursorX1<X_MIN || cursorX1>X_MAX || cursorY1<Y_MIN || cursorY1>Y_MAX) return;
  cursorX=cursorX1;
  cursorY=cursorY1;
  // Do not flash the cursor for 0.5s just after it's moved to a new location
  flashDisableCounter=1;
  cursorVisible=true;
}

bool Paint::readCanvas(uint8_t x, uint8_t y){
  return (canvas[y]>>(7-x))&1;
}

void Paint::clearCanvas(){
  for (uint8_t i=0;i<=Y_MAX;i++) canvas[i]=0;
}

void Paint::draw(){
  if (readCanvas(cursorX,cursorY)) canvas[cursorY]&=~_BV(7-cursorX);  // if (cursorX,cursorY) is 1 on the canvas, replace it with 0
  else canvas[cursorY]|=_BV(7-cursorX);                               // if (cursorX,cursorY) is 0 on the canvas, replace it with 1
}

uint8_t* Paint::getActiveCanvas(){
  for (uint8_t i=0;i<16;i++) activeCanvas[i]=canvas[i];
  if (cursorVisible) turnOnCursor();
  else turnOffCursor();
  return activeCanvas;
}
