// SPDX-FileCopyrightText: 2023 Mockba the Borg
// SPDX-FileCopyrightText: 2023 Jeff Epler for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <SdFat.h> // SDFat - Adafruit Fork
#include <PicoDVI.h>
#include "../../console.h"
#include "../../arduino_hooks.h"

#ifndef USE_DISPLAY
#define USE_DISPLAY (1)
#endif

#ifndef USE_MSC
#define USE_MSC (0)
#endif

#if USE_DISPLAY
DVItext1 display(DVI_RES_800x240p30, adafruit_feather_dvi_cfg);
#endif
#define SPI_CLOCK (20'000'000)
#define SD_CS_PIN (10)
#define SD_CONFIG SdSpiConfig(SD_CS_PIN, DEDICATED_SPI, SPI_CLOCK)
DedicatedSpiCard blockdevice;
FatFileSystem SD;     // Filesystem object from SdFat

// =========================================================================================
// Define Board-Data
// GP25 green onboard LED
// =========================================================================================
#define LED (13)
#define LEDinv (false)
#define board_pico
#define board_analog_io
#define board_digital_io

// FUNCTIONS REQUIRED FOR USB MASS STORAGE ---------------------------------

#if USE_MSC
Adafruit_USBD_MSC usb_msc; // USB mass storage object
static bool msc_changed = true; // Is set true on filesystem changes

// Callback on READ10 command.
int32_t msc_read_cb(uint32_t lba, void *buffer, uint32_t bufsize) {
  return blockdevice.readBlocks(lba, (uint8_t *)buffer, bufsize / 512) ? bufsize : -1;
}

// Callback on WRITE10 command.
int32_t msc_write_cb(uint32_t lba, uint8_t *buffer, uint32_t bufsize) {
  digitalWrite(LED_BUILTIN, HIGH);
  return blockdevice.writeBlocks(lba, buffer, bufsize / 512) ? bufsize : -1;
}

// Callback on WRITE10 completion.
void msc_flush_cb(void) {
  blockdevice.syncBlocks();   // Sync with blockdevice
  SD.cacheClear(); // Clear filesystem cache to force refresh
  digitalWrite(LED_BUILTIN, LOW);
  msc_changed = true;
}
#endif

#if USE_DISPLAY
uint16_t underCursor = ' ';

void putch_display(uint8_t ch) {
    auto x = display.getCursorX();
    auto y = display.getCursorY();
    display.drawPixel(x, y, underCursor);
    if(ch == 8) {
        if(x > 0) {
            display.setCursor(--x, y);
            display.drawPixel(x, y, ' ');
        }
    } else {
        display.write(ch);
    }
    x = display.getCursorX();
    y = display.getCursorY();
    underCursor = display.getPixel(x, y);
    display.drawPixel(x, y, 0xDB);
}
#endif

uint8_t getch_serial1(void) {
    while(true) {
        int r = Serial1.read();
        if(r != -1) {
            return r;
        }
    }
}

bool kbhit_serial1(void) {
    return Serial1.available();
}

bool port_init_early() {
#if USE_DISPLAY
  // vreg_set_voltage(VREG_VOLTAGE_1_30);
  if (!display.begin()) { return false; }
  _putch_hook = putch_display;
#endif
  _getch_hook = getch_serial1;
  _kbhit_hook = kbhit_serial1;
  // USB mass storage / filesystem setup (do BEFORE Serial init)
  if (!blockdevice.begin(SD_CONFIG)) { _puts("Failed to initialize SD card"); return false; }
#if USE_MSC
  // Set disk vendor id, product id and revision
  usb_msc.setID("Adafruit", "Internal Flash", "1.0");
  // Set disk size, block size is 512 regardless of blockdevice page size
  usb_msc.setCapacity(blockdevice.sectorCount(), 512);
  usb_msc.setReadWriteCallback(msc_read_cb, msc_write_cb, msc_flush_cb);
  usb_msc.setUnitReady(true); // MSC is ready for read/write
  if (!usb_msc.begin()) {
      _puts("Failed to initialize USB MSC"); return false;
  }
#endif
  return true;
}

bool port_flash_begin() {
  if (!SD.begin(&blockdevice, true, 1)) { // Start filesystem on the blockdevice
      _puts("!SD.begin()"); return false;
  }
  return true;
}

