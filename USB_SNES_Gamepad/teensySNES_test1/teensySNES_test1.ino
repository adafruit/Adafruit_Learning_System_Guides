#define REPEATRATE 100  // milliseconds

const int pinBtnUp = 0;
const int pinBtnRight = 1;
const int pinBtnDown = 2;
const int pinBtnLeft = 3;

const int pinBtnSelect = 4;
const int pinBtnStart = 5;

const int pinBtnB = 7;
const int pinBtnA = 8;
const int pinBtnY = 10;
const int pinBtnX = 9;

const int pinBtnTrigLeft = 6;
const int pinBtnTrigRight = 23;

const int pinLEDOutput = 11;

//Variables for the states of the SNES buttons
byte buttons[] = {  pinBtnUp, pinBtnRight, pinBtnDown, pinBtnLeft, pinBtnSelect, pinBtnStart,
                    pinBtnB, pinBtnA, pinBtnY, pinBtnX, pinBtnTrigLeft, pinBtnTrigRight
                 }; 
short keys[] = {KEY_U, KEY_R, KEY_D, KEY_L, KEY_ENTER, KEY_TAB, KEY_B, KEY_A, KEY_Y, KEY_X, KEY_P, KEY_Q};

#define NUMBUTTONS sizeof(buttons)

typedef void KeyFunction_t(uint8_t c);

KeyFunction_t* buttonActive[NUMBUTTONS];
KeyFunction_t* keyList[] = {myset_key6, myset_key5, myset_key4, myset_key3, myset_key2, myset_key1};
int            keySlot = sizeof(keyList) / sizeof(KeyFunction_t*);

void setup()
{
  //Setup the pin modes.
  pinMode( pinLEDOutput, OUTPUT );

  //Special for the Teensy is the INPUT_PULLUP
  //It enables a pullup resitor on the pin.
  for (byte i=0; i< NUMBUTTONS; i++) {
    pinMode(buttons[i], INPUT_PULLUP);
  }
  
  //Uncomment this line to debug the acceleromter values:
//  Serial.begin();

  for (int i=0; i < NUMBUTTONS; i++) {
    buttonActive[i] = 0;
  }
  
}

void loop()
{
//  //debugging the start button...
  digitalWrite ( pinLEDOutput, digitalRead(pinBtnStart));

  //Progess the SNES controller buttons to send keystrokes.
  fcnProcessButtons();
  
}

//Function to process the buttons from the SNES controller
void fcnProcessButtons()
{ 
  bool keysPressed = false; 
  bool keysReleased = false;
  
  // run through all the buttons
  for (byte i = 0; i < NUMBUTTONS; i++) {
    
    // are any of them pressed?
    if (! digitalRead(buttons[i])) 
    {                              //this button is pressed
      keysPressed = true;
      if (!buttonActive[i])        //was it pressed before?
        activateButton(i);            //no - activate the keypress
    }
    else
    {                              //this button is not pressed
      if (buttonActive[i]) {        //was it pressed before?
        releaseButton(i);            //yes - release the keypress
        keysReleased = true;
      }
    }
  }
  
  if (keysPressed || keysReleased)
    Keyboard.send_now();            //update all the keypresses

}

void activateButton(byte index)
{
  if (keySlot)      //any key slots left?
  {
    keySlot--;                                //Push the keySlot stack
    buttonActive[index] = keyList[keySlot];   //Associate the keySlot function pointer with the button
    (*keyList[keySlot])(keys[index]);         //Call the key slot function to set the key value 
  }
}

void releaseButton(byte index)
{
  keyList[keySlot] = buttonActive[index];    //retrieve the keySlot function pointer
  buttonActive[index] = 0;                   //mark the button as no longer pressed
  (*keyList[keySlot])(0);                    //release the key slot
  keySlot++;                                 //pop the keySlot stack
}

void myset_key1(uint8_t c)
{
  Keyboard.set_key1(c);
}

void myset_key2(uint8_t c)
{
  Keyboard.set_key2(c);
}

void myset_key3(uint8_t c)
{
  Keyboard.set_key3(c);
}

void myset_key4(uint8_t c)
{
  Keyboard.set_key4(c);
}

void myset_key5(uint8_t c)
{
  Keyboard.set_key5(c);
}

void myset_key6(uint8_t c)
{
  Keyboard.set_key6(c);
}
