/*

ESP_8_BIT color composite video generator wrapper class.

Wrapper class adapting code extracted from Peter Barrett's ESP_8_BIT project
into a standalone Arduino library.

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

#ifndef ESP_8_BIT_COMPOSITE_H
#define ESP_8_BIT_COMPOSITE_H

#include "Arduino.h"

#ifndef ARDUINO_ARCH_ESP32
#error This library requires ESP32 as it uses ESP32-specific hardware peripheral
#endif

#include "esp_types.h"
#include "esp_err.h"
#include "esp_log.h"

#include "esp_attr.h"
#include "esp_heap_caps.h"
#include "esp_intr_alloc.h"
#include "driver/periph_ctrl.h"
#include "driver/dac.h"
#include "driver/gpio.h"
#include "driver/i2s.h"
#include "rom/gpio.h"
#include "rom/lldesc.h"
#include "soc/gpio_reg.h"
#include "soc/i2s_struct.h"
#include "soc/i2s_reg.h"
#include "soc/io_mux_reg.h"
#include "soc/rtc.h"
#include "soc/rtc_io_reg.h"
#include "soc/soc.h"

class ESP_8_BIT_composite
{
  public:
    /*
     * @brief Constructor for ESP_8_BIT composite video wrapper class
     * @param ntsc True (or nonzero) for NTSC mode, False (or zero) for PAL mode
     */
    ESP_8_BIT_composite(int ntsc);

    /*
     * @brief Destructor for ESP_8_BIT composite video wrapper class. This
     * is only useful for freeing self-allocated memory, because I don't know how
     * to properly tear down rossumur's ESP_8_BIT magic I wrapped.
     */
    ~ESP_8_BIT_composite();

    /*
     * @brief Video subsystem setup: allocate frame buffer and start engine
     */
    void begin();

    /*
     * @brief Wait for current frame to finish rendering
     */
    void waitForFrame();

    /*
     * @brief Retrieve pointer to frame buffer lines array
     */
    uint8_t** getFrameBufferLines();

    /*
     * @brief Number of frames sent to screen
     */
    uint32_t getRenderedFrameCount();

    /*
     * @brief Number of buffer swaps performed
     */
    uint32_t getBufferSwapCount();
  private:
    /*
     * @brief Check to ensure this instance is the first and only allowed instance
     */
    void instance_check();

    /*
     * @brief Flag to ensure begin() is called once and only once
     */
    bool _started;

    /*
     * @brief Allocate memory for frame buffer
     */
    uint8_t** frameBufferAlloc();

    /*
     * @brief Free memory allocated by frameBufferAlloc();
     */
    void frameBufferFree(uint8_t** frameBuffer);
};

#endif // ESP_8_BIT_COMPOSITE_H
