#define KEYREPEAT 85 // delay when repeating characters
#define KEYDELAY 200 // delay from first to second character
const int pinAnalogXInput = 3;
const int pinAnalogYInput = 1;
const int pinAnalogZInput = 2;
const int pinAnalogDummyInput = 0;

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

// here is where we define the buttons that we'll use. button "1" is the first, button "6" is the 6th, etc
byte buttons[] = {pinBtnUp, pinBtnRight, pinBtnDown, pinBtnLeft, pinBtnSelect, pinBtnStart,
pinBtnB, pinBtnA, pinBtnY, pinBtnX, pinBtnTrigLeft, pinBtnTrigRight}; 
byte keys[] = {KEY_UP, KEY_RIGHT, KEY_DOWN, KEY_LEFT, KEY_F1, KEY_F2, KEY_SPACE, KEY_SPACE, KEY_4, KEY_5, KEY_ESC, KEY_ENTER};

#define NUMBUTTONS sizeof(buttons)

// we will track if a button is just pressed, just released, or 'currently pressed' 
volatile byte pressed[NUMBUTTONS], justpressed[NUMBUTTONS], justreleased[NUMBUTTONS];


const int pinLEDOutput = 11;

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
  //Serial.begin(19200);
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
  byte flag = 0;
  static long currentkey = 0;
  static long repeat = 0;
  
  for (byte i = 0; i < NUMBUTTONS; i++) {

    if ( !digitalRead(buttons[i])) {
      flag = 1;
      if (currentkey != keys[i]) {
        // unset the old key
        Keyboard.set_key1(0);
        Keyboard.send_now();
        Keyboard.set_key1(keys[i]);
        currentkey = keys[i];
        Keyboard.send_now();
        repeat = 0;
      } else {
        if (! repeat) {
          delay(KEYDELAY);
        } else {
         // resend 
         repeat = 1;
         Keyboard.set_key1(keys[i]);
         Keyboard.send_now();
         delay(KEYREPEAT);
       }
      }
    }
  }
   if ( currentkey && !flag) {
     currentkey = 0;
     Keyboard.set_key1(0);
     Keyboard.send_now();
  }
}
