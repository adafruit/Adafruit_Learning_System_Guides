// Adafruit Arcada based Level Bounce Game
//
// Mike Barela, June 3, 2019 for Adafruit Industries
//
// Mod of game by R0D0T posted on http://r0d0t.tumblr.com/post/29641975900 and 
// Hackaday http://hackaday.com/2012/10/01/fantastic-programming-makes-this-arduino-gaming-device-something-special/ 
// which was published for Arduino Esplora by Mike Barela 2013

#include <Adafruit_Arcada.h>
#include <Adafruit_Arcada_Def.h>
#include <Adafruit_NeoPixel.h>
#include "logo.h"

Adafruit_Arcada arcada; // Set up the Arcada code
Adafruit_NeoPixel strip(5, 8, NEO_GRB + NEO_KHZ800);  // 5 NeoPixels are on D8

// SCREEN
#define s_width   128
#define s_height  139
#define textline1 (s_height +  3)
#define textline2 (s_height + 13) 
unsigned int background = ARCADA_BLACK;

long lastMillis;

// SOUND
#define sound_pin A0      // Direct sound 
uint8_t sound_on = 1;     // start with sound on
char speaker_icon = 0xEC; // icon to show sound off

// PLAYER
float p_X = s_width/2;
float p_Y = s_height/2;
float p_lastX, p_vX;
float p_lastY, p_vY;
//#define p_vmaxY 6
//#define p_vmaxX 6
#define gravity_default 0.2
float gravity = 0.2;
#define p_bounceSpeed_default 4
byte p_bounceSpeed = p_bounceSpeed_default;
#define p_width_default 4
byte p_width = p_width_default;
#define p_height_default 4
byte p_height = p_height_default;
#define p_color_default ARCADA_WHITE
#define p_color_dead    ARCADA_RED
int p_color = p_color_default;

// SCORE & BONUS
unsigned int score = 0;
unsigned int highscore = 0;
byte nextBonus;
boolean b_pendingPlatform = false;
boolean b_used;
byte b_platformID;
byte b_pendingID;
byte b_onUseID;
byte b_remaining = 0;
byte b_max;
#define b_number 4
int b_colors[b_number] = {
  ARCADA_ORANGE, 0x0F00, 0xF000, 0x00FF};
byte b_lives = 0;
byte num_lives = 5;

// WORLD
#define w_size 8
byte world[w_size][6];         // contains platforms data
int  w_color = ARCADA_YELLOW;  // Platform default color
byte w_speed = 1;
byte w_widthMin = 4;
byte w_widthMax = 8;

// ACCELEROMETER 
int acc_avgX, acc_avgY, acc_avgZ;
sensors_event_t event;
#define acc_pinX 1  
#define acc_pinY 2  
#define acc_pinZ 3 

// NeoPixels
#define RED      0xFF0000
#define YELLOW   0xFFFF00
#define GREEN    0x00FF00
#define BLACK    0x000000

void setup() {
  Serial.begin(9600);
  // initialize 

  Serial.println("Hello! Arcada version of game");
  if (!arcada.begin()) {
    Serial.print("Failed to begin");
    strip.fill(RED);
    strip.show();
    while (1);
  }
  if( !arcada.hasAccel() ) {
    strip.fill(YELLOW);
    strip.show();
    arcada.haltBox("An accelerometer is required for this gamne");
  }
  arcada.displayBegin();         // Initialize display code
  arcada.setBacklight(0);        // Initial display off
  arcada.setRotation(0);         // Rotate to portrait
  arcada.fillScreen(background); // Clear screen if necessary
  arcada.setTextColor(ARCADA_GREEN, ARCADA_BLACK);
  arcada.setTextSize(2);
  arcada.println(" ");
  arcada.println("  Bounce!");
  // Set up the logo bitmap
  int logo_origin_x = (128 - 2*LOGO_WIDTH ) / 2;
  int logo_origin_y = (160 - 2*LOGO_HEIGHT) / 2;
  for(int y=0; y<LOGO_HEIGHT; y++) {
    for(int x=0; x<LOGO_WIDTH; x++) {
      uint8_t c = logo_mask[y][x / 8];
      if(c & (0x80 >> (x & 7))) {
        int xx = logo_origin_x+2*x;
        int yy = logo_origin_y+2*y;
        arcada.drawPixel(xx, yy, ARCADA_WHITE);
        arcada.drawPixel(xx+1, yy, ARCADA_WHITE);
        arcada.drawPixel(xx, yy+1, ARCADA_WHITE);
        arcada.drawPixel(xx+1, yy+1, ARCADA_WHITE);
      }
    }
  }
  arcada.println(" ");
  arcada.println(" ");
  arcada.println(" ");
  arcada.println(" ");
  arcada.println(" ");
  arcada.setTextColor(ARCADA_ORANGE, ARCADA_BLACK);
  arcada.setTextSize(1);
  arcada.println(" ");
  arcada.println("  Adafruit");
  arcada.println("   Industries");
  for (int i=0; i<220; i++) {    // Display initial text
    arcada.setBacklight(i);
    delay(14);
  }
  arcada.setBacklight(250);
  arcada.setTextColor(ST7735_WHITE, ST7735_BLACK);
  arcada.println(" ");
  arcada.println(" ");
  arcada.println("  Press Start");
  while(!(arcada.readButtons() & ARCADA_BUTTONMASK_START)) ; // wait for start button
  arcada.fillScreen(background);                             // Clear screen

  arcada.enableSpeaker(1);   // Enable the speaker and play opening tones
  pinMode(sound_pin, OUTPUT);
  beep(sound_pin,  880, 100);
  delay(100);
  beep(sound_pin, 1060, 120);
  delay(100);
  beep(sound_pin, 1800, 100);
  
  // NeoPixel setup
  strip.begin();
  strip.setBrightness(40);  // not too bright
  strip.show();

  // Game setup
  randomSeed(millis());  
  FillWorld();

  // Get average accelerations
  acc_avgX = acc_avg(acc_pinX);
  acc_avgY = acc_avg(acc_pinY);
  acc_avgZ = acc_avg(acc_pinZ);

  ScoreSetup();
}

void loop() {
  if(millis()-lastMillis > 20){
    lastMillis = millis();
    CheckButtons();
    MovePlayer();
    ScrollWorld();
    CollideBorders();
    CollideWorld();
    DrawWorld();
    DrawPlayer();
  }
}

int acc_avg(int pin) {
  int avg = 0;
  arcada.accel.getEvent(&event);
  switch (pin) {
    case acc_pinX:
       for(int i = 0; i < 50; i++) {
         avg += event.acceleration.x;
         // delay(10);
        }
       break;
     case acc_pinY:
       for(int i = 0; i < 50; i++) {
         avg += event.acceleration.y;
         // delay(10);
        }
       break;
     case acc_pinZ:
         for(int i = 0; i < 50; i++) {
         avg += event.acceleration.z;
         // delay(10);
        }
       break;
     }
  avg /= 50;
  return avg;
}

int acc_readX() {
  int val;
  arcada.accel.getEvent(&event);
  val = -1 * constrain((event.acceleration.y - acc_avgY)*7, -64, 64); // use Y for orientation
  // Serial.print("Acceleration: ");                                  // joystick is at top
  // Serial.println(val);
  return(val);
}


void CheckBonus(byte thisPlatform){
  if(b_pendingPlatform && (b_platformID == thisPlatform)){
    b_pendingPlatform = false;
  }
  if(nextBonus ){
    nextBonus--;
  } 
  else {
    nextBonus = random(30, 60);
    b_pendingID = random(0, b_number);
    b_pendingPlatform = true;
    b_platformID = thisPlatform;
  }
}

void BonusReset(){
  nextBonus = random(30, 60);
  b_pendingPlatform = false;
  b_remaining = 0;
  arcada.fillRect(0, s_height+2, 96, 10, background);
  arcada.fillRect(0, s_height+1, 96, 1, w_color);
  EndUseBonus();
}

void ClearBonus(){
  EndUseBonus();
  b_remaining = 0;
  p_color = p_color_default;
  arcada.fillRect(0, s_height+2, 96, 10, background);
  arcada.fillRect(0, s_height+1, s_width-1,  1, w_color);
  b_used = false;
}

void GetBonus(){
  ClearBonus();
  b_onUseID = b_pendingID;
  b_pendingPlatform = false;
  beep(sound_pin, 3500, 50);  // SOUND
  p_color = b_colors[b_onUseID];
  arcada.fillRect(0, s_height+2, 96, 10, background);

  switch (b_onUseID){
  case 0:
    drawString(1, textline1, "Jet pack", b_colors[b_onUseID], 1);
    b_max = 100;
    b_remaining = b_max;
    break;
  case 1:
    drawString(1, textline1, "Frog legs", b_colors[b_onUseID], 1);
    b_max = 100;
    b_remaining = b_max;
    break;
  case 2:
    drawString(1, textline1, "Boost", b_colors[b_onUseID], 1);
    b_max = 1;
    b_remaining = b_max;
    break;
  case 3:
    drawString(1, textline1, "Low gravity", b_colors[b_onUseID], 1);
    b_max = 255;
    b_remaining = b_max;
    break;
  }
  if(b_remaining > 1) {
    arcada.fillRect(95, s_height+2, 1, 10, b_colors[b_onUseID]);
    arcada.fillRect( 0, s_height+1, 95, 1, b_colors[b_onUseID]);
  }
}

void UseBonus(){
  if(b_remaining){
    b_used = true;
    arcada.fillRect(b_remaining*95/b_max, s_height+2, 1, 10, background);
    arcada.drawPixel(b_remaining*95/b_max, s_height+1, w_color);
    b_remaining --;
    arcada.fillRect(b_remaining*95/b_max, s_height+2, 1, 10, b_colors[b_onUseID]);
    arcada.drawPixel(b_remaining*95/b_max, s_height+1, b_colors[b_onUseID]);

    switch (b_onUseID){
    case 0:
      if(p_vY > -1){
        p_vY -= 0.3;
      }
      beep(sound_pin, 100, 3 + abs(10 * p_vY)); // SOUND
      break;
    case 1:
      p_bounceSpeed = p_bounceSpeed_default * 1.5;
      break;
    case 2:
      p_width = min(p_width+1, p_width_default+12);
      p_height = min(p_height+1, p_height_default+12);
      b_lives = min(b_lives+1, 12);
      beep(sound_pin, 50+150*b_lives, 100);  // SOUND
      break;
    case 3:
      gravity = gravity_default * 0.3;
      break;
    }

    if(!b_remaining){
      ClearBonus();
    }
  }
}

void EndUseBonus(){
  b_used = false;

  switch (b_onUseID){
  case 0:
    break;
  case 1:
    p_bounceSpeed = p_bounceSpeed_default;
    break;
  case 2:
    break;
  case 3:
    gravity = gravity_default;
    break;
  }
}

void CheckButtons(){
  uint32_t pressed_buttons;
  pressed_buttons = arcada.readButtons();
  
  if(pressed_buttons & ARCADA_BUTTONMASK_START) {  // pause
    Serial.print("START");
    delay(500);
    while(!(arcada.readButtons())) {  // wait until any button is pressed again
       strip.setPixelColor(0, GREEN);
       strip.show();
       delay(100);
       strip.setPixelColor(0, BLACK);
       strip.show();
       delay(100);
    }
    pressed_buttons = 0;
    return;
  }
  if(pressed_buttons & ARCADA_BUTTONMASK_B) {  // use bonus
    Serial.print("B");
    if(b_used = true) {
      EndUseBonus();
    } else {
      UseBonus();
    }
    return;
  }
  if(pressed_buttons & ARCADA_BUTTONMASK_SELECT) {  // SELECT toggles sound on/off
    Serial.print("SELECT");
    if(sound_on) {
       sound_on = 0;
       drawChar(s_width-6, textline2, speaker_icon, ARCADA_RED);  // Put character in lower right corner to indicate speaker off
    } else {
       sound_on = 1;
       arcada.fillRect( s_width-6, textline2, s_width-1, textline2+9, background); // Blank lower right character = sound on
    }
  }
}

void DrawPlayer(){
  CheckButtons();  // check more frequently
  arcada.fillRect(p_lastX, p_lastY, p_width, p_height, background); // erase previous pos
  if(p_lastX > (s_width-1 - p_width)) // if across the edge of the screen
    arcada.fillRect(0, p_lastY, p_lastX + p_width - s_width, p_height, background);

  arcada.fillRect(p_X, p_Y, p_width, p_height, p_color); // draw new pos
  if(p_X > (s_width-1 - p_width)) // if across the edge of the screen
    arcada.fillRect(0, p_Y, p_X + p_width - s_width, p_height, p_color);
}

void MovePlayer(){
  p_lastX = p_X;
  p_lastY = p_Y;

  p_vX = (p_vX + acc_readX()) / 20;
  p_vY = (p_vY + gravity);

  p_X = p_X + p_vX;
  if(p_X > s_width){
    p_X = 0;
  }
  if(p_X < 0){
    p_X = s_width - p_X;
  }
  p_Y = p_Y + p_vY;

  if((p_vY < -4) && (p_color != p_color_dead)){
    beep(sound_pin, 600+p_vY*100, 25);  // SOUND
  }
  if(b_used && (b_onUseID == 3)) { // if low gravity is on use
    beep(sound_pin, 300-abs(p_vY*100), 25);  // SOUND
  }
}

void CollideBorders() {
  if(p_Y > s_height - p_height){ // touch the floor
    p_vY = -p_bounceSpeed;
    p_Y = s_height - p_height;
    if(!b_lives){
      if(p_color != p_color_dead){
        BonusReset();
        ScoreReset();
      }
    } 
    else {
      arcada.fillRect(p_lastX, p_lastY, p_width, p_height, background);
      p_width--;
      p_height--;
      b_lives--;
      beep(sound_pin, 100+150*b_lives, 100);  // SOUND
    }
  }
}

void ScoreSetup(){
  arcada.fillRect(0, s_height+2, 128, 10, background);
  arcada.fillRect(0, s_height+1, 128, 1, w_color);
  // highscore = EEPROM.read(0);
  // highscore += (EEPROM.read(1)<<8);
  if(highscore > 64000){
    highscore = 0;
  }
  drawString(1, textline2, "High score:", w_color, 1);  
  drawInt(highscore, 66, textline2, w_color, background);
}

void ScoreReset(){
  if(p_color != p_color_dead) {
    p_color = p_color_dead;
    beep(sound_pin, 50, 500); // SOUND
    if(score > highscore){
      if(score < 64000) {
        // EEPROM.write(0, score);
        // EEPROM.write(1, score>>8);
      }
      else { // bad value, zero out
        // EEPROM.write(0,0);
        // EEPROM.write(1,0);
      }       
      highscore = score; 
      flashMessage();
      // drawInt(score, 66, textline2, p_color_default, background);
    } 
    else {
      drawString(1, textline1, "Last score:", w_color, 1);
      drawInt(score, 66, s_height+3, w_color, background);
    }
    score = 0;
    drawInt(score, 97, textline1, w_color, background);
  }
}

void flashMessage() {
   uint8_t i;
   arcada.fillRect( 0, textline2, s_width-10, textline2+9, background);
   for(i=0; i<5; i++) {
     drawString(1, textline2, "HIGHSCORE!", p_color_default, 1);
     delay(400);
     arcada.fillRect( 0, textline2, s_width-10, textline2+9, background);
     delay(400);
   }
   drawString(1, textline2, "High score:", w_color, 1);  
   drawInt(highscore, 66, textline2, w_color, background);
}

void ScoreAdd(){ // add to the current score lower left
  score++;
  beep(sound_pin, 3000, 50);  // SOUND
  if(score > highscore) {
    drawInt(score, 97, textline1, p_color_default, background);
  } 
  else {
    drawInt(score, 97, textline1, w_color, background);
  }
  w_widthMin = max(1, 4 - score/50);
  w_widthMax = max(2, 8 - score/50);
  if(score == 1) {
    p_color = p_color_default;
  }
}

// transform from int to string and display it
void drawInt(unsigned int num, byte nx, byte ny, unsigned int color, unsigned int color2) {
  arcada.fillRect(nx, ny, 29, 7, color2);
  drawChar(nx+24, ny, 48+(num%10), color);

  if(num > 9) {
    drawChar(nx+18, ny, 48+(num%100)/10, color);

    if(num>99) {
      drawChar(nx+12, ny, 48+(num%1000)/100, color);

      if(num>999) {
        drawChar(nx+6, ny, 48+(num%10000)/1000, color);

        if(num>9999) {
          drawChar(nx, ny, 48+(num%100000)/10000, color);
        }
      }
    }
  }
}

/*
world[a][b] ->
 a ->  platform id
 b ->  0 = x
 1 = y
 2 = last x
 3 = last y
 4 = width
 4 = last width
 */

void FillWorld(){
  for(byte i=0; i<w_size; i++) {
    world[i][0] = (s_width * (w_size-i-1) / w_size)/2;
    world[i][1] = 1 + i * (s_height / w_size);
    world[i][2] = world[i][0];
    world[i][3] = world[i][1];
    world[i][4] = s_width * (i+1)/w_size;
    world[i][5] = world[i][4];
  }
}

void ScrollWorld(){
  byte fastScrolling = 0;
  if(p_Y < s_height/4) { // if the player reaches the top of the screen
    fastScrolling ++;
    if(p_Y < s_height/8) { // if the player reaches the top of the screen
      fastScrolling ++;
    }
  }
  p_Y += fastScrolling;
  for(byte i=0; i<w_size; i++) {  // for each platform
    world[i][3] = world[i][1];    // update last y
    world[i][2] = world[i][0];    // update last x
    world[i][5] = world[i][4];    // update last width
    world[i][1] += w_speed ;      // move the platform downward
    world[i][1] += fastScrolling;
    if(world[i][1] > s_height){    // if the platform reaches the bottom of the screen
      //world[i][2] = world[i][0]; // update last x
      world[i][1] = world[i][1] - s_height + 1; // put the platform on the top of the screen
      world[i][4] = min(random(w_widthMin, w_widthMax)*p_width_default, s_width-world[i][0]); //pick a random width
      world[i][0] = random(0, s_width-world[i][4]); // pick a random x
      CheckBonus(i); // check if the new platform will have a bonus
    }
  }
}

void CollideWorld() {
  for(byte i=0; i<w_size; i++) {
    if(p_vY > 0){ // if player falling
      if((p_Y+p_width <= world[i][1]) && (world[i][1] < (p_Y+p_vY+p_height)) ) { // and at the height of the platform
        if(((p_X+p_width) >= world[i][0]) && (world[i][0]+world[i][4] > (p_X)) ) {     // and does not miss it
          p_vY = -p_bounceSpeed ;
          p_Y = world[i][1] - p_height;
          ScoreAdd();
          if(b_pendingPlatform && (b_platformID == i)) {
            GetBonus();
          }
        }
      }
    }
  }
}

void DrawWorld() {
  for(byte i=0; i<w_size; i++) {
    arcada.fillRect(world[i][2], world[i][3], world[i][5], 1, background);
    arcada.fillRect(world[i][0], world[i][1], world[i][4], 1, w_color);
  }
  if(b_pendingPlatform){
    arcada.fillRect(world[b_platformID][0], world[b_platformID][1], world[b_platformID][4], 1, b_colors[b_pendingID]);
  }
}


void drawString(byte x, byte y, char *text, uint16_t color, bool wrap) { // replicate tft.drawString
  arcada.setCursor(x,y);
  arcada.setTextColor(color);
  arcada.setTextWrap(wrap);
  arcada.print(text);
}

void drawChar(byte x, byte y, char text, uint16_t color) { // replicate tft.drawChar
  arcada.setCursor(x,y);
  arcada.setTextColor(color);  
  arcada.print(text);
  Serial.println(text);
}

// A sound-producing function
void beep(unsigned char speakerPin, int frequencyInHertz, long timeInMilliseconds) {
  // http://web.media.mit.edu/~leah/LilyPad/07_sound_code.html
  int  x;
  if( sound_on ) {     // Only play if the sound_on flag is 1
    long delayAmount = (long)(1000000 / frequencyInHertz);
    long loopTime = (long)((timeInMilliseconds * 1000) / (delayAmount * 2));
    for (x = 0; x < loopTime; x++) {
      digitalWrite(speakerPin, HIGH);
      delayMicroseconds(delayAmount);
      digitalWrite(speakerPin, LOW);
      delayMicroseconds(delayAmount);
    }
  }
}
