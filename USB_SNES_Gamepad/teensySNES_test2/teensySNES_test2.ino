const int pinAnalogXInput = 3;
const int pinAnalogYInput = 1;
const int pinAnalogZInput = 2;
const int pinAnalogDummyInput = 0;

#define KEYREPEAT 100  // milliseconds
#define KEYDELAY 200 // delay from first to second character

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

//Change these values if accelerometer reading are different:
//How far the accerometer is tilted before
//the Teensy starts moving the mouse:
const int cintMovementThreshold = 18;

//The average zero acceleration values read
//from the accelerometer for each axis:
const int cintZeroXValue = 328;
const int cintZeroYValue = 328;
const int cintZeroZValue = 328;

//The maximum (positive) acceleration values read
//from the accelerometer for each axis:
const int cintMaxXValue = 396;
const int cintMaxYValue = 396;
const int cintMaxZValue = 396;

//The minimum (negative) acceleration values read
//from the accelerometer for each axis:
const int cintMinXValue = 256;
const int cintMinYValue = 256;
const int cintMinZValue = 256;

//The sign of the mouse movement relative to the acceleration.
//If your cursor is going in the opposite direction you think it
//should go, change the sign for the appropriate axis.
const int cintXSign = 1;
const int cintYSign = -1;
const int cintZSign = 1;

//const float cfloatMovementMultiplier = 1;

//The maximum speed in each axis (x and y)
//that the cursor should move. Set this to a higher or lower
//number if the cursor does not move fast enough or is too fast.
const int cintMaxMouseMovement = 10;

//This reduces the 'twitchiness' of the cursor by calling
//a delay function at the end of the main loop.
//There is a better way to do this without delaying the whole
//microcontroller, but that is left for another time or person.
const int cintMouseDelay = 8;


void setup()
{
    //This is not needed and set to default but can be useful if you
  //want to get the full range out of the analog channels when
  //reading from the 3.3V ADXL335.
  //If the analog reference is used, the thresholds, zeroes,
  //maxima and minima will need to be re-evaluated.
  analogReference( DEFAULT );
  
  //Setup the pin modes.
  pinMode( pinLEDOutput, OUTPUT );

  //Special for the Teensy is the INPUT_PULLUP
  //It enables a pullup resitor on the pin.
  for (byte i=0; i< NUMBUTTONS; i++) {
    pinMode(buttons[i], INPUT_PULLUP);
  }

  //Uncomment this line to debug the acceleromter values:
//  Serial.begin();

}


void loop()
{
//  //debugging the start button...
  digitalWrite ( pinLEDOutput, digitalRead(pinBtnStart));


  //Process the accelerometer to make the cursor move.
  //Comment this line to debug the accelerometer values:
  fcnProcessAccelerometer();

  //Progess the SNES controller buttons to send keystrokes.
  fcnProcessButtons();
  
    
  //Delay to avoid 'twitchiness' and bouncing inputs
  //due to too fast of sampling.
  //As said above, there is a better way to do this
  //than delay the whole MCU.
  delay(cintMouseDelay);
}


//Function to process the acclerometer data
//and send mouse movement information to the host computer.
void fcnProcessAccelerometer()
{
  //Initialize values for the mouse cursor movement.
  int intMouseXMovement = 0;
  int intMouseYMovement = 0;
  
  //Read the dummy analog channel
  //This must be done first because the X analog channel was first
  //and was unstable, it dropped or pegged periodically regardless
  //of pin or source.
  analogRead( pinAnalogDummyInput );
  
  //Read accelerometer readings  
  int intAnalogXReading = analogRead(pinAnalogXInput);
  int intAnalogYReading = analogRead(pinAnalogYInput);
  int intAnalogZReading = analogRead(pinAnalogZInput);

  //Calculate mouse movement
  //If the analog X reading is ouside of the zero threshold...
  if( cintMovementThreshold < abs( intAnalogXReading - cintZeroXValue ) )
  {
    //...calculate X mouse movement based on how far the X acceleration is from its zero value.
    intMouseXMovement = cintXSign * ( ( ( (float)( 2 * cintMaxMouseMovement ) / ( cintMaxXValue - cintMinXValue ) ) * ( intAnalogXReading - cintMinXValue ) ) - cintMaxMouseMovement );
    //it could use some improvement, like making it trigonometric.
  }
  else
  {
    //Within the zero threshold, the cursor does not move in the X.
    intMouseXMovement = 0;
  }

  //If the analog Y reading is ouside of the zero threshold... 
  if( cintMovementThreshold < abs( intAnalogYReading - cintZeroYValue ) )
  {
    //...calculate Y mouse movement based on how far the Y acceleration is from its zero value.
    intMouseYMovement = cintYSign * ( ( ( (float)( 2 * cintMaxMouseMovement ) / ( cintMaxYValue - cintMinYValue ) ) * ( intAnalogYReading - cintMinYValue ) ) - cintMaxMouseMovement );
    //it could use some improvement, like making it trigonometric.
  }
  else
  {
    //Within the zero threshold, the cursor does not move in the Y.
    intMouseYMovement = 0;
  }
 
  Mouse.move(intMouseXMovement, intMouseYMovement);

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
