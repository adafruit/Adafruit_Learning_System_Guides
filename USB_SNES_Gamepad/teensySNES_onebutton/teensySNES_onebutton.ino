const int pinBtnUp = 0;

const int pinLEDOutput = 11;

//Variables for the states of the SNES buttons
boolean boolBtnUp;


void setup()
{
  //Setup the pin modes.
  pinMode( pinLEDOutput, OUTPUT );
  //Special for the Teensy is the INPUT_PULLUP
  //It enables a pullup resitor on the pin.
  pinMode( pinBtnUp, INPUT_PULLUP );
 
  //Zero the SNES controller button keys:
  boolBtnUp = false;
 
}


void loop()
{
//  //debugging the start button...
  digitalWrite ( pinLEDOutput, digitalRead(pinBtnUp));

  //Progess the SNES controller buttons to send keystrokes.
  fcnProcessButtons();
  
}

//Function to process the buttons from the SNES controller
void fcnProcessButtons()
{
  //Assign temporary values for the buttons.
  //Remember, the SNES buttons are read as active LOW.
  //Capture their status here:
  boolean boolBtnUp = !digitalRead(pinBtnUp);
 
  if ( boolBtnUp )
  {
    //Set key1 to the U key
    Keyboard.set_key1( KEY_U );
  } else {
    Keyboard.set_key1( 0 );
  }
    
  //Send all of the set keys.
  Keyboard.send_now();


}
