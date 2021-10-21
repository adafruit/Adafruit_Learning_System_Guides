// SPDX-FileCopyrightText: 2018 Arduino SA 
//
// SPDX-License-Identifier: GPL-2.1-or-later
/*
  RP2040-SerialESPPassthrough - Used for flashing ESP32 module
  with the Raspberry Pi RP2040.
  Copyright (c) 2018 Arduino SA. All rights reserved.
  This library is free software; you can redistribute it and/or
  modify it under the terms of the GNU Lesser General Public
  License as published by the Free Software Foundation; either
  version 2.1 of the License, or (at your option) any later version.
  This library is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
  Lesser General Public License for more details.
  You should have received a copy of the GNU Lesser General Public
  License along with this library; if not, write to the Free Software
  Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
*/
#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/uart.h"

// Define which Raspberry Pi RP2040 board you're using below:
// Raspberry Pi Pico RP2040
#define RP2040_PICO
// Adafruit Feather RP2040
//#define RP2040_FEATHER

#define BAUD_RATE 115200
#define UART_ESP32 uart0
#define UART_ESP32_TX_PIN 0
#define UART_ESP32_RX_PIN 1

#if defined RP2040_PICO
    #define ESP32_CS    13 // Chip select pin
    #define ESP32_RST   16 // Reset pin
    #define ESP32_GPIO0  9 // GPIO0 pin
#elif defined RP2040_FEATHER
    #define ESP32_CS    13 // Chip select pin
    #define ESP32_RST   12 // Reset pin
    #define ESP32_GPIO0 10 // GPIO0 pin
#endif

int main() {
    // init stdio_usb
    stdio_usb_init();
    stdio_set_translate_crlf(&stdio_usb, false);

    // init UART0
    uart_init(UART_ESP32, BAUD_RATE);
    gpio_set_function(UART_ESP32_TX_PIN, GPIO_FUNC_UART);
    gpio_set_function(UART_ESP32_RX_PIN, GPIO_FUNC_UART);
    sleep_ms(100);

    // init ESP32 module
    gpio_init(ESP32_CS);
    gpio_set_dir(ESP32_CS, GPIO_OUT);
    gpio_init(ESP32_RST);
    gpio_set_dir(ESP32_RST, GPIO_OUT);
    gpio_init(ESP32_GPIO0);
    gpio_set_dir(ESP32_GPIO0, GPIO_OUT);

    // manually put the ESP32 in upload mode
    gpio_put(ESP32_GPIO0, 0);
    gpio_put(ESP32_RST, 0);
    sleep_ms(100);

    gpio_put(ESP32_RST, 1);
    sleep_ms(100);

    while (true) {

        // read from USB
        int c = getchar_timeout_us(0);
        if (c != PICO_ERROR_TIMEOUT) {
            // write to UART
            uart_putc(UART_ESP32, c);
        }

        // check if data is in UART RX buffer
        if (uart_is_readable(UART_ESP32)) {
            // read from UART
            char ch = uart_getc(UART_ESP32);
            // write to USB
            printf("%c", ch);
        }
    }

    return 0;
}