#include "HT16K33.h"
#include "Tetris.h"
#include "Snake.h"
#include "Paint.h"

// ADC clock configurations
#define ADPS_16 _BV(ADPS2)
#define ADPS_32 _BV(ADPS2)|_BV(ADPS0)
#define ADPS_128 _BV(ADPS2)|_BV(ADPS1)|_BV(ADPS0)

// Buttons: bits 0-6 in the first byte of the key-scan matrix
#define LEFT 6
#define SELECT 1
#define DOWN 2
#define UP 5
#define RIGHT 0
#define BRIGHTNESS_UP 4
#define BRIGHTNESS_DOWN 3

// Objects
HT16K33 ht(0x70);  // I2C address of the HT16K33 IC
Tetris tetris;
Snake snake;
Paint paint(3,3);  // initilize cursor position to (3,3)

// Mode: 0-Undecided; 1-Tetris; 2-Snake; 3-Paint
uint8_t mode=0;

// Interrupt Variables
uint8_t interruptCounter2Hz = 0;

ISR(TIMER1_OVF_vect){  
  // things that need to be done at 50Hz
  ht.readButtons();
  processButtons();
  switch(mode) {
    case 0:
      ht.storeToBuffer(getMenu());
      break;
    case 1:
      ht.storeToBuffer(tetris.getActiveBoard());
      break;
    case 2:
      ht.storeToBuffer(snake.getActiveBoard());
      break;
    case 3: 
      ht.storeToBuffer(paint.getActiveCanvas());
  }
  ht.refreshDisplay();
  
  // things that happen less frequently
  interruptCounter2Hz++;
  if (interruptCounter2Hz==25) {
    interruptCounter2Hz=0;
    paint.flashCursor();
  }
}

void processButtons() {
  // These two buttons are fixed
  if (ht.allowToMove(BRIGHTNESS_DOWN,25,6) && ht.getButtonHoldTime(SELECT)==0) ht.decreaseBrightness();
  if (ht.allowToMove(BRIGHTNESS_UP,25,6) && ht.getButtonHoldTime(SELECT)==0) ht.increaseBrightness();
  
  // change to the previous/next program by pressing holding select and press the brightness control buttons
  if (mode!=0 && ht.getButtonHoldTime(SELECT)>10) {
    if (ht.getButtonFirstPress(BRIGHTNESS_UP)) {
      changeOption(-1);
      changeMode();
    }
    else if (ht.getButtonFirstPress(BRIGHTNESS_DOWN)){
      changeOption(1);
      changeMode();
    }
  }
  
  // control for different programs
  switch(mode) {
    case 0:
      if (ht.getButtonFirstPress(LEFT)) changeOption(-1);
      if (ht.getButtonFirstPress(RIGHT)) changeOption(1);
      if (ht.getButtonFirstPress(SELECT)) changeMode();
      break;
    case 1:
      if (tetris.gameRunning) {
        if (ht.allowToMove(UP,100,4)) tetris.rotatePiece();
        if (ht.allowToMove(DOWN,15,2)) tetris.movePiece(0,1);
        if (ht.allowToMove(LEFT,15,2)) tetris.movePiece(-1,0);
        if (ht.allowToMove(RIGHT,15,2)) tetris.movePiece(1,0);
        if (ht.getButtonFirstPress(SELECT)) tetris.dropPiece();
      }
      else {
        if (ht.getButtonFirstPress(SELECT)) tetris.init();
      }
      break;
    case 2:
      if (snake.gameRunning) {
        if (ht.getButtonFirstPress(UP)) snake.changeDirection(0,-1);
        if (ht.getButtonFirstPress(DOWN)) snake.changeDirection(0,1);
        if (ht.getButtonFirstPress(LEFT)) snake.changeDirection(-1,0);
        if (ht.getButtonFirstPress(RIGHT)) snake.changeDirection(1,0);
      }
      else {
        if (ht.getButtonFirstPress(SELECT)) snake.init();
      }
      break;
    case 3: 
        if (ht.allowToMove(UP,25,2)) paint.moveCursor(0,-1);
        if (ht.allowToMove(DOWN,25,2)) paint.moveCursor(0,1);
        if (ht.allowToMove(LEFT,25,2)) paint.moveCursor(-1,0);
        if (ht.allowToMove(RIGHT,25,2)) paint.moveCursor(1,0);
        if (ht.getButtonFirstPress(SELECT)) paint.draw();
        if (ht.getButtonHoldTime(SELECT)==150) paint.clearCanvas();    
  }
}

void setup(){    
  // Set randomSeed; the first few random() are not used because they never change
  randomSeed(analogRead(A0));
  for (uint8_t i=0;i<4;i++) random();
  
  // Initiate objects
  Serial.begin(115200);
  ht.init();
  tetris.init();
  snake.init();
  
  //ADC: 16MHz/16=1MHz
  ADCSRA &= ~ADPS_128;              // clean out ADPS
  ADCSRA |= ADPS_32;                // set Division Factor
  
  // Timer1 overflow interrupt setup
  TCNT1 = 0;                        // reset the counter
  ICR1 = 19999;                     // top value of the counter (16*10^6Hz/2000000*20000us/8-1) -> 1/20000us = 50Hz
  TCCR1A = 0;                       // clear TCCR1A (not used)
  TCCR1B = _BV(WGM13) | _BV(CS11);  // mode 8(PWM), set prescalar=8;
  TIMSK1 = _BV(TOIE1);              // Enable Overflow Interrupt 
}

void loop(){
  // For both the tetris and snake, they have a function called "run" as the main game loop.
  // For the paint program, all the actions are handled in the timer interrupt, so there is nothing to do in the main loop
  switch(mode) {
    case 0:
      break;
    case 1:
      tetris.run(); break;
    case 2:
      snake.run(); break;
    case 3: 
      ;    
  }
}
