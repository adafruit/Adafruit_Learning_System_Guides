// SPDX-FileCopyrightText: 2022 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <AnimatedGIF.h>
#include <SdFat.h>
#include <Adafruit_SPIFlash.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h> // Hardware-specific library for ST7735
#include <Adafruit_ST7789.h> // Hardware-specific library for ST7789

#define TFT_CS         5
#define TFT_DC         6
#define TFT_RST        9

#define DISPLAY_WIDTH 320
#define DISPLAY_HEIGHT 174

#define GIFDIRNAME "/"
#define NUM_LOOPS 5

#if defined(ARDUINO_ARCH_ESP32)
  // ESP32 use same flash device that store code.
  // Therefore there is no need to specify the SPI and SS
  Adafruit_FlashTransport_ESP32 flashTransport;

#elif defined(ARDUINO_ARCH_RP2040)
  // RP2040 use same flash device that store code for file system. Therefore we
  // only need to specify start address and size (no need SPI or SS)
  // By default (start=0, size=0), values that match file system setting in
  // 'Tools->Flash Size' menu selection will be used.
  // Adafruit_FlashTransport_RP2040 flashTransport;

  // To be compatible with CircuitPython partition scheme (start_address = 1 MB,
  // size = total flash - 1 MB) use const value (CPY_START_ADDR, CPY_SIZE) or
  // subclass Adafruit_FlashTransport_RP2040_CPY. Un-comment either of the
  // following line:
  //  Adafruit_FlashTransport_RP2040
  //    flashTransport(Adafruit_FlashTransport_RP2040::CPY_START_ADDR,
  //                   Adafruit_FlashTransport_RP2040::CPY_SIZE);
  Adafruit_FlashTransport_RP2040_CPY flashTransport;

#else
  // On-board external flash (QSPI or SPI) macros should already
  // defined in your board variant if supported
  // - EXTERNAL_FLASH_USE_QSPI
  // - EXTERNAL_FLASH_USE_CS/EXTERNAL_FLASH_USE_SPI
  #if defined(EXTERNAL_FLASH_USE_QSPI)
    Adafruit_FlashTransport_QSPI flashTransport;

  #elif defined(EXTERNAL_FLASH_USE_SPI)
    Adafruit_FlashTransport_SPI flashTransport(EXTERNAL_FLASH_USE_CS, EXTERNAL_FLASH_USE_SPI);

  #else
    #error No QSPI/SPI flash are defined on your board variant.h !
  #endif
#endif

Adafruit_SPIFlash flash(&flashTransport);

// file system object from SdFat
FatFileSystem fatfs;

Adafruit_ST7789 tft = Adafruit_ST7789(TFT_CS, TFT_DC, TFT_RST);
AnimatedGIF gif;
File32 f, root;

void * GIFOpenFile(const char *fname, int32_t *pSize)
{
  f = fatfs.open(fname);
  if (f)
  {
    *pSize = f.size();
    return (void *)&f;
  }
  return NULL;
} /* GIFOpenFile() */

void GIFCloseFile(void *pHandle)
{
  File32 *f = static_cast<File32 *>(pHandle);
  if (f != NULL)
     f->close();
} /* GIFCloseFile() */

int32_t GIFReadFile(GIFFILE *pFile, uint8_t *pBuf, int32_t iLen)
{
    int32_t iBytesRead;
    iBytesRead = iLen;
    File32 *f = static_cast<File32 *>(pFile->fHandle);
    // Note: If you read a file all the way to the last byte, seek() stops working
    if ((pFile->iSize - pFile->iPos) < iLen)
       iBytesRead = pFile->iSize - pFile->iPos - 1; // <-- ugly work-around
    if (iBytesRead <= 0)
       return 0;
    iBytesRead = (int32_t)f->read(pBuf, iBytesRead);
    pFile->iPos = f->position();
    return iBytesRead;
} /* GIFReadFile() */

int32_t GIFSeekFile(GIFFILE *pFile, int32_t iPosition)
{ 
  int i = micros();
  File32 *f = static_cast<File32 *>(pFile->fHandle);
  f->seek(iPosition);
  pFile->iPos = (int32_t)f->position();
  i = micros() - i;
//  Serial.printf("Seek time = %d us\n", i);
  return pFile->iPos;
} /* GIFSeekFile() */

// Draw a line of image directly on the LCD
void GIFDraw(GIFDRAW *pDraw)
{
    uint8_t *s;
    uint16_t *d, *usPalette, usTemp[320];
    int x, y, iWidth;

    iWidth = pDraw->iWidth;
    // Serial.printf("Drawing %d pixels\n", iWidth);

    if (iWidth + pDraw->iX > DISPLAY_WIDTH)
       iWidth = DISPLAY_WIDTH - pDraw->iX;
    usPalette = pDraw->pPalette;
    y = pDraw->iY + pDraw->y; // current line
    if (y >= DISPLAY_HEIGHT || pDraw->iX >= DISPLAY_WIDTH || iWidth < 1)
       return; 
    s = pDraw->pPixels;
    if (pDraw->ucDisposalMethod == 2) // restore to background color
    {
      for (x=0; x<iWidth; x++)
      {
        if (s[x] == pDraw->ucTransparent)
           s[x] = pDraw->ucBackground;
      }
      pDraw->ucHasTransparency = 0;
    }

    // Apply the new pixels to the main image
    if (pDraw->ucHasTransparency) // if transparency used
    {
      uint8_t *pEnd, c, ucTransparent = pDraw->ucTransparent;
      int x, iCount;
      pEnd = s + iWidth;
      x = 0;
      iCount = 0; // count non-transparent pixels
      while(x < iWidth)
      {
        c = ucTransparent-1;
        d = usTemp;
        while (c != ucTransparent && s < pEnd)
        {
          c = *s++;
          if (c == ucTransparent) // done, stop
          {
            s--; // back up to treat it like transparent
          }
          else // opaque
          {
             *d++ = usPalette[c];
             iCount++;
          }
        } // while looking for opaque pixels
        if (iCount) // any opaque pixels?
        {
          tft.startWrite();
          tft.setAddrWindow(pDraw->iX+x, y, iCount, 1);
          tft.writePixels(usTemp, iCount, false, false);
          tft.endWrite();
          x += iCount;
          iCount = 0;
        }
        // no, look for a run of transparent pixels
        c = ucTransparent;
        while (c == ucTransparent && s < pEnd)
        {
          c = *s++;
          if (c == ucTransparent)
             iCount++;
          else
             s--; 
        }
        if (iCount)
        {
          x += iCount; // skip these
          iCount = 0;
        }
      }
    }
    else
    {
      s = pDraw->pPixels;
      // Translate the 8-bit pixels through the RGB565 palette (already byte reversed)
      for (x=0; x<iWidth; x++)
        usTemp[x] = usPalette[*s++];
      tft.startWrite();
      tft.setAddrWindow(pDraw->iX, y, iWidth, 1);
      tft.writePixels(usTemp, iWidth, false, false);
      tft.endWrite();
    }
} /* GIFDraw() */


void setup() {
  Serial.begin(115200);
  while (!Serial);

  Serial.println("Adafruit SPIFlash Animated GIF Example");

  // Initialize flash library and check its chip ID.
  if (!flash.begin()) {
    Serial.println("Error, failed to initialize flash chip!");
    while(1);
  }
  Serial.print("Flash chip JEDEC ID: 0x"); Serial.println(flash.getJEDECID(), HEX);

  // First call begin to mount the filesystem.  Check that it returns true
  // to make sure the filesystem was mounted.
  if (!fatfs.begin(&flash)) {
    Serial.println("Failed to mount filesystem!");
    Serial.println("Was CircuitPython loaded on the board first to create the filesystem?");
    while(1);
  }
  Serial.println("Mounted filesystem!");

  if (!root.open(GIFDIRNAME)) {
    Serial.println("Open dir failed");
  }
  while (f.openNext(&root, O_RDONLY)) {
    f.printFileSize(&Serial);
    Serial.write(' ');
    f.printModifyDateTime(&Serial);
    Serial.write(' ');
    f.printName(&Serial);
    if (f.isDir()) {
      // Indicate a directory.
      Serial.write('/');
    }
    Serial.println();
    f.close();
  }
  root.close();
  
  tft.init(DISPLAY_HEIGHT, DISPLAY_WIDTH);
  tft.fillScreen(ST77XX_BLUE);
  tft.setRotation(1);
  gif.begin(LITTLE_ENDIAN_PIXELS);
}

void loop() {
  char thefilename[80];
  
  if (!root.open(GIFDIRNAME)) {
    Serial.println("Open GIF directory failed");
    while (1);
  }
  while (f.openNext(&root, O_RDONLY)) {
    f.printFileSize(&Serial);
    Serial.write(' ');
    f.printModifyDateTime(&Serial);
    Serial.write(' ');
    f.printName(&Serial);
    if (f.isDir()) {
      // Indicate a directory.
      Serial.write('/');
    }
    Serial.println();
    f.getName(thefilename, sizeof(thefilename)-1);
    f.close();
    if (strstr(thefilename, ".gif") || strstr(thefilename, ".GIF")) {
      // found a gif mebe!
      if (gif.open(thefilename, GIFOpenFile, GIFCloseFile, GIFReadFile, GIFSeekFile, GIFDraw)) {
        GIFINFO gi;
        Serial.printf("Successfully opened GIF %s; Canvas size = %d x %d\n",  thefilename, gif.getCanvasWidth(), gif.getCanvasHeight());
        if (gif.getInfo(&gi)) {
          Serial.printf("frame count: %d\n", gi.iFrameCount);
          Serial.printf("duration: %d ms\n", gi.iDuration);
          Serial.printf("max delay: %d ms\n", gi.iMaxDelay);
          Serial.printf("min delay: %d ms\n", gi.iMinDelay);
        }
        // play thru n times
        for (int loops=0; loops<NUM_LOOPS; loops++) {
          while (gif.playFrame(true, NULL));
          gif.reset();
        }
        gif.close();
      } else {
        Serial.printf("Error opening file %s = %d\n", thefilename, gif.getLastError());
      }
    }
  }
  root.close();
}
