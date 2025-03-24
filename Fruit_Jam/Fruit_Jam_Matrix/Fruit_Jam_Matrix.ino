// SPDX-FileCopyrightText: 2021 Anne Barela for Adafruit Industries
//
// SPDX-License-Identifier: MIT
//
// Based on Adafruit-DVI-HSTX library code written by Jeff Epler
// and use of Claude 3.7 Sonnet on 3/2/2025
// https://claude.site/artifacts/cf022b66-50c3-43eb-b334-17fbf0ed791c

#include <Adafruit_dvhstx.h>

// Display configuration for text mode in Adafruit-DVI-HSTX
const int SCREEN_WIDTH = 91;
const int SCREEN_HEIGHT = 30;

// Animation speed (lower = faster)
// Adjust this value to change the speed of the animation
const int ANIMATION_SPEED = 1; // milliseconds between updates

// Initialize display for Adafruit Metro RP2350
DVHSTXText display(DVHSTX_PINOUT_DEFAULT, true); // Adafruit Metro HSTX Pinout

// Define structures for character streams
struct CharStream {
  int x;          // X position
  int y;          // Y position (head of the stream)
  int length;     // Length of the stream
  int speed;      // How many frames to wait before moving
  int countdown;  // Counter for movement
  int headColor;
  bool active;    // Whether this stream is currently active
  bool canFreeze;    // Whether this stream is currently active
  char chars[30]; // Characters in the stream
};

// Array of character streams - increased for higher density
// To fill 60-75% of the screen width (91 chars), we need around 55-68 active
// streams
CharStream streams[250]; // Allow for decent density

// Stream creation rate (higher = more frequent new streams)
const int STREAM_CREATION_CHANCE =
    65; // % chance per frame to create new stream

// Initial streams to create at startup
const int INITIAL_STREAMS = 30;

// Random characters that appear in the streams
const char matrixChars[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()-_=+[]{}|;:,.<>?/\\";
const int numMatrixChars = sizeof(matrixChars) - 1;

const char frozenLine1[] = " A D A F R U I T ";
const char frozenLine2[] = "                 ";
const char frozenLine3[] = "F R U I T   J A M";

constexpr size_t nFrozen = sizeof(frozenLine1) - 1;
const char *const frozenLines[] = {frozenLine1, frozenLine2, frozenLine3};
const int colorFrozen[3] = {
    TextColor::TEXT_WHITE,
    TextColor::TEXT_WHITE,
    TextColor::TEXT_MAGENTA,
};

constexpr auto frozenFirstRow = (SCREEN_HEIGHT / 2) - 1;
constexpr auto frozenFirstCol = (SCREEN_WIDTH - nFrozen) / 2;
bool isFrozen[3][nFrozen];

// Function declarations
void initStreams();
void updateStreams();
void drawStream(CharStream &stream);
int createNewStream();
char getRandomChar();

void setup() {
  // Initialize the display
  display.begin();
  display.clear();

  // Seed the random number generator
  randomSeed(analogRead(A0));

  // Initialize all streams
  initStreams();

  for (int fy = 0; fy < 3; fy++) {
    for (int fx = 0; fx < nFrozen; fx++) {
        int c = frozenLines[fy][fx];
        if (c == ' ')
          continue;
      isFrozen[fy][fx] = true;
    }
  }
}

bool anyActiveStreams() {
  for (int i = 0; i < sizeof(streams) / sizeof(streams[0]); i++) {
    if (streams[i].active)
      return true;
  }
  return false;
}
bool allFrozen() {
  for (int fy = 0; fy < 3; fy++) {
    for (int fx = 0; fx < nFrozen; fx++) {
        int c = frozenLines[fy][fx];
        if (c == ' ')
          continue;
      if (!isFrozen[fy][fx])
        return false;
    }
  }
  return true;
}

void loop() {
  // Update and draw all streams
  updateStreams();

  // Randomly create new streams at a higher rate
  if (random(100) < STREAM_CREATION_CHANCE) {
    if (allFrozen()) {
      if (!anyActiveStreams()) {
        memset(isFrozen, 0, sizeof(isFrozen));
        for (int fy = 0; fy < 3; fy++) {
          for (int fx = 0; fx < nFrozen; fx++) {
            int c = frozenLines[fy][fx];
            if (c == ' ')
              continue;
            int st;
            if ((st = createNewStream()) != -1) {
              streams[st].x = fx + frozenFirstCol;
              streams[st].y = fy + frozenFirstRow;
              streams[st].chars[0] = c;
              for (int i = 1; i < streams[st].length; i++) {
                streams[st].chars[i] = ' ';
              }
              streams[st].canFreeze = false;
              streams[st].headColor = colorFrozen[fy];
            }
          }
        }
      }
    } else {
      createNewStream();
    }
  }

  // Control animation speed
  delay(ANIMATION_SPEED);
}

void initStreams() {
  // Initialize all streams as inactive
  for (int i = 0; i < sizeof(streams) / sizeof(streams[0]); i++) {
    streams[i].active = false;
  }

  // Create more initial streams for immediate visual impact
  for (int i = 0; i < INITIAL_STREAMS; i++) {
    createNewStream();
  }
}

int createNewStream() {
  // Find an inactive stream
  for (int i = 0; i < sizeof(streams) / sizeof(streams[0]); i++) {
    if (!streams[i].active) {
      // Initialize the stream
      streams[i].x = random(SCREEN_WIDTH);
      streams[i].y = random(5) - 5; // Start above the screen
      streams[i].length = random(5, 20);
      streams[i].speed = random(1, 4);
      streams[i].countdown = streams[i].speed;
      streams[i].active = true;
      streams[i].headColor = TextColor::TEXT_WHITE;
      streams[i].canFreeze = true;

      // Fill with random characters
      for (int j = 0; j < streams[i].length; j++) {
        streams[i].chars[j] = getRandomChar();
      }

      return i;
    }
  }
  return -1;
}

void updateStreams() {
  display.clear();
  delay(30);

  // Count active streams (for debugging if needed)
  int activeCount = 0;

  for (int i = 0; i < sizeof(streams) / sizeof(streams[0]); i++) {
    if (streams[i].active) {
      activeCount++;
      streams[i].countdown--;

      // Time to move the stream down
      if (streams[i].countdown <= 0) {
        streams[i].y++;
        streams[i].countdown = streams[i].speed;

        // Change a random character in the stream
        int randomIndex = random(streams[i].length);
        streams[i].chars[randomIndex] = getRandomChar();
      }

      // Draw the stream
      drawStream(streams[i]);

      // Check if the stream has moved completely off the screen
      if (streams[i].y - streams[i].length > SCREEN_HEIGHT) {
        streams[i].active = false;
      }
    }
  }
  displayFrozen();
  display.swap();
}

bool handleFrozen(int x, int y, int i, bool canFreeze) {
  if (x < frozenFirstCol || y < frozenFirstRow)
    return false;
  int fx = x - frozenFirstCol;
  int fy = y - frozenFirstRow;
  if (fy > 2 || fx >= nFrozen)
    return false;
int c = frozenLines[fy][fx];
if (c == ' ')
  return false;
  if (!isFrozen[fy][fx]) {
    if (canFreeze && random(5) == 0) {
      isFrozen[fy][fx] = true;
    } else {
      return false;
    }
  }

  return true;
}

void displayFrozen() {
  for (int fy = 0; fy < 3; fy++) {
    display.setColor(colorFrozen[fy]);
    for (int fx = 0; fx < nFrozen; fx++) {
      int x = fx + frozenFirstCol;
      int y = fy + frozenFirstRow;
      if (isFrozen[fy][fx]) {
        display.setCursor(x, y);
        display.write(frozenLines[fy][fx]);
      }
    }
  }
}

void drawStream(CharStream &stream) {
  for (int i = 0; i < stream.length; i++) {
    int y = stream.y - i;
    int x = stream.x;
    // Only draw if the character is on screen
    if (y >= 0 && y < SCREEN_HEIGHT) {
      display.setCursor(x, y);

      // Set different colors/intensities based on position in the stream
      if (i == 0) {
        // Head of the stream is white (brightest)
        display.setColor(stream.headColor);
      } else if (i < 3) {
        // First few characters are bright green
        display.setColor(TextColor::TEXT_GREEN, TextColor::BG_BLACK,
                         TextColor::ATTR_NORMAL_INTEN);
      } else if (i < 6) {
        // Next few are medium green
        display.setColor(TextColor::TEXT_GREEN, TextColor::BG_BLACK,
                         TextColor::ATTR_LOW_INTEN);
      } else {
        // The rest are dim green
        display.setColor(TextColor::TEXT_GREEN, TextColor::BG_BLACK,
                         TextColor::ATTR_V_LOW_INTEN);
      }

      // Draw the character
      if (!handleFrozen(x, y, i, stream.canFreeze)) {
        display.write(stream.chars[i]);
      }
    }
  }

  // Occasionally change a character in the stream
  if (random(100) < 25) { // 25% chance
    int idx = random(stream.length);
    stream.chars[idx] = getRandomChar();
  }
}

char getRandomChar() { return matrixChars[random(numMatrixChars)]; }
