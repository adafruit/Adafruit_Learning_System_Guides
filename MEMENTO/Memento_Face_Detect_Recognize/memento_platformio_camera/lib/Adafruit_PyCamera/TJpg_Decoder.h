// SPDX-FileCopyrightText: ChaN, Bodmer
//
// SPDX-License-Identifier: BSD-2-Clause
/*
TJpg_Decoder.h

JPEG Decoder for Arduino using TJpgDec:
http://elm-chan.org/fsw/tjpgd/00index.html

Incorporated into an Arduino library by Bodmer 18/10/19

Latest version here:
https://github.com/Bodmer/TJpg_Decoder
*/

#ifndef TJpg_Decoder_H
#define TJpg_Decoder_H

#include "Arduino.h"
#include "User_Config.h"
#include "tjpgd.h"

#if defined(TJPGD_LOAD_SD_LIBRARY)
#include <SD.h>
#endif

enum { TJPG_ARRAY = 0, TJPG_FS_FILE, TJPG_SD_FILE };

//------------------------------------------------------------------------------

typedef bool (*SketchCallback)(int16_t x, int16_t y, uint16_t w, uint16_t h,
                               uint16_t *data);

/**************************************************************************/
/**
 * @class TJpg_Decoder
 * @brief JPEG Decoder for Arduino using TJpgDec.
 *
 * Incorporates the TJpgDec library into an Arduino library for JPEG decoding.
 * Supports loading JPEG files from various sources like SD card, SPIFFS, and
 * memory arrays.
 */
/**************************************************************************/
class TJpg_Decoder {

private:
#if defined(TJPGD_LOAD_SD_LIBRARY)
  File jpgSdFile; ///< File handle for JPEG files on SD card.
#endif

#ifdef TJPGD_LOAD_FFS
  fs::File jpgFile; ///< File handle for JPEG files in SPIFFS.
#endif

public:
  TJpg_Decoder();  ///< Constructor for TJpg_Decoder.
  ~TJpg_Decoder(); ///< Destructor for TJpg_Decoder.

  static int
  jd_output(JDEC *jdec, void *bitmap,
            JRECT *jrect); ///< Static callback for outputting JPEG blocks.
  static unsigned int
  jd_input(JDEC *jdec, uint8_t *buf,
           unsigned int len); ///< Static callback for inputting JPEG data.

  void setJpgScale(uint8_t scale); ///< Set the JPEG scaling factor.
  void
  setCallback(SketchCallback sketchCallback); ///< Set the callback function for
                                              ///< rendering decoded blocks.

#if defined(TJPGD_LOAD_SD_LIBRARY) || defined(TJPGD_LOAD_FFS)
  JRESULT drawJpg(int32_t x, int32_t y, const char *pFilename);
  JRESULT drawJpg(int32_t x, int32_t y, const String &pFilename);

  JRESULT getJpgSize(uint16_t *w, uint16_t *h, const char *pFilename);
  JRESULT getJpgSize(uint16_t *w, uint16_t *h, const String &pFilename);
#endif

#if defined(TJPGD_LOAD_SD_LIBRARY)
  JRESULT drawSdJpg(int32_t x, int32_t y, const char *pFilename);
  JRESULT drawSdJpg(int32_t x, int32_t y, const String &pFilename);
  JRESULT drawSdJpg(int32_t x, int32_t y, File inFile);

  JRESULT getSdJpgSize(uint16_t *w, uint16_t *h, const char *pFilename);
  JRESULT getSdJpgSize(uint16_t *w, uint16_t *h, const String &pFilename);
  JRESULT getSdJpgSize(uint16_t *w, uint16_t *h, File inFile);
#endif

#ifdef TJPGD_LOAD_FFS
  JRESULT drawFsJpg(int32_t x, int32_t y, const char *pFilename,
                    fs::FS &fs = SPIFFS);
  JRESULT drawFsJpg(int32_t x, int32_t y, const String &pFilename,
                    fs::FS &fs = SPIFFS);
  JRESULT drawFsJpg(int32_t x, int32_t y, fs::File inFile);

  JRESULT getFsJpgSize(uint16_t *w, uint16_t *h, const char *pFilename,
                       fs::FS &fs = SPIFFS);
  JRESULT getFsJpgSize(uint16_t *w, uint16_t *h, const String &pFilename,
                       fs::FS &fs = SPIFFS);
  JRESULT getFsJpgSize(uint16_t *w, uint16_t *h, fs::File inFile);
#endif

  JRESULT drawJpg(int32_t x, int32_t y, const uint8_t array[],
                  uint32_t array_size);
  JRESULT getJpgSize(uint16_t *w, uint16_t *h, const uint8_t array[],
                     uint32_t array_size);

  void setSwapBytes(bool swap);

  bool _swap = false; ///< Swap byte order flag.

  const uint8_t *array_data =
      nullptr;              ///< Pointer to JPEG data in memory array.
  uint32_t array_index = 0; ///< Current index in the memory array.
  uint32_t array_size = 0;  ///< Size of the memory array.

  /*! \cond DOXYGEN_SHOULD_SKIP_THIS */
  uint8_t workspace[TJPGD_WORKSPACE_SIZE] __attribute__((
      aligned(4))); ///< Workspace for TJpgDec, aligned to 32-bit boundary.
  /*! \endcond */

  uint8_t jpg_source = 0; ///< Source of the JPEG data.

  int16_t jpeg_x = 0; ///< X-coordinate for rendering JPEG.
  int16_t jpeg_y = 0; ///< Y-coordinate for rendering JPEG.

  uint8_t jpgScale = 0; ///< JPEG scaling factor.

  SketchCallback tft_output =
      nullptr; ///< Callback function for rendering JPEG blocks.

  TJpg_Decoder *thisPtr =
      nullptr; ///< Pointer to this instance, used in static functions.
};

extern TJpg_Decoder TJpgDec; ///< Global instance of TJpg_Decoder.

#endif // TJpg_Decoder_H
