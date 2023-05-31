// SPDX-FileCopyrightText: 2023 Mockba the Borg
//
// SPDX-License-Identifier: MIT

// only AVR and ARM CPU
// #include <MemoryFree.h>

#include "globals.h"

// =========================================================================================
// Guido Lehwalder's Code-Revision-Number
// =========================================================================================
#define GL_REV "GL20230303.0"

#include <SPI.h>

#include <SdFat.h>        // One SD library to rule them all - Greinman SdFat from Library Manager
#include <Adafruit_SPIFlash.h>
#include <Adafruit_TinyUSB.h>

#define TEXT_BOLD "\033[1m"
#define TEXT_NORMAL "\033[0m"

// =========================================================================================
// Board definitions go into the "hardware" folder, if you use a board different than the
// Arduino DUE, choose/change a file from there and reference that file here
// =========================================================================================

// Raspberry Pi Pico - normal (LED = GPIO25)
#include "hardware/pico/feather_dvi.h"

#ifndef BOARD_TEXT
#define BOARD_TEXT USB_MANUFACTURER " " USB_PRODUCT
#endif

#include "abstraction_arduino.h"
// Raspberry Pi Pico W(iFi)   (LED = GPIO32)
// #include "hardware/pico/pico_w_sd_spi.h"

// =========================================================================================
// Delays for LED blinking
// =========================================================================================
#define sDELAY 100
#define DELAY 1200


// =========================================================================================
// Serial port speed
// =========================================================================================
#define SERIALSPD 115200

// =========================================================================================
// PUN: device configuration
// =========================================================================================
#ifdef USE_PUN
File32 pun_dev;
int pun_open = FALSE;
#endif

// =========================================================================================
// LST: device configuration
// =========================================================================================
#ifdef USE_LST
File32 lst_dev;
int lst_open = FALSE;
#endif

#include "ram.h"
#include "console.h"
#include "cpu.h"
#include "disk.h"
#include "host.h"
#include "cpm.h"
#ifdef CCP_INTERNAL
#include "ccp.h"
#endif

void setup(void) {
  pinMode(LED, OUTPUT);
  digitalWrite(LED, LOW^LEDinv);


// =========================================================================================
// Serial Port Definition
// =========================================================================================
//   Serial =USB / Serial1 =UART0/COM1 / Serial2 =UART1/COM2

   Serial1.setRX(1); // Pin 2
   Serial1.setTX(0); // Pin 1
   Serial1.begin(SERIALSPD);

   Serial2.setRX(5); // Pin 7
   Serial2.setTX(4); // Pin 6
   Serial2.begin(SERIALSPD);

// or

//   Serial1.setRX(17); // Pin 22
//   Serial1.setTX(16); // Pin 21

//   Serial2.setRX(21); // Pin 27
//   Serial2.setTX(20); // Pin 26
// =========================================================================================

  if (!port_init_early()) { return; }

#if defined(WAIT_SERIAL)
  // _clrscr();
  // _puts("Opening serial-port...\r\n");  
  Serial.begin(SERIALSPD);
  while (!Serial) {	// Wait until serial is connected
    digitalWrite(LED, HIGH^LEDinv);
    delay(sDELAY);
    digitalWrite(LED, LOW^LEDinv);
    delay(DELAY);
  }
#endif

#ifdef DEBUGLOG
  _sys_deletefile((uint8 *)LogName);
#endif

  
// =========================================================================================  
// Printing the Startup-Messages
// =========================================================================================

  _clrscr();

  // if (bootup_press == 1)
  //   { _puts("Recognized " TEXT_BOLD "#" TEXT_NORMAL " key as pressed! :)\r\n\r\n");
  //   }
  
  _puts("CP/M Emulator " TEXT_BOLD "v" VERSION "" TEXT_NORMAL "   by   " TEXT_BOLD "Marcelo  Dantas\e[0m\r\n");
  _puts("----------------------------------------------\r\n");  
  _puts("    running on [" TEXT_BOLD BOARD_TEXT TEXT_NORMAL "]\r\n");
  _puts("----------------------------------------------\r\n");

	_puts("BIOS              at [" TEXT_BOLD "0x");
	_puthex16(BIOSjmppage);
//	_puts(" - ");
	_puts("" TEXT_NORMAL "]\r\n");

	_puts("BDOS              at [" TEXT_BOLD "0x");
	_puthex16(BDOSjmppage);
	_puts("" TEXT_NORMAL "]\r\n");

	_puts("CCP " CCPname " at [" TEXT_BOLD "0x");
	_puthex16(CCPaddr);
	_puts("" TEXT_NORMAL "]\r\n");

  #if BANKS > 1
	_puts("Banked Memory        [" TEXT_BOLD "");
	_puthex8(BANKS);
    _puts("" TEXT_NORMAL "]banks\r\n");
  #endif

   // Serial.printf("Free Memory          [" TEXT_BOLD "%d bytes" TEXT_NORMAL "]\r\n", freeMemory());

  _puts("CPU-Clock            [" TEXT_BOLD);
  _putdec((clock_get_hz( clk_sys ) + 500'000) / 1'000'000);
  _puts(TEXT_NORMAL "] MHz\r\n");

  _puts("Init Storage         [ " TEXT_BOLD "");
  if (port_flash_begin()) {
    _puts("OK " TEXT_NORMAL "]\r\n");
    _puts("----------------------------------------------");

    if (VersionCCP >= 0x10 || SD.exists(CCPname)) {
      while (true) {
        _puts(CCPHEAD);
        _PatchCPM();
	Status = 0;
#ifndef CCP_INTERNAL
        if (!_RamLoad((char *)CCPname, CCPaddr)) {
          _puts("Unable to load the CCP.\r\nCPU halted.\r\n");
          break;
        }
        Z80reset();
        SET_LOW_REGISTER(BC, _RamRead(DSKByte));
        PC = CCPaddr;
        Z80run();
#else
        _ccp();
#endif
        if (Status == 1)
          break;
#ifdef USE_PUN
        if (pun_dev)
          _sys_fflush(pun_dev);
#endif
#ifdef USE_LST
        if (lst_dev)
          _sys_fflush(lst_dev);
#endif
      }
    } else {
      _puts("Unable to load CP/M CCP.\r\nCPU halted.\r\n");
    }
  } else {
    _puts("ERR " TEXT_NORMAL "]\r\nUnable to initialize SD card.\r\nCPU halted.\r\n");
  }
}

// if loop is reached, blink LED forever to signal error
void loop(void) {
  digitalWrite(LED, HIGH^LEDinv);
  delay(DELAY);
  digitalWrite(LED, LOW^LEDinv);
  delay(DELAY);
  digitalWrite(LED, HIGH^LEDinv);
  delay(DELAY);
  digitalWrite(LED, LOW^LEDinv);
  delay(DELAY * 4);
}
