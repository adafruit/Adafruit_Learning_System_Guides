// Adafruit Bluefruit LE Feather Holiday Lights
// See the full guide at:
//   https://learn.adafruit.com/feather-holiday-lights/overview
// Author: Tony DiCola
// Based on the neopixel_picker example from the Adafruit Bluefruit nRF51 library.
// Released under a MIT license:
//   https://opensource.org/licenses/MIT
#include "Adafruit_BLE.h"
#include "Adafruit_BluefruitLE_SPI.h"
#include "Adafruit_NeoPixel.h"
#include "BluefruitConfig.h"
#include "SoftwareSerial.h"
#include "SPI.h"


#define PIXEL_COUNT 60    // The number of NeoPixels connected to the board.

#define PIXEL_PIN   6     // The pin connected to the input of the NeoPixels.

#define PIXEL_TYPE  NEO_GRB + NEO_KHZ800  // The type of NeoPixels, see the NeoPixel
                                          // strandtest example for more options.

#define ANIMATION_PERIOD_MS  300  // The amount of time (in milliseconds) that each
                                  // animation frame lasts.  Decrease this to speed
                                  // up the animation, and increase it to slow it down.


// Create NeoPixel strip from above parameters.
Adafruit_NeoPixel strip = Adafruit_NeoPixel(PIXEL_COUNT, PIXEL_PIN, PIXEL_TYPE);

// Create the Bluefruit object using hardware SPI (for Bluefruit LE feather).
Adafruit_BluefruitLE_SPI ble(BLUEFRUIT_SPI_CS, BLUEFRUIT_SPI_IRQ, BLUEFRUIT_SPI_RST);

// Global variable to hold the current pixel color.  Starts out red but will be
// changed by the BLE color picker.
int r = 255;
int g = 0;
int b = 0;

// Function prototypes and data over in packetparser.cpp
uint8_t readPacket(Adafruit_BLE *ble, uint16_t timeout);
float parsefloat(uint8_t *buffer);
void printHex(const uint8_t * data, const uint32_t numBytes);
extern uint8_t packetbuffer[];


void setup(void)
{
  Serial.begin(115200);
  Serial.println(F("Adafruit Bluefruit LE Holiday Lights"));

  // Initialize NeoPixels.
  strip.begin();
  strip.show();

  // Initialize BLE library.
  if (!ble.begin(false))
  {
    Serial.println(F("Couldn't find Bluefruit LE module!"));
    while (1);
  }
  ble.echo(false);

  Serial.println(F("Please use Adafruit Bluefruit LE app to connect in Controller mode"));
  Serial.println(F("Then activate/use the color picker to change color."));
  Serial.println();

  // Wait for connection.
  while (!ble.isConnected()) {
    // Make sure to animate the pixels while waiting!
    animatePixels(strip, r, g, b, ANIMATION_PERIOD_MS);
    delay(50);
  }
  ble.setMode(BLUEFRUIT_MODE_DATA);
}

void loop(void)
{
  // Animate the pixels.
  animatePixels(strip, r, g, b, ANIMATION_PERIOD_MS);
  
  // Grab a BLE controller packet if available.
  uint8_t len = readPacket(&ble, BLE_READPACKET_TIMEOUT);
  if (len == 0) return;

  // Parse a color packet.
  if (packetbuffer[1] == 'C') {
    // Grab the RGB values from the packet and change the light color.
    r = packetbuffer[2];
    g = packetbuffer[3];
    b = packetbuffer[4];
    // Print out the color that was received too:
    Serial.print ("RGB #");
    if (r < 0x10) Serial.print("0");
    Serial.print(r, HEX);
    if (g < 0x10) Serial.print("0");
    Serial.print(g, HEX);
    if (b < 0x10) Serial.print("0");
    Serial.println(b, HEX);
  }
}

void animatePixels(Adafruit_NeoPixel& strip, uint8_t r, uint8_t g, uint8_t b, int periodMS) {
  // Animate the NeoPixels with a simple theater chase/marquee animation.
  // Must provide a NeoPixel object, a color, and a period (in milliseconds) that controls how
  // long an animation frame will last.
  // First determine if it's an odd or even period.
  int mode = millis()/periodMS % 2;
  // Now light all the pixels and set odd and even pixels to different colors.
  // By alternating the odd/even pixel colors they'll appear to march along the strip.
  for (int i = 0; i < strip.numPixels(); ++i) {
    if (i%2 == mode) {
      strip.setPixelColor(i, r, g, b);  // Full bright color.
    }
    else {
      strip.setPixelColor(i, r/4, g/4, b/4);  // Quarter intensity color.
    }
  }
  strip.show();
}
