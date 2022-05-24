/*

Adafruit_GFX for ESP_8_BIT color composite video.

NOT AN OFFICIAL ADAFRUIT GRAPHICS LIBRARY.

Allows ESP32 Arduino sketches to draw to a composite video device using
Adafruit's graphics API.

NOTE RE:COLOR

Adafruit GFX is designed for 16-bit (RGB565) color, but ESP_8_BIT video
only handles 8-bit (RGB332) color. There are two ways to handle this,
depending on passsing "8" or "16" into the constructor:

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

#ifndef ESP_8_BIT_GFX_H
#define ESP_8_BIT_GFX_H

#include "Arduino.h"
#include "Adafruit_GFX.h"
#include "ESP_8_BIT_composite.h"

/*
 * @brief Expose Adafruit GFX API for ESP_8_BIT composite video generator
 */
class ESP_8_BIT_GFX : public Adafruit_GFX {
  public:
    /*
     * @brief Constructor
     * @param ntsc true for NTSC, false for PAL
     * @param colorDepth 8 to treat color as 8-bit directly, 16 to perform
     *        downconversion from 16-bit RGB565 color to 8-bit RGB332.
     */
    ESP_8_BIT_GFX(bool ntsc, uint8_t colorDepth);

    /*
     * @brief Call once to set up the API with self-allocated frame buffer.
     */
    void begin();

    /*
     * @brief Wait for swap of front and back buffer. Gathers performance
     * metrics while waiting.
     */
    void waitForFrame();

    /*
     * @brief Fraction of time in waitForFrame() in percent of percent.
     * @return Number range from 0 to 10000. Higher values indicate more time
     * has been spent waiting for buffer swap, implying the rest of the code
     * ran faster and completed more quickly.
     */
    uint32_t getWaitFraction();

    /*
     * @brief Ends the current performance tracking session and start a new
     * one. Useful for isolating sections of code for measurement.
     * @note Sessions are still terminated whenever CPU clock counter
     * overflows (every ~18 seconds @ 240MHz) so some data may still be lost.
     * @return Number range from 0 to 10000. Higher values indicate more time
     * has been spent waiting for buffer swap, implying the rest of the code
     * ran faster and completed more quickly.
     */
    uint32_t newPerformanceTrackingSession();

    /*
     * @brief Utility to convert from 16-bit RGB565 color to 8-bit RGB332 color
     */
    uint8_t convertRGB565toRGB332(uint16_t color);

    /*
     * @brief Required Adafruit_GFX override to put a pixel on screen
     */
    void drawPixel(int16_t x, int16_t y, uint16_t color) override;

    /*
     * @brief Optional Adafruit_GFX overrides for performance
     */
    void drawFastVLine(int16_t x, int16_t y, int16_t h, uint16_t color) override;
    void drawFastHLine(int16_t x, int16_t y, int16_t w, uint16_t color) override;
    void fillRect(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t color) override;
    void fillScreen(uint16_t color) override;

    /*
     * @brief Set this to true if the frame buffer should be copied upon every
     * swap of the front/back buffer. Defaults to false.
     * @note Some graphics libraries act on delta from previous frame, so the
     * front and buffers need to be in sync to avoid visual artifacts.
     */
    bool copyAfterSwap;
  private:
    /*
     * @brief Given input X-coordinate, return value clamped within valid range.
     */
    int16_t clampX(int16_t inputX);

    /*
     * @brief Given input Y-coordinate, return value clamped within valid range.
     */
    int16_t clampY(int16_t inputY);

    /*
     * @brief Whether to treat color as 8 or 16 bit color values
     */
    uint8_t _colorDepth;

    /*
     * @brief Internal reference to ESP_8_BIT video generator wrapper class
     */
    ESP_8_BIT_composite* _pVideo;

    /*
     * @brief Retrieve color to use depending on _colorDepth
     */
    uint8_t getColor8(uint16_t color);


    /////////////////////////////////////////////////////////////////////////
    //
    //  Performance metric data
    //
    //  The Tensilica core in an ESP32 keeps a count of clock cycles read via
    //  xthal_get_ccount(). This is only a 32-bit unsigned value. So when the
    //  core is running at 240MHz we have just under 18 seconds before this
    //  value overflows.
    //
    //  Rather than trying to make error-prone and expensive calculations to
    //  account for clock count overflows, this performance tracking is
    //  divided up into sessions. Every ~18 seconds the clock count overflow,
    //  we start a new session. Performance data of gaps between sessions
    //  are lost.
    //
    //  Each sessions retrieves from the underlying rendering class two pieces
    //  of data: the number of frames rendered to screen and the number of
    //  buffer swaps performed. These are uint32_t. When they overflow, the
    //  frame count related statistics will be nonsensical for that session.
    //  The values should make sense again for the following session.
    //
    //  Performance data is only gathered during waitForFrame(), which assumes
    //  the application is calling waitForFrame() at high rate so we can
    //  sample performance data. Applications that do not call waitForFrame()
    //  frequently may experience large session gaps of lost data. If
    //  waitForFrame() is not called for more than 18 seconds, the data will
    //  be nonsensical. Fortunately applications that do not make frequent
    //  frame updates are probably not concerned with performance data anyway.
    //
    //  Clock cycle count is a value kept by a core. They are not synchronized
    //  across multiple ESP32 cores. Trying to calculate from cycle counts
    //  from different cores will result in nonsensical data. This is usually
    //  not a problem as the typical usage has Arduino runtime pinned to a
    //  single core.
    //
    //  These metrics track the number of clocks we spend waiting, but that
    //  includes both idle clock cycles and clock cycles consumed by other
    //  code. Including our underlying rendering class! The percentage is
    //  valid for relative comparisons. "Algorithm A leaves lower percentage
    //  waiting than B, so B is faster" is a valid conclusion. However
    //  inferring from absolute numbers are not valid. For example "We wait
    //  50% of the time so we have enough power for twice the work" would be
    //  wrong. Some of that 50% wait time is used by other code and not free
    //  for use.
    //
    //  The tradeoff for the limitations above is that we have a very
    //  lightweight performance tracker that imposes minimal overhead. But
    //  take care interpreting its numbers!

    /*
     * @brief Number of clock counts spent waiting for frame buffer swap.
     */
    uint32_t _waitTally;

    /*
     * @brief Clock count value at the start of a session.
     */
    uint32_t _perfStart;

    /*
     * @brief Clock count value at the end of a session.
     */
    uint32_t _perfEnd;

    /*
     * @brief Number of frames rendered at the start of a session
     */
    uint32_t _frameStart;

    /*
     * @brief Number of buffer swaps performed at the start of a session
     */
    uint32_t _swapStart;

    /*
     * @brief Calculate performance metrics, output as INFO log.
     * @return Number range from 0 to 10000. Higher values indicate more time
     * has been spent waiting for buffer swap, implying the rest of the code
     * ran faster and completed more quickly.
     */
    uint32_t perfData();
};

#endif // #ifndef ESP_8_BIT_GFX_H
