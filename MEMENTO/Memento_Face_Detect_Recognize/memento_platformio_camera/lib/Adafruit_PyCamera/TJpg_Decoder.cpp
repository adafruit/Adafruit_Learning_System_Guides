// SPDX-FileCopyrightText: ChaN, Bodmer
//
// SPDX-License-Identifier: BSD-2-Clause
/*
TJpg_Decoder.cpp

Created by Bodmer 18/10/19

Latest version here:
https://github.com/Bodmer/TJpg_Decoder
*/

#include "TJpg_Decoder.h"

// Create a class instance to be used by the sketch (defined as extern in
// header)
TJpg_Decoder TJpgDec;

/**************************************************************************/
/**
 * @brief Constructor for the TJpg_Decoder class.
 *
 * @details Initializes a new instance of the TJpg_Decoder class.
 *          Sets up a pointer to this class instance for static functions.
 */
/**************************************************************************/
TJpg_Decoder::TJpg_Decoder() {
  // Setup a pointer to this class for static functions
  thisPtr = this;
}

/**************************************************************************/
/**
 * @brief Destructor for the TJpg_Decoder class.
 *
 * @details Releases any resources or memory allocated by the TJpg_Decoder
 * instance.
 */
/**************************************************************************/
TJpg_Decoder::~TJpg_Decoder() {
  // Bye
}

/**************************************************************************/
/**
 * @brief Sets the byte swapping option for the JPEG decoder.
 *
 * @details This function configures whether the bytes in the decoded JPEG image
 *          should be swapped. This is useful for different hardware
 * configurations and image rendering methods.
 *
 * @param swapBytes Boolean flag to enable or disable byte swapping.
 */
/**************************************************************************/
void TJpg_Decoder::setSwapBytes(bool swapBytes) { _swap = swapBytes; }

/**************************************************************************/
/**
 * @brief Sets the JPEG image scale factor.
 *
 * @details This function configures the scaling factor for the JPEG decoding
 * process. It allows the image to be reduced by a factor of 1, 2, 4, or 8. This
 * can be useful for handling large images or for faster rendering with reduced
 *          resolution.
 *
 * @param scaleFactor The scale factor for the JPEG image (1, 2, 4, or 8).
 */
/**************************************************************************/
void TJpg_Decoder::setJpgScale(uint8_t scaleFactor) {
  switch (scaleFactor) {
  case 1:
    jpgScale = 0;
    break;
  case 2:
    jpgScale = 1;
    break;
  case 4:
    jpgScale = 2;
    break;
  case 8:
    jpgScale = 3;
    break;
  default:
    jpgScale = 0;
  }
}

/**************************************************************************/
/**
 * @brief Sets the callback function for rendering decoded JPEG blocks.
 *
 * @details This function sets a user-defined callback function that is called
 *          during the JPEG decoding process. The callback function is
 * responsible for rendering the decoded image blocks to the display or other
 * output devices. This allows for custom handling of the JPEG decoding process.
 *
 * @param sketchCallback The callback function to be used for rendering decoded
 * blocks.
 */
/**************************************************************************/
void TJpg_Decoder::setCallback(SketchCallback sketchCallback) {
  tft_output = sketchCallback;
}

/**************************************************************************/
/**
 * @brief Called by tjpgd.c to retrieve more data for JPEG decoding.
 *
 * @details This function is a callback used by the JPEG decoding library
 * (tjpgd.c) to fetch more data for the decoding process. It handles data
 * retrieval from various sources including arrays, SPIFFS, and SD files. The
 * function ensures that the end of the data source is not exceeded and copies
 * the required number of bytes into the provided buffer.
 *
 * @param jdec Pointer to the JDEC structure, representing the state of the JPEG
 *             decompression process.
 * @param buf Pointer to the buffer where the fetched data should be stored. If
 * null, no data is copied.
 * @param len The number of bytes to fetch.
 *
 * @return The actual number of bytes fetched.
 */
/**************************************************************************/
unsigned int TJpg_Decoder::jd_input(JDEC *jdec, uint8_t *buf,
                                    unsigned int len) {
  TJpg_Decoder *thisPtr = TJpgDec.thisPtr;
  jdec = jdec; // Supress warning

  // Handle an array input
  if (thisPtr->jpg_source == TJPG_ARRAY) {
    // Avoid running off end of array
    if (thisPtr->array_index + len > thisPtr->array_size) {
      len = thisPtr->array_size - thisPtr->array_index;
    }

    // If buf is valid then copy len bytes to buffer
    if (buf)
      memcpy_P(buf,
               (const uint8_t *)(thisPtr->array_data + thisPtr->array_index),
               len);

    // Move pointer
    thisPtr->array_index += len;
  }

#ifdef TJPGD_LOAD_FFS
  // Handle SPIFFS input
  else if (thisPtr->jpg_source == TJPG_FS_FILE) {
    // Check how many bytes are available
    uint32_t bytesLeft = thisPtr->jpgFile.available();
    if (bytesLeft < len)
      len = bytesLeft;

    if (buf) {
      // Read into buffer, pointer moved as well
      thisPtr->jpgFile.read(buf, len);
    } else {
      // Buffer is null, so skip data by moving pointer
      thisPtr->jpgFile.seek(thisPtr->jpgFile.position() + len);
    }
  }
#endif

#if defined(TJPGD_LOAD_SD_LIBRARY)
  // Handle SD library input
  else if (thisPtr->jpg_source == TJPG_SD_FILE) {
    // Check how many bytes are available
    uint32_t bytesLeft = thisPtr->jpgSdFile.available();
    if (bytesLeft < len)
      len = bytesLeft;

    if (buf) {
      // Read into buffer, pointer moved as well
      thisPtr->jpgSdFile.read(buf, len);
    } else {
      // Buffer is null, so skip data by moving pointer
      thisPtr->jpgSdFile.seek(thisPtr->jpgSdFile.position() + len);
    }
  }
#endif

  return len;
}

/**************************************************************************/
/**
 * @brief Called by tjpgd.c with an image block for rendering.
 *
 * @details This function is a callback used by the JPEG decoding library
 * (tjpgd.c) to pass decoded image blocks for rendering. It may be a complete or
 *          partial Minimum Coded Unit (MCU). The function calculates the
 * position and dimensions of the image block and passes these parameters along
 * with the image data to a user-defined rendering function.
 *
 * @param jdec Pointer to the JDEC structure, representing the state of the JPEG
 *             decompression process.
 * @param bitmap Pointer to the image block data.
 * @param jrect Pointer to the JRECT structure defining the position and size of
 *              the image block.
 *
 * @return The return value from the user-defined rendering function.
 */
/**************************************************************************/
// Pass image block back to the sketch for rendering, may be a complete or
// partial MCU
int TJpg_Decoder::jd_output(JDEC *jdec, void *bitmap, JRECT *jrect) {
  // This is a static function so create a pointer to access other members of
  // the class
  TJpg_Decoder *thisPtr = TJpgDec.thisPtr;

  jdec = jdec; // Supress warning as ID is not used

  // Retrieve rendering parameters and add any offset
  int16_t x = jrect->left + thisPtr->jpeg_x;
  int16_t y = jrect->top + thisPtr->jpeg_y;
  uint16_t w = jrect->right + 1 - jrect->left;
  uint16_t h = jrect->bottom + 1 - jrect->top;

  // Pass the image block and rendering parameters in a callback to the sketch
  return thisPtr->tft_output(x, y, w, h, (uint16_t *)bitmap);
}

#if defined(TJPGD_LOAD_SD_LIBRARY) || defined(TJPGD_LOAD_FFS)

************************************************************************** /
    /**
     * @brief Draw a named jpg file at x,y (name in char array).
     * @details Generic file call for SD or SPIFFS, uses leading / to
     * distinguish SPIFFS files.
     * @param x X-coordinate where the image will be drawn.
     * @param y Y-coordinate where the image will be drawn.
     * @param pFilename Pointer to the character array containing the file name.
     * @return JRESULT status of the drawing operation.
     */
    /**************************************************************************/
    // Generic file call for SD or SPIFFS, uses leading / to distinguish SPIFFS
    // files
    JRESULT TJpg_Decoder::drawJpg(int32_t x, int32_t y, const char *pFilename) {

#if defined(ARDUINO_ARCH_ESP8266) || defined(ESP32)
#if defined(TJPGD_LOAD_SD_LIBRARY)
  if (*pFilename == '/')
#endif
    return drawFsJpg(x, y, pFilename);
#endif

#if defined(TJPGD_LOAD_SD_LIBRARY)
  return drawSdJpg(x, y, pFilename);
#endif

  return JDR_INP;
}

/**************************************************************************/
/**
 * @brief Draw a named jpg file at x,y (name in String).
 * @details Generic file call for SD or SPIFFS, uses leading / to distinguish
 * SPIFFS files.
 * @param x X-coordinate where the image will be drawn.
 * @param y Y-coordinate where the image will be drawn.
 * @param pFilename String containing the file name.
 * @return JRESULT status of the drawing operation.
 */
/**************************************************************************/
// Generic file call for SD or SPIFFS, uses leading / to distinguish SPIFFS
// files
JRESULT TJpg_Decoder::drawJpg(int32_t x, int32_t y, const String &pFilename) {

#if defined(ARDUINO_ARCH_ESP8266) || defined(ESP32)
#if defined(TJPGD_LOAD_SD_LIBRARY)
  if (pFilename.charAt(0) == '/')
#endif
    return drawFsJpg(x, y, pFilename);
#endif

#if defined(TJPGD_LOAD_SD_LIBRARY)
  return drawSdJpg(x, y, pFilename);
#endif

  return JDR_INP;
}

/**************************************************************************/
/**
 * @brief Get width and height of a jpg file (name in char array).
 * @details Generic file call for SD or SPIFFS, uses leading / to distinguish
 * SPIFFS files.
 * @param w Pointer to store the width of the image.
 * @param h Pointer to store the height of the image.
 * @param pFilename Pointer to the character array containing the file name.
 * @return JRESULT status of the size retrieval operation.
 */
/**************************************************************************/
// Generic file call for SD or SPIFFS, uses leading / to distinguish SPIFFS
// files
JRESULT TJpg_Decoder::getJpgSize(uint16_t *w, uint16_t *h,
                                 const char *pFilename) {

#if defined(ARDUINO_ARCH_ESP8266) || defined(ESP32)
#if defined(TJPGD_LOAD_SD_LIBRARY)
  if (*pFilename == '/')
#endif
    return getFsJpgSize(w, h, pFilename);
#endif

#if defined(TJPGD_LOAD_SD_LIBRARY)
  return getSdJpgSize(w, h, pFilename);
#endif

  return JDR_INP;
}

/**************************************************************************/
/**
 * @brief Get width and height of a jpg file (name in String).
 * @details Generic file call for SD or SPIFFS, uses leading / to distinguish
 * SPIFFS files.
 * @param w Pointer to store the width of the image.
 * @param h Pointer to store the height of the image.
 * @param pFilename String containing the file name.
 * @return JRESULT status of the size retrieval operation.
 */
/**************************************************************************/
// Generic file call for SD or SPIFFS, uses leading / to distinguish SPIFFS
// files
JRESULT TJpg_Decoder::getJpgSize(uint16_t *w, uint16_t *h,
                                 const String &pFilename) {

#if defined(ARDUINO_ARCH_ESP8266) || defined(ESP32)
#if defined(TJPGD_LOAD_SD_LIBRARY)
  if (pFilename.charAt(0) == '/')
#endif
    return getFsJpgSize(w, h, pFilename);
#endif

#if defined(TJPGD_LOAD_SD_LIBRARY)
  return getSdJpgSize(w, h, pFilename);
#endif

  return JDR_INP;
}

#endif

#ifdef TJPGD_LOAD_FFS

/**************************************************************************/
/**
 * @brief Draw a named jpg file at x,y (name in char array) from SPIFFS or
 * LittleFS.
 * @param x X-coordinate where the image will be drawn.
 * @param y Y-coordinate where the image will be drawn.
 * @param pFilename Pointer to the character array containing the file name.
 * @param fs Filesystem reference (SPIFFS or LittleFS).
 * @return JRESULT status of the drawing operation.
 */
/**************************************************************************/
// Call specific to SPIFFS
JRESULT TJpg_Decoder::drawFsJpg(int32_t x, int32_t y, const char *pFilename,
                                fs::FS &fs) {
  // Check if file exists
  if (!fs.exists(pFilename)) {
    Serial.println(F("Jpeg file not found"));
    return JDR_INP;
  }

  return drawFsJpg(x, y, fs.open(pFilename, "r"));
}

/**************************************************************************/
/**
 * @brief Draw a named jpg file at x,y (name in String) from SPIFFS or LittleFS.
 * @param x X-coordinate where the image will be drawn.
 * @param y Y-coordinate where the image will be drawn.
 * @param pFilename String containing the file name.
 * @param fs Filesystem reference (SPIFFS or LittleFS).
 * @return JRESULT status of the drawing operation.
 */
/**************************************************************************/
JRESULT TJpg_Decoder::drawFsJpg(int32_t x, int32_t y, const String &pFilename,
                                fs::FS &fs) {
  // Check if file exists
  if (!fs.exists(pFilename)) {
    Serial.println(F("Jpeg file not found"));
    return JDR_INP;
  }
  return drawFsJpg(x, y, fs.open(pFilename, "r"));
}

/**************************************************************************/
/**
 * @brief Draw a jpg with opened file handle at x,y.
 * @param x X-coordinate where the image will be drawn.
 * @param y Y-coordinate where the image will be drawn.
 * @param inFile Opened file handle to the jpg file.
 * @return JRESULT status of the drawing operation.
 */
/**************************************************************************/
JRESULT TJpg_Decoder::drawFsJpg(int32_t x, int32_t y, fs::File inFile) {
  JDEC jdec;
  JRESULT jresult = JDR_OK;

  jpg_source = TJPG_FS_FILE;
  jpeg_x = x;
  jpeg_y = y;

  jdec.swap = _swap;

  jpgFile = inFile;

  jresult = jd_prepare(&jdec, jd_input, workspace, TJPGD_WORKSPACE_SIZE,
                       (unsigned int)0);

  // Extract image and render
  if (jresult == JDR_OK) {
    jresult = jd_decomp(&jdec, jd_output, jpgScale);
  }

  // Close file
  if (jpgFile)
    jpgFile.close();

  return jresult;
}

/**************************************************************************/
/**
 * @brief Get width and height of a jpg saved in SPIFFS or LittleFS (name in
 * char array).
 * @param w Pointer to store the width of the image.
 * @param h Pointer to store the height of the image.
 * @param pFilename Pointer to the character array containing the file name.
 * @param fs Filesystem reference (SPIFFS or LittleFS).
 * @return JRESULT status of the size retrieval operation.
 */
/**************************************************************************/
// Call specific to SPIFFS
JRESULT TJpg_Decoder::getFsJpgSize(uint16_t *w, uint16_t *h,
                                   const char *pFilename, fs::FS &fs) {
  // Check if file exists
  if (!fs.exists(pFilename)) {
    Serial.println(F("Jpeg file not found"));
    return JDR_INP;
  }

  return getFsJpgSize(w, h, fs.open(pFilename, "r"));
}

/**************************************************************************/
/**
 * @brief Get width and height of a jpg saved in SPIFFS or LittleFS (name in
 * String).
 * @param w Pointer to store the width of the image.
 * @param h Pointer to store the height of the image.
 * @param pFilename String containing the file name.
 * @param fs Filesystem reference (SPIFFS or LittleFS).
 * @return JRESULT status of the size retrieval operation.
 */
/**************************************************************************/
JRESULT TJpg_Decoder::getFsJpgSize(uint16_t *w, uint16_t *h,
                                   const String &pFilename, fs::FS &fs) {
  // Check if file exists
  if (!fs.exists(pFilename)) {
    Serial.println(F("Jpeg file not found"));
    return JDR_INP;
  }

  return getFsJpgSize(w, h, fs.open(pFilename, "r"));
}

/**************************************************************************/
/**
 * @brief Get width and height of a jpg saved in SPIFFS.
 * @details Retrieves the dimensions of a JPEG image stored in SPIFFS.
 * @param w Pointer to store the width of the image.
 * @param h Pointer to store the height of the image.
 * @param inFile Opened file handle to the jpg file.
 * @return JRESULT status of the size retrieval operation.
 */
/**************************************************************************/
JRESULT TJpg_Decoder::getFsJpgSize(uint16_t *w, uint16_t *h, fs::File inFile) {
  JDEC jdec;
  JRESULT jresult = JDR_OK;

  *w = 0;
  *h = 0;

  jpg_source = TJPG_FS_FILE;

  jpgFile = inFile;

  jresult = jd_prepare(&jdec, jd_input, workspace, TJPGD_WORKSPACE_SIZE, 0);

  if (jresult == JDR_OK) {
    *w = jdec.width;
    *h = jdec.height;
  }

  // Close file
  if (jpgFile)
    jpgFile.close();

  return jresult;
}

#endif

#if defined(TJPGD_LOAD_SD_LIBRARY)

/**************************************************************************/
/**
 * @brief Draw a named jpg SD file at x,y (name in char array).
 * @details Draws a JPEG image from an SD card at specified coordinates.
 * @param x X-coordinate where the image will be drawn.
 * @param y Y-coordinate where the image will be drawn.
 * @param pFilename Pointer to the character array containing the file name.
 * @return JRESULT status of the drawing operation.
 */
/**************************************************************************/
// Call specific to SD
JRESULT TJpg_Decoder::drawSdJpg(int32_t x, int32_t y, const char *pFilename) {

  // Check if file exists
  if (!SD.exists(pFilename)) {
    Serial.println(F("Jpeg file not found"));
    return JDR_INP;
  }

  return drawSdJpg(x, y, SD.open(pFilename, FILE_READ));
}

/**************************************************************************/
/**
 * @brief Draw a named jpg SD file at x,y (name in String).
 * @details Draws a JPEG image from an SD card at specified coordinates.
 * @param x X-coordinate where the image will be drawn.
 * @param y Y-coordinate where the image will be drawn.
 * @param pFilename String containing the file name.
 * @return JRESULT status of the drawing operation.
 */
/**************************************************************************/
JRESULT TJpg_Decoder::drawSdJpg(int32_t x, int32_t y, const String &pFilename) {

  // Check if file exists
  if (!SD.exists(pFilename)) {
    Serial.println(F("Jpeg file not found"));
    return JDR_INP;
  }

  return drawSdJpg(x, y, SD.open(pFilename, FILE_READ));
}

/**************************************************************************/
/**
 * @brief Draw a jpg with opened SD file handle at x,y.
 * @details Renders a JPEG image from an opened SD file at specified
 * coordinates.
 * @param x X-coordinate where the image will be drawn.
 * @param y Y-coordinate where the image will be drawn.
 * @param inFile Opened file handle to the jpg file.
 * @return JRESULT status of the drawing operation.
 */
/**************************************************************************/
JRESULT TJpg_Decoder::drawSdJpg(int32_t x, int32_t y, File inFile) {
  JDEC jdec;
  JRESULT jresult = JDR_OK;

  jpg_source = TJPG_SD_FILE;
  jpeg_x = x;
  jpeg_y = y;

  jdec.swap = _swap;

  jpgSdFile = inFile;

  jresult = jd_prepare(&jdec, jd_input, workspace, TJPGD_WORKSPACE_SIZE, 0);

  // Extract image and render
  if (jresult == JDR_OK) {
    jresult = jd_decomp(&jdec, jd_output, jpgScale);
  }

  // Close file
  if (jpgSdFile)
    jpgSdFile.close();

  return jresult;
}

/**************************************************************************/
/**
 * @brief Get width and height of a jpg saved in SPIFFS.
 * @details Retrieves the dimensions of a JPEG image stored in SPIFFS.
 * @param w Pointer to store the width of the image.
 * @param h Pointer to store the height of the image.
 * @param pFilename Pointer to the character array containing the file name.
 * @return JRESULT status of the size retrieval operation.
 */
/**************************************************************************/
// Call specific to SD
JRESULT TJpg_Decoder::getSdJpgSize(uint16_t *w, uint16_t *h,
                                   const char *pFilename) {

  // Check if file exists
  if (!SD.exists(pFilename)) {
    Serial.println(F("Jpeg file not found"));
    return JDR_INP;
  }

  return getSdJpgSize(w, h, SD.open(pFilename, FILE_READ));
}

/**************************************************************************/
/**
 * @brief Get width and height of a jpg saved in SPIFFS.
 * @details Retrieves the dimensions of a JPEG image stored in SPIFFS.
 * @param w Pointer to store the width of the image.
 * @param h Pointer to store the height of the image.
 * @param pFilename String containing the file name.
 * @return JRESULT status of the size retrieval operation.
 */
/**************************************************************************/
JRESULT TJpg_Decoder::getSdJpgSize(uint16_t *w, uint16_t *h,
                                   const String &pFilename) {

  // Check if file exists
  if (!SD.exists(pFilename)) {
    Serial.println(F("Jpeg file not found"));
    return JDR_INP;
  }

  return getSdJpgSize(w, h, SD.open(pFilename, FILE_READ));
}

/**************************************************************************/
/**
 * @brief Get width and height of a jpg saved in SPIFFS.
 * @details Retrieves the dimensions of a JPEG image stored in SPIFFS.
 * @param w Pointer to store the width of the image.
 * @param h Pointer to store the height of the image.
 * @param inFile Opened file handle to the jpg file.
 * @return JRESULT status of the size retrieval operation.
 */
/**************************************************************************/
JRESULT TJpg_Decoder::getSdJpgSize(uint16_t *w, uint16_t *h, File inFile) {
  JDEC jdec;
  JRESULT jresult = JDR_OK;

  *w = 0;
  *h = 0;

  jpg_source = TJPG_SD_FILE;

  jpgSdFile = inFile;

  jresult = jd_prepare(&jdec, jd_input, workspace, TJPGD_WORKSPACE_SIZE, 0);

  if (jresult == JDR_OK) {
    *w = jdec.width;
    *h = jdec.height;
  }

  // Close file
  if (jpgSdFile)
    jpgSdFile.close();

  return jresult;
}

#endif

/**************************************************************************/
/**
 * @brief Draw a jpg saved in a FLASH memory array.
 * @details Renders a JPEG image stored in a FLASH memory array at specified
 * coordinates.
 * @param x X-coordinate where the image will be drawn.
 * @param y Y-coordinate where the image will be drawn.
 * @param jpeg_data Pointer to the JPEG data in FLASH memory.
 * @param data_size Size of the JPEG data in bytes.
 * @return JRESULT status of the drawing operation.
 */
/**************************************************************************/
JRESULT TJpg_Decoder::drawJpg(int32_t x, int32_t y, const uint8_t jpeg_data[],
                              uint32_t data_size) {
  JDEC jdec;
  JRESULT jresult = JDR_OK;

  jpg_source = TJPG_ARRAY;
  array_index = 0;
  array_data = jpeg_data;
  array_size = data_size;

  jpeg_x = x;
  jpeg_y = y;

  jdec.swap = _swap;

  // Analyse input data
  jresult = jd_prepare(&jdec, jd_input, workspace, TJPGD_WORKSPACE_SIZE, 0);

  // Extract image and render
  if (jresult == JDR_OK) {
    jresult = jd_decomp(&jdec, jd_output, jpgScale);
  }

  return jresult;
}

/**************************************************************************/
/**
 * @brief Get width and height of a jpg saved in a FLASH memory array.
 * @details Retrieves the dimensions of a JPEG image stored in a FLASH memory
 * array.
 * @param w Pointer to store the width of the image.
 * @param h Pointer to store the height of the image.
 * @param jpeg_data Pointer to the JPEG data in FLASH memory.
 * @param data_size Size of the JPEG data in bytes.
 * @return JRESULT status of the size retrieval operation.
 */
/**************************************************************************/
JRESULT TJpg_Decoder::getJpgSize(uint16_t *w, uint16_t *h,
                                 const uint8_t jpeg_data[],
                                 uint32_t data_size) {
  JDEC jdec;
  JRESULT jresult = JDR_OK;

  *w = 0;
  *h = 0;

  jpg_source = TJPG_ARRAY;
  array_index = 0;
  array_data = jpeg_data;
  array_size = data_size;

  // Analyse input data
  jresult = jd_prepare(&jdec, jd_input, workspace, TJPGD_WORKSPACE_SIZE, 0);

  if (jresult == JDR_OK) {
    *w = jdec.width;
    *h = jdec.height;
  }

  return jresult;
}
