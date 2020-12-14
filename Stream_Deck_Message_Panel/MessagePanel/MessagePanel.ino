// Message Panel
// Reads an Adafruit IO Feed, then formats and displays the message
// Author: Melissa LeBlanc-Williams

#include <RGBmatrixPanel.h>
#include <SPI.h>

#define BASE_CHAR_WIDTH 6   // 5 pixels + 1 space
#define BASE_CHAR_HEIGHT 8  // 7 pixels + 1 space

// Most of the signal pins are configurable, but the CLK pin has some
// special constraints.  On 8-bit AVR boards it must be on PORTB...
// Pin 8 works on the Arduino Uno & compatibles (e.g. Adafruit Metro),
// Pin 11 works on the Arduino Mega.  On 32-bit SAMD boards it must be
// on the same PORT as the RGB data pins (D2-D7)...
// Pin 8 works on the Adafruit Metro M0 or Arduino Zero,
// Pin A4 works on the Adafruit Metro M4 (if using the Adafruit RGB
// Matrix Shield, cut trace between CLK pads and run a wire to A4).

//#define CLK  8   // USE THIS ON ADAFRUIT METRO M0 or adapting to use Airlift, etc.
#define CLK A4 // USE THIS ON METRO M4 (not M0)
#define OE   9
#define LAT 10
#define A   A0
#define B   A1
#define C   A2
#define D   A3

RGBmatrixPanel matrix(A, B, C, D, CLK, LAT, OE, false, 64);

#include "config.h"

// set up the 'messagepanel' feed
AdafruitIO_Feed *counter = io.feed("messagepanel");

void drawText(const char *text, bool resetPosition = true, uint16_t color = 0xffff, uint16_t textSize = 1) {
  matrix.setTextSize(textSize);     // size 1 == 8 pixels high
  if (resetPosition) {
    matrix.setCursor(0, 0);    // start at top left, with 8 pixel of spacing
  }
  matrix.setTextColor(color);
  matrix.print(text);
}

// This function is called whenever a 'messagepanel' message
// is received from Adafruit IO. it was attached to
// the counter feed in the setup() function above.
void handleMessage(AdafruitIO_Data *data) {
  String message = data->toString();
  String plainText = data->toString();
  uint16_t color = matrix.Color333(7, 7, 7);
  uint16_t textSize = 1;
  uint16_t colorStartIndex = 0, colorEndIndex = 0;
  uint16_t sizeStartIndex = 0, sizeEndIndex = 0;
  uint16_t strpos = 0;
  byte lineLengths[] = {0, 0, 0, 0};
  byte lineNum = 0;
  byte messageHeight = 0;
  byte lineHeight = 0;
  // Calculate line lengths
  boolean paramRead = false;
  boolean newLine = false;
  
  matrix.setCursor(0, 0);
  matrix.fillScreen(matrix.Color333(0, 0, 0));

  // Strip out all color data first
  while(strpos < plainText.length()) {
    colorStartIndex = plainText.indexOf('{');
    colorEndIndex = plainText.indexOf('}');
    plainText.remove(colorStartIndex, colorEndIndex - colorStartIndex + 1);
    strpos++;
  }

  // Calculate the line lengths in pixels for fixed width text
  strpos = 0;
  while(strpos < plainText.length()) {
    sizeStartIndex = plainText.indexOf('<');
    sizeEndIndex = plainText.indexOf('>');

    if (strpos == sizeStartIndex) {
      textSize = atoi(plainText.substring(sizeStartIndex + 1, sizeEndIndex).c_str());
      plainText.remove(sizeStartIndex, sizeEndIndex - sizeStartIndex + 1);
    }
    
    if (plainText.charAt(strpos) != '\n') {
      lineLengths[lineNum] += textSize * BASE_CHAR_WIDTH;
      if (textSize * BASE_CHAR_HEIGHT > lineHeight) {
        lineHeight = textSize * BASE_CHAR_HEIGHT;
      }
    }

    // We want to keep adding up the characters * textSize until we hit a newline character
    // or we reach the width of the message panel. Then we go down to the next line
    if (plainText.charAt(strpos) == '\n' || lineLengths[lineNum] >= matrix.width()) {
      messageHeight += lineHeight;
      lineHeight = 0;
      lineNum++;
    }
    
    strpos++;
  }

  // Add the last line
  messageHeight += lineHeight;

  textSize = 1;
  lineNum = 0;
  for(uint16_t i=0; i<message.length(); i++) {
    if (message.charAt(i) == '{') {
      paramRead = true;
      colorStartIndex = i + 1;
    } else if (message.charAt(i) == '}') {
      paramRead = false;
      int wheelPos = atoi(message.substring(colorStartIndex, i).c_str());
      if (wheelPos < 24) {
        color = Wheel(wheelPos);
      } else {
        color = matrix.Color333(7, 7, 7);
      }
    } else if (message.charAt(i) == '<') {
      paramRead = true;
      sizeStartIndex = i + 1;
    } else if (message.charAt(i) == '>') {
      paramRead = false;
      textSize = atoi(message.substring(sizeStartIndex, i).c_str());
    } else {
      if (paramRead) continue;

      if (matrix.getCursorX() == 0 && matrix.getCursorY() == 0) {
        matrix.setCursor(floor((matrix.width() / 2) - (lineLengths[lineNum] / 2)), matrix.height() / 2 - messageHeight / 2);
      } else if (newLine) {
        matrix.setCursor(floor((matrix.width() / 2) - (lineLengths[++lineNum] / 2)), matrix.getCursorY());
        newLine = false;
      }
      drawText(message.substring(i, i+1).c_str(), false, color, textSize);
      if (message.charAt(i) == '\n' || matrix.getCursorX() >= matrix.width()) {
        newLine = true;
      }
    }
  } 
}

void setup() {
  matrix.begin();

  // fill the screen with 'black'
  matrix.fillScreen(matrix.Color333(0, 0, 0));
  // draw some text!
  matrix.setTextWrap(true);
  drawText("Connecting...");
  Serial.begin(115200);
  io.connect();

  counter->onMessage(handleMessage);

  while(io.mqttStatus() < AIO_CONNECTED) {
    drawText(".");
    delay(500);
  }  

  counter->get();

  Serial.println();
  Serial.println(io.statusText());
}

void loop() {
  io.run();
}

// Input a value 0 to 23 to get a color value.
// The colours are a transition r - g - b - back to r.
uint16_t Wheel(byte WheelPos) {
  if(WheelPos < 8) {
   return matrix.Color333(7 - WheelPos, WheelPos, 0);
  } else if(WheelPos < 16) {
   WheelPos -= 8;
   return matrix.Color333(0, 7 - WheelPos, WheelPos);
  } else {
   WheelPos -= 16;
   return matrix.Color333(WheelPos, 0, 7 - WheelPos);
  }
}
