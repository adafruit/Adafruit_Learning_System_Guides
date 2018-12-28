/* Live Launcher - Ableton Live controller for Adafruit Neotrellis M4
    by Collin Cunningham for Adafruit Industries
    https://www.adafruit.com/product/3938
*/

#include <Adafruit_NeoTrellisM4.h>

#define WIDTH      8
#define HEIGHT     4
#define N_BUTTONS  WIDTH*HEIGHT
#define NEO_PIN 10
#define NUM_KEYS 32
#define SERIAL_TIMEOUT 1000  //time before giving up on incoming serial data
#define COLOR_DATA_LENGTH 98   //number of total bytes to expect in incoming color data 
//4 bytes per color * 32 buttons = 128 bytes + 2 header bytes = 130 bytes total
#define BUTTON_DATA_LENGTH 5  //clip playing status message for each button
#define PULSE_DURATION 350  //length of 'now playing' pulse

unsigned long readTime; //time we start reading serial buffer
unsigned long lastPulseTime;
bool pulseOn = false;
uint8_t packetbuffer[COLOR_DATA_LENGTH]; //store incoming serial data
uint8_t colors[96];

Adafruit_NeoTrellisM4 trellis = Adafruit_NeoTrellisM4();

const byte ROWS = HEIGHT; // four rows
const byte COLS = WIDTH; // eight columns
byte trellisKeys[ROWS][COLS] = {  //define the symbols on the buttons of the keypads
  {1,  2,  3,  4,  5,  6,  7,  8},
  {9,  10, 11, 12, 13, 14, 15, 16},
  {17, 18, 19, 20, 21, 22, 23, 24},
  {25, 26, 27, 28, 29, 30, 31, 32}
};
byte rowPins[ROWS] = {14, 15, 16, 17}; //connect to the row pinouts of the keypad
byte colPins[COLS] = {2, 3, 4, 5, 6, 7, 8, 9}; //connect to the column pinouts of the keypad
Adafruit_Keypad customKeypad = Adafruit_Keypad( makeKeymap(trellisKeys), rowPins, colPins, ROWS, COLS); //initialize keypad
extern const uint8_t gamma8[];

boolean pressed[N_BUTTONS] = {false};        // Pressed state for each button
uint8_t playing[N_BUTTONS] = {0};        // Playing state for each button

void setup() {
  Serial.begin(57600);
  //  while (!Serial) {}

  trellis.begin();
  trellis.setBrightness(255);
  trellis.fill(0);
}


void loop() {
  unsigned long startTime = millis();

  if (Serial.available() >= BUTTON_DATA_LENGTH) {
    parseData();
  }

  //send press events to Live via serial
  trellis.tick();
  while (trellis.available()) {
    keypadEvent e = trellis.read();
    uint8_t i = e.bit.KEY;
    if (e.bit.EVENT == KEY_JUST_PRESSED) {
      pressed[i] = true;
      Serial.write(i);
    }
    else if (e.bit.EVENT == KEY_JUST_RELEASED) {
      pressed[i] = false;
    }
  }

  if ((startTime - lastPulseTime) >= PULSE_DURATION) {

    //flash any clip which is playing
    if (pulseOn) {
      for (uint8_t i = 0; i < N_BUTTONS; i++) {
          setPixelWithColorsIndex(i, false);
      }
    }
    else {
      for (uint8_t i = 0; i < N_BUTTONS; i++) {
        if (playing[i]) {
          setPixelWithColorsIndex(i, true);
        }
        else setPixelWithColorsIndex(i, false);
      }
    }
    pulseOn = !pulseOn;
    lastPulseTime = millis();
  }
}

void parseData() {

  //check for ! start char
  if (Serial.read() == '!') {
    uint8_t id = Serial.read();

    //check for Color data
    if (id == 'C') {
      for (int i = 0; i < 96; i++) {
        colors[i] = Serial.read();
      }

      //color button leds
      for (int i = 0; i < N_BUTTONS; i++) {
        setPixelWithColorsIndex(i, false);
      }
    }

    //check for clip status data
    else if (id == 'B') {
      uint8_t x = Serial.read();
      uint8_t state = Serial.read();
      uint8_t y = Serial.read();

      if (state == 0) { //if state is 0, all clips in track are stopped
        for (int i = 0; i < HEIGHT; i++) {
          uint8_t index = i * WIDTH + x;
          playing[index] = state;
        }
      }

      else {  //all other clips in track should stop
        for (int i = 0; i < HEIGHT; i++) {
          uint8_t index = i * WIDTH + x;
          playing[index] = 0;
        }
        //save playing state
        uint8_t index = y * WIDTH + x;
        playing[index] = state;
      }
    }
  }
}

void setPixelWithColorsIndex(int i, bool dimmed) {

  uint8_t red = colors[i * 3];
  uint8_t green = colors[i * 3 + 1];
  uint8_t blue = colors[i * 3 + 2];
  if (dimmed) {
    setPixelWithGamma(i, red / 2, green / 2, blue / 2);
  }
  else {
    setPixelWithGamma(i, red, green, blue);
  }

}

void setPixelWithGamma(int pixelNumber, uint8_t red, uint8_t green, uint8_t blue) {

  uint32_t color = trellis.Color(
                     pgm_read_byte(&gamma8[red]),
                     pgm_read_byte(&gamma8[green]),
                     pgm_read_byte(&gamma8[blue]));

  trellis.setPixelColor(pixelNumber, color);
}

const uint8_t PROGMEM gamma8[] = {
  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,
  1,  1,  1,  1,  1,  1,  1,  1,  1,  2,  2,  2,  2,  2,  2,  2,
  2,  3,  3,  3,  3,  3,  3,  3,  4,  4,  4,  4,  4,  5,  5,  5,
  5,  6,  6,  6,  6,  7,  7,  7,  7,  8,  8,  8,  9,  9,  9, 10,
  10, 10, 11, 11, 11, 12, 12, 13, 13, 13, 14, 14, 15, 15, 16, 16,
  17, 17, 18, 18, 19, 19, 20, 20, 21, 21, 22, 22, 23, 24, 24, 25,
  25, 26, 27, 27, 28, 29, 29, 30, 31, 32, 32, 33, 34, 35, 35, 36,
  37, 38, 39, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 50,
  51, 52, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 66, 67, 68,
  69, 70, 72, 73, 74, 75, 77, 78, 79, 81, 82, 83, 85, 86, 87, 89,
  90, 92, 93, 95, 96, 98, 99, 101, 102, 104, 105, 107, 109, 110, 112, 114,
  115, 117, 119, 120, 122, 124, 126, 127, 129, 131, 133, 135, 137, 138, 140, 142,
  144, 146, 148, 150, 152, 154, 156, 158, 160, 162, 164, 167, 169, 171, 173, 175,
  177, 180, 182, 184, 186, 189, 191, 193, 196, 198, 200, 203, 205, 208, 210, 213,
  215, 218, 220, 223, 225, 228, 231, 233, 236, 239, 241, 244, 247, 249, 252, 255
};

