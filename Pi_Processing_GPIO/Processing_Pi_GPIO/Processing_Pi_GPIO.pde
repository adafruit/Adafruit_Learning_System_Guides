// Processing on Raspberry Pi GPIO Example
// Author: Tony DiCola
//
// Note this code is for Processing and not Arduino
//
// See the guide for this sketch at:
//  https://learn.adafruit.com/processing-on-the-raspberry-pi-and-pitft/overview
//
// Released under a MIT license:
//  https://opensource.org/licenses/MIT

// Import hardware IO library.
import processing.io.*;


// Pin numbers for the LEDs and button connected to the Pi:
int redLEDPin   = 22;
int greenLEDPin = 27;
int buttonPin   = 17;

// Variables to hold the width and height of the buttons.
// This will be set based on the size of the screen.
int buttonWidth;
int buttonHeight;

// LED state, on or off (true or false).
boolean redLED = false;
boolean greenLED = false;


void setup() {
  // Go fullscreen and hide the cursor.
  fullScreen();
  noCursor();

  // Initialize LEDs as outputs.
  GPIO.pinMode(redLEDPin, GPIO.OUTPUT);
  GPIO.pinMode(greenLEDPin, GPIO.OUTPUT);

  // Initialize button as input.
  GPIO.pinMode(buttonPin, GPIO.INPUT);

  // Turn the LEDs off.
  GPIO.digitalWrite(redLEDPin, false);
  GPIO.digitalWrite(greenLEDPin, false);

  // Compute button width and height based on screen width and height.
  buttonWidth = width/5;
  buttonHeight = height/3;

  // Default to drawing black lines around buttons.
  stroke(0, 0, 0);
}

void draw() {
  // Check button state to see if it's pressed.  Because there's a pull-up
  // resistor to 3.3V the button pin will be at high level until the button
  // is pressed and it drops to a low level.
  if (GPIO.digitalRead(buttonPin) == GPIO.LOW) {
    // Blue background when button pressed.
    background(0, 0, 255);
  }
  else {
    // Gray background when button isn't pressed.
    background(100, 100, 100);
  }

  // Draw red LED button.
  if (redLED) {
    // Fill button with red when on.
    fill(255, 0, 0);
  }
  else {
    // Otherwise fill with white.
    fill(255, 255, 255);
  }
  rect(buttonWidth, buttonHeight, buttonWidth, buttonHeight);

  // Draw green LED button.
  if (greenLED) {
    // Fill button with red when on.
    fill(0, 255, 0);
  }
  else {
    // Otherwise fill with white.
    fill(255, 255, 255);
  }
  rect(3*buttonWidth, buttonHeight, buttonWidth, buttonHeight);
}

void mousePressed() {
  // Check if red LED button pressed.
  if (overRect(buttonWidth, buttonHeight, buttonWidth, buttonHeight)) {
    // Button pressed, invert the red LED state and turn on/off the LED.
    redLED = !redLED;
    GPIO.digitalWrite(redLEDPin, redLED);

  }
  // Check if green LED button pressed.
  if (overRect(3*buttonWidth, buttonHeight, buttonWidth, buttonHeight)) {
    // Button pressed, invert the green LED state and turn on/off the LED.
    greenLED = !greenLED;
    GPIO.digitalWrite(greenLEDPin, greenLED);
  }
}

boolean overRect(int x, int y, int width, int height)  {
  // Check if the mouse is inside the provided box (defined by x, y position
  // and width, height).
  if (mouseX >= x && mouseX <= x+width &&
      mouseY >= y && mouseY <= y+height) {
    return true;
  } else {
    return false;
  }
}
