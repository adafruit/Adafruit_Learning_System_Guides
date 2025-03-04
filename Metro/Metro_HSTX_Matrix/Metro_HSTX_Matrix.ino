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
const int ANIMATION_SPEED = 70; // milliseconds between updates

// Initialize display for Adafruit Metro RP2350
DVHSTXText display({14, 18, 16, 12});  // Adafruit Metro HSTX Pinout

// Define structures for character streams
struct CharStream {
  int x;          // X position
  int y;          // Y position (head of the stream)
  int length;     // Length of the stream
  int speed;      // How many frames to wait before moving
  int countdown;  // Counter for movement
  bool active;    // Whether this stream is currently active
  char chars[30]; // Characters in the stream
};

// Array of character streams - increased for higher density
// To fill 60-75% of the screen width (91 chars), we need around 55-68 active streams
CharStream streams[250]; // Allow for decent density

// Stream creation rate (higher = more frequent new streams)
const int STREAM_CREATION_CHANCE = 65; // % chance per frame to create new stream

// Initial streams to create at startup
const int INITIAL_STREAMS = 30;

// Random characters that appear in the streams
const char matrixChars[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()-_=+[]{}|;:,.<>?/\\";
const int numMatrixChars = sizeof(matrixChars) - 1;

// Function declarations
void initStreams();
void updateStreams();
void drawStream(CharStream &stream);
void createNewStream();
char getRandomChar();

void setup() {
  // Initialize the display
  display.begin();
  display.clear();
  
  // Seed the random number generator
  randomSeed(analogRead(A0));
  
  // Initialize all streams
  initStreams();
}

void loop() {
  // Update and draw all streams
  updateStreams();
  
  // Randomly create new streams at a higher rate
  if (random(100) < STREAM_CREATION_CHANCE) {
    createNewStream();
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

void createNewStream() {
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
      
      // Fill with random characters
      for (int j = 0; j < streams[i].length; j++) {
        streams[i].chars[j] = getRandomChar();
      }
      
      return;
    }
  }
}

void updateStreams() {
  display.clear();
  
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
}

void drawStream(CharStream &stream) {
  for (int i = 0; i < stream.length; i++) {
    int y = stream.y - i;
    
    // Only draw if the character is on screen
    if (y >= 0 && y < SCREEN_HEIGHT) {
      display.setCursor(stream.x, y);
      
      // Set different colors/intensities based on position in the stream
      if (i == 0) {
        // Head of the stream is white (brightest)
        display.setColor(TextColor::TEXT_WHITE, TextColor::BG_BLACK, TextColor::ATTR_NORMAL_INTEN);
      } else if (i < 3) {
        // First few characters are bright green
        display.setColor(TextColor::TEXT_GREEN, TextColor::BG_BLACK, TextColor::ATTR_NORMAL_INTEN);
      } else if (i < 6) {
        // Next few are medium green
        display.setColor(TextColor::TEXT_GREEN, TextColor::BG_BLACK, TextColor::ATTR_LOW_INTEN);
      } else {
        // The rest are dim green
        display.setColor(TextColor::TEXT_GREEN, TextColor::BG_BLACK, TextColor::ATTR_V_LOW_INTEN);
      }
      
      // Draw the character
      display.write(stream.chars[i]);
    }
  }
  
  // Occasionally change a character in the stream
  if (random(100) < 25) { // 25% chance
    int idx = random(stream.length);
    stream.chars[idx] = getRandomChar();
  }
}

char getRandomChar() {
  return matrixChars[random(numMatrixChars)];
}
