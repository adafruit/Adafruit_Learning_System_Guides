// SPDX-FileCopyrightText: Adafruit Industries
//
// SPDX-License-Identifier: MIT

#define WIFI_SSID "your_wifi_ssid"
#define WIFI_PASS "your_wifi_password"

// visit io.adafruit.com if you need to create an account,
// or if you need your Adafruit IO key.
#define IO_USERNAME "your_io_username"
#define IO_KEY      "your_io_key"

#define FEED_OWNER "feed_owner_name"
#define FEED_NAME  "cheekmate"

#define REPS           3        // Max number of times to repeat new message
#define WPM            15       // Morse code words-per-minute
#define BUZZ           255      // Haptic buzzer amplitude, 0-255
#define LED_BRIGHTNESS 50       // NeoPixel brightness 1-255, or 0 to disable
#define LED_COLOR      0xFF0000 // NeoPixel color (RGB hexadecimal)

// These values are derived from the 'WPM' setting above and do not require
// manual editing. The dot, dash and gap times are set according to accepted
// Morse code procedure.
#define DOT_LENGTH    1200 / WPM       // Duration of one Morse dot
#define DASH_LENGTH   (DOT_LENGTH * 3) // Duration of one Morse dash
#define SYMBOL_GAP    DOT_LENGTH       // Duration of gap between dot or dash
#define CHARACTER_GAP (DOT_LENGTH * 3) // Duration of gap between characters
#define MEDIUM_GAP    (DOT_LENGTH * 7) // Duraction of gap between words

// Morse code symbol-to-mark conversion dictionary. This contains the
// standard A-Z and 0-9, and extra symbols "+" and "=" sometimes used
// in chess. If other symbols are needed for this or other games, they
// can be added to the end of the list.
const struct {
  char symbol;
  char *mark;
} morse[] = {
    'A', (char *)".-",
    'B', (char *)"-...",
    'C', (char *)"-.-.",
    'D', (char *)"-..",
    'E', (char *)".",
    'F', (char *)"..-.",
    'G', (char *)"--.",
    'H', (char *)"....",
    'I', (char *)"..",
    'J', (char *)".---",
    'K', (char *)"-.-",
    'L', (char *)".-..",
    'M', (char *)"--",
    'N', (char *)"-.",
    'O', (char *)"---",
    'P', (char *)".--.",
    'Q', (char *)"--.-",
    'R', (char *)".-.",
    'S', (char *)"...",
    'T', (char *)"-",
    'U', (char *)"..-",
    'V', (char *)"...-",
    'W', (char *)".--",
    'X', (char *)"-..-",
    'Y', (char *)"-.--",
    'Z', (char *)"--..",
    '0', (char *)"-----",
    '1', (char *)".----",
    '2', (char *)"..---",
    '3', (char *)"...--",
    '4', (char *)"....-",
    '5', (char *)".....",
    '6', (char *)"-....",
    '7', (char *)"--...",
    '8', (char *)"---..",
    '9', (char *)"----.",
    '+', (char *)".-.-.",
    '=', (char *)"-...-",
};
#define NUM_SYMBOLS (sizeof morse / sizeof morse[0])
