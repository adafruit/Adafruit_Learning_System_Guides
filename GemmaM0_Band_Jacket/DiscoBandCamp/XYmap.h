//  Helper functions for a two-dimensional XY matrix of pixels.
//  Special credit to Mark Kriegsman for RGB Shades Kickstarter 2014-10-18
//  https://www.kickstarter.com/projects/macetech/rgb-led-shades
//
//  This special 'XY' code lets you program as a plain matrix.
//
//  Writing to and reading from the 'holes' in the layout is 
//  also allowed; holes retain their data, it's just not displayed.
//
//  You can also test to see if you're on or off the layout
//  like this
//  if( XY(x,y) > LAST_VISIBLE_LED ) { ...off the layout...}
//
//  X and Y bounds checking is also included, so it is safe
//  to just do this without checking x or y in your code:
//  leds[ XY(x,y) ] == CRGB::Red;
//  All out of bounds coordinates map to the first hidden pixel.
//
//  XY(x,y) takes x and y coordinates and returns an LED index number,
//  for use like this:  leds[ XY(x,y) ] == CRGB::Red;


// Parameters for width and height
const uint8_t kMatrixWidth = 24;
const uint8_t kMatrixHeight = 8;
const uint8_t kBorderWidth = 2; //for swirly

#define NUM_LEDS (kMatrixWidth * kMatrixHeight)
CRGB leds[ NUM_LEDS ];

// This function will return the right 'led index number' for 
// a given set of X and Y coordinates on DiscoBandCamp
// This code, plus the supporting 80-byte table is much smaller 
// and much faster than trying to calculate the pixel ID with code.
#define LAST_VISIBLE_LED 119
uint8_t XY( uint8_t x, uint8_t y)
{
  // any out of bounds address maps to the first hidden pixel
  if( (x >= kMatrixWidth) || (y >= kMatrixHeight) ) {
    return (LAST_VISIBLE_LED + 1);
  }

//   On the visual left of DiscoBandCamp, wearers right
//     +------------------------------------------ 
//   | 10   9   8   7   6   5   4   3   2   1   0
//   | .    20  19  18  17  16  15  14  13  12  11
//   | .    .   29  28  27  26  25  24  23  22  21
//   | .    .   .   37  36  35  34  33  32  31  30  
//   | .    .   .   .   44  43  42  41  40  39  38
//   | .    .   .   .   .   50  49  48  47  46  45
//   | .    .   .   .   .   .   55  54  53  52  51  
//   | .    .   .   .   .   .   .   59  58  57  56

//this is how DiscoBandCamp works
  const uint8_t JacketTable[] = {
10, 9,  8,  7,  6,  5,  4,  3,  2,  1,  0,  145,
153,60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 
120,11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 146,  
154,80, 79, 78, 77, 76, 75, 74, 73, 72, 71, 182, 
121,127,21, 22, 23, 24, 25, 26, 27, 28, 29, 147, 
155,89, 88, 87, 86, 85, 84, 83, 82, 81, 176,183, 
122,128,133,30, 31, 32, 33, 34, 35, 36, 37, 148,  
156,97, 96, 95, 94, 93, 92, 91, 90, 171,177,184, 
123,129,134,135,38, 39, 40, 41, 42, 43, 44, 149,  
157,104,103,102,101,100,99, 98, 167,172,178,185, 
124,130,134,136,139,45, 46, 47, 48, 49, 50, 150,  
158,110,109,108,107,106,105,164,168,173,179,186, 
125,131,134,137,140,142,51, 52, 53, 54, 55, 151,  
159,115,114,113,112,111,162,165,169,174,180,187, 
126,132,134,138,141,143,144,56, 57, 58, 59, 152,  
160,119,118,117,116,161,163,166,170,175,181,188,
  };

  uint8_t i = (y * kMatrixWidth) + x;
  uint8_t j = JacketTable[i];
  return j;
}
