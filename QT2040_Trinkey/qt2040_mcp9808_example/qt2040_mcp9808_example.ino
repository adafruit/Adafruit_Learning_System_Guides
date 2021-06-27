/**************************************************************************/
/*!
This is a demo for the Adafruit QT2040 Trinkey and the MCP9808 temperature
sensor.
QT2040 Trinkey - https://www.adafruit.com/product/5056
MCP9808 - https://www.adafruit.com/product/5027

*/
/**************************************************************************/
#include "Adafruit_MCP9808.h"
#include <Adafruit_NeoPixel.h>

// Create the neopixel strip with the built in definitions NUM_NEOPIXEL and
// PIN_NEOPIXEL
Adafruit_NeoPixel pixel =
    Adafruit_NeoPixel(NUM_NEOPIXEL, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

// Create the MCP9808 temperature sensor object
Adafruit_MCP9808 mcp9808 = Adafruit_MCP9808();

long previousMillis = 0;
long intervalTemp = 2000;
bool last_button = false;

void setup() {
  Serial.begin(115200);
  delay(100);

  pinMode(PIN_SWITCH, INPUT_PULLUP); // Setup the BOOT button

  pixel.begin();
  pixel.setBrightness(20);
  pixel.show(); // Initialize all pixels to 'off'

  if (!mcp9808.begin(0x18)) {
    Serial.println("Couldn't find MCP9808! Check your connections and verify "
                   "the address is correct.");
    while (1)
      ;
  }

  mcp9808.setResolution(3);
}

uint8_t j = 0;

void loop() {
  bool curr_button = !digitalRead(PIN_SWITCH);

  pixel.setPixelColor(0, Wheel(j++));
  pixel.show();

  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis > intervalTemp) {
    previousMillis = currentMillis;
    // Read and print out the temperature.
    float c = mcp9808.readTempC();
    float f = mcp9808.readTempF();
    Serial.print("Temp: ");
    Serial.print(c, 4);
    Serial.print("*C\t and ");
    Serial.print(f, 4);
    Serial.println("*F.");
  }

  if (curr_button && !last_button) {
    Serial.println("Button pressed!");
  }
  if (!curr_button && last_button) {
    !Serial.println("Button released!");
  }
  last_button = curr_button;

  delay(10);
}

// Input a value 0 to 255 to get a color value.
// The colours are a transition r - g - b - back to r.
uint32_t Wheel(byte WheelPos) {
  if (WheelPos < 85) {
    return pixel.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
  } else if (WheelPos < 170) {
    WheelPos -= 85;
    return pixel.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  } else {
    WheelPos -= 170;
    return pixel.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
}
