const int pinAnalogXInput = 3;
const int pinAnalogYInput = 1;
const int pinAnalogZInput = 2;
const int pinAnalogDummyInput = 0;

const int pinBtnA = 0;
const int pinBtnB = 1;
const int pinBtnX = 2;
const int pinBtnY = 3;

const int pinBtnUp = 4;
const int pinBtnDown = 5;
const int pinBtnLeft = 6;
const int pinBtnRight = 7;

const int pinBtnTrigLeft = 8;
const int pinBtnTrigRight = 9;
const int pinBtnSelect = 10;

//For some reason, it is not possible to get a digital read from
//pin 12 or for as far as I can tell, any analog capable pin.
//const int pinBtnStart = 12;
const int pinBtnStart = 23;

const int pinLEDOutput = 11;

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

//Variables for the mouse buttons.
boolean boolLeftMouseBtn;
boolean boolMiddleMouseBtn;
boolean boolRightMouseBtn;

//Variables for the states of the SNES buttons
boolean boolBtnA;
boolean boolBtnB;
boolean boolBtnX;
boolean boolBtnY;

boolean boolBtnTrigLeft;
boolean boolBtnTrigRight;

boolean boolBtnUp;
boolean boolBtnDown;
boolean boolBtnLeft;
boolean boolBtnRight;

boolean boolBtnSelect;
boolean boolBtnStart;

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

  pinMode( pinBtnA, INPUT );
  pinMode( pinBtnB, INPUT );
  pinMode( pinBtnX, INPUT );
  pinMode( pinBtnY, INPUT );
  
  pinMode( pinBtnUp, INPUT );
  pinMode( pinBtnDown, INPUT );
  pinMode( pinBtnLeft, INPUT );
  pinMode( pinBtnRight, INPUT );
  
  pinMode( pinBtnTrigLeft, INPUT );
  pinMode( pinBtnTrigRight, INPUT );
  pinMode( pinBtnSelect, INPUT );
  
  //Special for the Teensy is the INPUT_PULLUP
  //It enables a pullup resitor on the pin.
  pinMode( pinBtnStart, INPUT_PULLUP );

  //Zero the mouse buttons:
  boolLeftMouseBtn = false;
  boolMiddleMouseBtn = false;
  boolRightMouseBtn = false;
  
  //Zero the SNES controller button keys:
  boolBtnA = false;
  boolBtnB = false;
  boolBtnX = false;
  boolBtnY = false;
  
  boolBtnTrigLeft = false;
  boolBtnTrigRight = false;
  
  boolBtnUp = false;
  boolBtnDown = false;
  boolBtnLeft = false;
  boolBtnRight = false;
  
  boolBtnSelect = false;
  boolBtnStart = false;

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

  //Uncomment these lines to debug the accelerometer values:
//  Serial.print("X:\t");
//  Serial.print(analogRead(pinAnalogXInput));
//  Serial.print("\tY:\t");
//  Serial.print(analogRead(pinAnalogYInput));
//  Serial.print("\tZ:\t");
//  Serial.println(analogRead(pinAnalogZInput));

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
  //Assign temporary values for the buttons.
  //Remember, the SNES buttons are read as active LOW.
  //Capture their status here:
  boolean boolTempBtnA = !digitalRead(pinBtnA);
  boolean boolTempBtnB = !digitalRead(pinBtnB);  
  boolean boolTempBtnX = !digitalRead(pinBtnX);
  boolean boolTempBtnY = !digitalRead(pinBtnY);
  
  boolean boolTempBtnTrigLeft = !digitalRead(pinBtnTrigLeft);
  boolean boolTempBtnTrigRight = !digitalRead(pinBtnTrigRight);
  
  boolean boolTempBtnUp = !digitalRead(pinBtnUp);
  boolean boolTempBtnDown = !digitalRead(pinBtnDown);
  boolean boolTempBtnLeft = !digitalRead(pinBtnLeft);
  boolean boolTempBtnRight = !digitalRead(pinBtnRight);
  
  boolean boolTempBtnSelect = !digitalRead(pinBtnSelect);
  boolean boolTempBtnStart = !digitalRead(pinBtnStart);
  

  //If the A, B, or Y buttons are different from last time,
  //send an update of the buttons.
  //This has to be done, otherwise the Teensy constantly sends
  //an update to the host that a button has been pressed,
  //which really bogs everything down.
  //So use this if statment for any buttons that should not be
  //repeated until released.
  if( ( boolTempBtnA != boolBtnA ) ||
      ( boolTempBtnB != boolBtnB ) ||
      ( boolTempBtnY != boolBtnY ) )
  {  
    //Assign temporary values to the real values:
    boolBtnA = boolTempBtnA;
    boolBtnB = boolTempBtnB;
    boolBtnY = boolTempBtnY;
    
    //Update the mouse button status:
    Mouse.set_buttons(boolBtnB,
                    false,
                    boolBtnA);

    
    //If the Y button was pressed...
    if ( true == boolBtnY )
    {
      //Set the key modifier to the control key
      Keyboard.set_modifier( MODIFIERKEY_CTRL );
    }
    else
    {
      //Set the key modifier to the control key
      Keyboard.set_modifier( 0 );
    }

  }
  

  
  boolBtnUp = boolTempBtnUp;
  boolBtnDown = boolTempBtnDown;
  boolBtnLeft = boolTempBtnLeft;
  boolBtnRight = boolTempBtnRight;
  
  boolBtnX = boolTempBtnX;
  
  boolBtnTrigLeft = boolTempBtnTrigLeft;
  boolBtnTrigRight = boolTempBtnTrigRight;
  


  //Due to the shape of the D-pad only up or down can be pressed
  //at the same time.
  //This is useful as we can only send 6 keys at the same time.
  
  //These two lines are sickenly cute, but do not make much sense, kept here for posterity.
  //Keyboard.set_key1((boolBtnUp ^ boolBtnDown) * ((KEY_W * boolBtnUp) + (KEY_S * boolBtnDown)));
  //Keyboard.set_key2((boolBtnLeft ^ boolBtnRight) * ((KEY_A * boolBtnLeft) + (KEY_D * boolBtnRight)));
  //Use if statements for clarity.

  //If the up button was pressed and not the down button...
  if ( ( true == boolBtnUp ) && ( false == boolBtnDown ) )
  {
    //Set key1 to the 'W' key
    Keyboard.set_key1( KEY_W );
  }
  //If the down button was pressed and not the up button...
  else if ( ( false == boolBtnUp ) && ( true == boolBtnDown ) )
  {
    //Set key1 to the 'S' key
    Keyboard.set_key1( KEY_S );
  }
  //All else: both up and down butttons pressed or none pressed.
  else
  {
    //Set key1 to send nothing
    Keyboard.set_key1( 0 );
  }

  //If the left button was pressed and not the right button...
  if ( ( true == boolBtnLeft ) && ( false == boolBtnRight ) )
  {
    //Set key2 to the 'A' key
    Keyboard.set_key2( KEY_A );
  }
  //If the right button was pressed and not the left button...
  else if ( ( false == boolBtnLeft ) && ( true == boolBtnRight ) )
  {
    //Set key2 to the 'D' key
    Keyboard.set_key2( KEY_D );
  }
  //All else: both left and right butttons pressed or none pressed.
  else
  {
    //Set key2 to send nothing
    Keyboard.set_key2( 0 );
  }
  
  //If the X button was pressed...
  if ( true == boolBtnX )
  {
    //Set key3 to the space key
    Keyboard.set_key3( KEY_SPACE );
  }

  //If the Left trigger button was pressed...
  if ( true == boolBtnTrigLeft )
  {
    //Set key4 to the tab key
    Keyboard.set_key4( KEY_TAB );
  }

  //If the Right trigger button was pressed...
  if ( true == boolBtnTrigRight )
  {
    //Set key5 to the 'E' key
    Keyboard.set_key5( KEY_E );
  }

  //If the Select or Start buttons have changed since last time...
  if (  ( boolBtnSelect != boolTempBtnSelect ) ||
        ( boolBtnStart != boolTempBtnStart ) )
  {

    //Update the buttons' statuses.
    boolBtnSelect = boolTempBtnSelect;
    boolBtnStart = boolTempBtnStart;

    //Process the start and select buttons, they can only use
    //one key channel together so pressing both of them will only
    //send the key assigned to the start button
    //If the Start button was pressed...
    if ( true == boolBtnStart )
    {
      //Set key6 to the Escape key
      Keyboard.set_key6( KEY_ESC );
    }  
    //If the Start button was not pressed but the Select button
    //was pressed...
    else if ( true == boolBtnSelect )
    {
      //Set key6 to the Enter key
      Keyboard.set_key6( KEY_ENTER );
    }
    else
    {
      //Set key6 to send nothing
      Keyboard.set_key6( 0 );
    }

  }



  //Send all of the set keys.
  Keyboard.send_now();

  //Send an empty set of keys. The modifier key must be kept.
  if ( true == boolBtnY )
  {
    Keyboard.set_modifier( MODIFIERKEY_CTRL );
  }
  else
  {
    Keyboard.set_modifier( 0 );
  }
  
  Keyboard.set_key1( 0 );
  Keyboard.set_key2( 0 );
  Keyboard.set_key3( 0 );
  Keyboard.set_key4( 0 );
  Keyboard.set_key5( 0 );
  Keyboard.set_key6( 0 );

  Keyboard.send_now();



}
