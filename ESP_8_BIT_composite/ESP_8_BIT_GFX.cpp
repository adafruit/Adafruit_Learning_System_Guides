/*

Adafruit_GFX for ESP_8_BIT color composite video.

NOT AN OFFICIAL ADAFRUIT GRAPHICS LIBRARY.

Allows ESP32 Arduino sketches to draw to a composite video device using
Adafruit's graphics API.

NOTE RE:COLOR

Adafruit GFX is designed for 16-bit (RGB565) color, but ESP_8_BIT video
only handles 8-bit (RGB332) color. There are two ways to handle this,
specified by passsing "8" or "16" into the constructor:

8  = Truncate the 16-bit color values and use the lower 8 bits directly as
     RGB332 color. This is faster, but caller needs to know to use 8-bit
     color values. A good choice when writing new code using this library.
16 = Automatically extract the most significant 3 red, 3 green, and 2 blue
     bits from a 16-bit RGB565 color value to generate a RGB332 color.
     Performing this conversion slows down the code, but the caller does not
     need to know about the limitations. A good choice when reusing existing
     Adafruit GFX code that works in 16-bit color space.

An utility function RGB565toRGB332 is available to perform this conversion.

NOTE RE:ASPECT RATIO

Adafruit GFX assumes pixels are square, but this is not true of ESP_8_BIT
which has nonsquare pixels. (4:3 aspect ratio in a 256x240 frame buffer.)
Circles will look squashed as wide ovals, etc. This version of the API does
not offer any way to compensate, the caller has to deal with it.



Copyright (c) Roger Cheng

MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

*/

#include "ESP_8_BIT_GFX.h"

static const char *TAG = "ESP_8_BIT_GFX";

static const int16_t MAX_Y = 239;
static const int16_t MAX_X = 255;

/*
 * @brief Expose Adafruit GFX API for ESP_8_BIT composite video generator
 */
ESP_8_BIT_GFX::ESP_8_BIT_GFX(bool ntsc, uint8_t colorDepth)
  : Adafruit_GFX(MAX_X+1, MAX_Y+1)
{
  _pVideo = new ESP_8_BIT_composite(ntsc);
  if (NULL==_pVideo)
  {
    ESP_LOGE(TAG, "Video signal generator allocation failed");
    ESP_ERROR_CHECK(ESP_FAIL);
  }

  if (8 == colorDepth || 16 == colorDepth)
  {
    _colorDepth = colorDepth;
  }
  else
  {
    ESP_LOGE(TAG, "Unsupported color depth");
    ESP_ERROR_CHECK(ESP_FAIL);
  }

  // Default behavior is not to copy buffer upon swap
  copyAfterSwap = false;

  // Initialize performance tracking state
  _perfStart = 0;
  _perfEnd = 0;
  _waitTally = 0;
}

/*
 * @brief Call once to set up the API with self-allocated frame buffer.
 */
void ESP_8_BIT_GFX::begin()
{
  _pVideo->begin();
}

/*
 * @brief Calculate performance metrics, output as INFO log.
 * @return Number range from 0 to 10000. Higher values indicate more time
 * has been spent waiting for buffer swap, implying the rest of the code
 * ran faster and completed more quickly.
 */
uint32_t ESP_8_BIT_GFX::perfData()
{
  uint32_t fraction = getWaitFraction();

  if (_perfEnd < _perfStart)
  {
    ESP_LOGE(TAG, "Performance end time is earlier than start time.");
  }
  else
  {
    uint32_t duration = _perfEnd - _perfStart;
    if (duration < _waitTally)
    {
      ESP_LOGE(TAG, "Overall time duration is less than tally of wait times.");
    }
    else
    {
      uint32_t frames = _pVideo->getRenderedFrameCount() - _frameStart;
      uint32_t swaps = _pVideo->getBufferSwapCount() - _swapStart;
      uint32_t wholePercent = fraction/100;
      uint32_t decimalPercent = fraction%100;
      ESP_LOGI(TAG, "Waited %d.%d%%, missed %d of %d frames",
        wholePercent, decimalPercent, frames-swaps, frames);
    }
  }
  _perfStart = 0;
  _perfEnd = 0;
  _waitTally = 0;

  return fraction;
}

/*
 * @brief Wait for swap of front and back buffer. Gathers performance
 * metrics while waiting.
 */
void ESP_8_BIT_GFX::waitForFrame()
{
  // Track the old lines array in case we need to copy after swap
  uint8_t** oldLineArray = _pVideo->getFrameBufferLines();
  // Values to track time spent waiting for swap
  uint32_t waitStart = xthal_get_ccount();
  uint32_t waitEnd;

  if (waitStart < _perfEnd)
  {
    // CCount overflowed since last call, conclude this session.
    perfData();
  }
  if (0 == _waitTally)
  {
    // No wait tally signifies start of new session.
    _perfStart = waitStart;
    _frameStart = _pVideo->getRenderedFrameCount();
    _swapStart = _pVideo->getBufferSwapCount();
  }

  // Wait for swap of front and back buffer
  _pVideo->waitForFrame();

  if (copyAfterSwap)
  {
    uint8_t** newLineArray = _pVideo->getFrameBufferLines();

    // This must be kept in sync with how frame buffer memory
    // is allocated in ESP_8_BIT_composite::frameBufferAlloc()
    for (uint8_t chunk = 0; chunk < 15; chunk++)
    {
      memcpy(newLineArray[chunk*16], oldLineArray[chunk*16], 256*16);
    }
  }

  // Core clock count after we've finished waiting
  waitEnd = xthal_get_ccount();
  if (waitEnd < waitStart)
  {
    // CCount overflowed while we were waiting, perform calculation
    // ignoring the time spent waiting.
    _perfEnd = waitStart;
    perfData();
  }
  else
  {
    // Increase tally of time we spent waiting for buffer swap
    _waitTally += waitEnd-waitStart;
    _perfEnd = waitEnd;
  }
}

/*
 * @brief Fraction of time in waitForFrame() in percent of percent.
 * @return Number range from 0 to 10000. Higher values indicate more time
 * has been spent waiting for buffer swap, implying the rest of the code
 * ran faster and completed more quickly.
 */
uint32_t ESP_8_BIT_GFX::getWaitFraction()
{
  if (_perfEnd > _perfStart + 10000)
  {
    return _waitTally/((_perfEnd-_perfStart)/10000);
  }
  else
  {
    return 10000;
  }
}

/*
 * @brief Ends the current performance tracking session and start a new
 * one. Useful for isolating sections of code for measurement.
 * @note Sessions are still terminated whenever CPU clock counter
 * overflows (every ~18 seconds @ 240MHz) so some data may still be lost.
 * @return Number range from 0 to 10000. Higher values indicate more time
 * has been spent waiting for buffer swap, implying the rest of the code
 * ran faster and completed more quickly.
 */
uint32_t ESP_8_BIT_GFX::newPerformanceTrackingSession()
{
  return perfData();
}

/*
 * @brief Utility to convert from 16-bit RGB565 color to 8-bit RGB332 color
 */
uint8_t ESP_8_BIT_GFX::convertRGB565toRGB332(uint16_t color)
{
  // Extract most significant 3 red, 3 green and 2 blue bits.
  return (uint8_t)(
        (color & 0xE000) >> 8 |
        (color & 0x0700) >> 6 |
        (color & 0x0018) >> 3
      );
}

/*
 * @brief Retrieve color to use depending on _colorDepth
 */
uint8_t ESP_8_BIT_GFX::getColor8(uint16_t color)
{
  switch(_colorDepth)
  {
    case 8:
      // Use lower 8 bits directly
      return (uint8_t)color;
      break;
    case 16:
      // Downsample from 16 to 8-bit color.
      return convertRGB565toRGB332(color);
      break;
  }
}

/*
 * @brief Clamp X coordinate value within valid range
 */
int16_t ESP_8_BIT_GFX::clampX(int16_t inputX)
{
  if (inputX < 0) {
    ESP_LOGV(TAG, "Clamping X to 0");
    return 0;
  }

  if (inputX > MAX_X) {
    ESP_LOGV(TAG, "Clamping X to 255");
    return MAX_X;
  }

  return inputX;
}

/*
 * @brief Clamp Y coordinate value within valid range
 */
int16_t ESP_8_BIT_GFX::clampY(int16_t inputY)
{
  if (inputY < 0) {
    ESP_LOGV(TAG, "Clamping Y to 0");
    return 0;
  }

  if (inputY > MAX_Y) {
    ESP_LOGV(TAG, "Clamping Y to 239");
    return MAX_Y;
  }

  return inputY;
}

/*
 * @brief Required Adafruit_GFX override to put a pixel on screen
 */
void ESP_8_BIT_GFX::drawPixel(int16_t x, int16_t y, uint16_t color)
{
  // Account for screen rotation. Copied from Adafruit_GFX.cpp
  int16_t t;
  switch (rotation) {
  case 1:
    t = x;
    x = WIDTH - 1 - y;
    y = t;
    break;
  case 2:
    x = WIDTH - 1 - x;
    y = HEIGHT - 1 - y;
    break;
  case 3:
    t = x;
    x = y;
    y = HEIGHT - 1 - t;
    break;
  }

  if (x < 0 || x > MAX_X ||
      y < 0 || y > MAX_Y )
  {
    // This pixel is off screen, nothing to draw.
    return;
  }

  startWrite();
  _pVideo->getFrameBufferLines()[y][x] = getColor8(color);
  endWrite();
}

/**************************************************************************/
/*!
   @brief    Draw a perfectly vertical line, optimized for ESP_8_BIT
    @param    x   Top-most x coordinate
    @param    y   Top-most y coordinate
    @param    h   Height in pixels
   @param    color Color to fill with.
*/
/**************************************************************************/
void ESP_8_BIT_GFX::drawFastVLine(int16_t x, int16_t y, int16_t h, uint16_t color)
{
  // Call ESP_8_BIT optimized fillRect with width of one
  fillRect(x, y, 1, h, color);
}

/**************************************************************************/
/*!
   @brief    Draw a perfectly horizontal line, optimized for ESP_8_BIT
    @param    x   Left-most x coordinate
    @param    y   Left-most y coordinate
    @param    w   Width in pixels
   @param    color Color to fill with
*/
/**************************************************************************/

void ESP_8_BIT_GFX::drawFastHLine(int16_t x, int16_t y, int16_t w, uint16_t color)
{
  // Call ESP_8_BIT optimized fillRect with height of one
  fillRect(x, y, w, 1, color);
}

/**************************************************************************/
/*!
   @brief    Fill a rectangle completely with one color, optimized for ESP_8_BIT
    @param    x   Top left corner x coordinate
    @param    y   Top left corner y coordinate
    @param    w   Width in pixels
    @param    h   Height in pixels
   @param    color Color to fill with
*/
/**************************************************************************/
void ESP_8_BIT_GFX::fillRect(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t color)
{
  if (h < 1)
  {
    // Don't draw anything for zero or negative height
    return;
  }

  if (w < 1)
  {
    // Don't draw anything for zero or negative width
    return;
  }

  // Account for screen rotation. Copied from Adafruit_GFX.cpp then added width/height swap.
  int16_t t;
  switch (rotation) {
  case 1:
    t = x;
    x = WIDTH - 1 - y;
    y = t;
    // Swap width and height
    t = w;
    w = h;
    h = t;
    break;
  case 2:
    x = WIDTH - 1 - x;
    y = HEIGHT - 1 - y;
    break;
  case 3:
    t = x;
    x = y;
    y = HEIGHT - 1 - t;
    // Swap width and height
    t = w;
    w = h;
    h = t;
    break;
  }

  if (x+w < 0 || x > MAX_X)
  {
    // This rectangle is off screen left or right, nothing to draw.
    return;
  }

  if (y+h < 0 || y > MAX_Y )
  {
    // This rectangle is off screen top or bottom, nothing to draw.
    return;
  }

  int16_t clampedX = clampX(x);
  int16_t clampedXW = clampX(x+w-1);
  int16_t fillWidth = clampedXW-clampedX+1;

  int16_t clampedY = clampY(y);
  int16_t clampedYH = clampY(y+h-1)+1;

  uint8_t color8 = getColor8(color);
  uint8_t** lines = _pVideo->getFrameBufferLines();

  startWrite();
  for(int16_t vertical = clampedY; vertical < clampedYH; vertical++)
  {
    memset(&(lines[vertical][clampedX]), color8, fillWidth);
  }
  endWrite();
}

/**************************************************************************/
/*!
   @brief    Fill the screen completely with one color, optimized for ESP_8_BIT.
    @param    color Color to fill with
*/
/**************************************************************************/
void ESP_8_BIT_GFX::fillScreen(uint16_t color)
{
  uint8_t color8 = getColor8(color);
  uint8_t** lines = _pVideo->getFrameBufferLines();

  startWrite();
  // We can't do a single memset() because it is valid for _lines to point
  // into non-contingous pieces of memory. (Necessary when memory is
  // fragmented and we can't get a big enough chunk of contiguous bytes.)
  for(uint8_t y = 0; y <= MAX_Y; y++)
  {
    memset(lines[y], color8, 256);
  }
  endWrite();
}
