// BMP-reading code. Much of this is adapted from the Adafruit_ImageReader
// library, which is extremely LCD-display-centric and turned out to be
// neither workable nor easily extensible into what was needed here. That's
// okay. For now, I just pulled in minimal parts of that code, with changes
// as needed for this project (and dropping some portability considerations).

#include <SdFat.h>

// Barebones query pixel height of BMP image file. NOT universally portable;
// does some rude straight-to-var little-endian reads.
// Param:   Pointer to FAT volume.
// Param:   Absolute filename.
// Param:   Pointer to int32_t for height result.
// Returns: true on success, false on ANY error, does not distinguish
//          (file not found, no BMP signature, etc.).
bool bmpHeight(FatVolume *fs, char *filename, int32_t *height) {
  File32 file;
  bool   status = false; // Assume error until success
  if ((file = fs->open(filename, FILE_READ))) {
    uint16_t sig;
    file.read(&sig, sizeof sig);          // Little-endian straight to var
    if (sig == 0x4D42) {                  // BMP signature?
      file.seekCur(20);                   // Skip file size, width, etc.
      file.read(height, sizeof(int32_t)); // Little-endian straight to var
      if (*height < 0) *height *= -1;     // Handle top-to-bottom variant
      status = true; // YAY
    }
    file.close();
  }
  return status;
}

// Barebones BMP read into RAM. ALL images regardless of BMP format are
// converted as needed into a DotStar-ready 24-bit-per-pixel format. Again
// this is NOT universally portable; rude little-endian reads.
// Param:   Pointer to FAT volume.
// Param:   Absolute filename.
// Param:   Pointer to uint8_t for storing result (destination buffer
//          is assumed allocated and cleared, not performed here).
// Param:   Max width to clip or pad to (DotStar strip length).
// Param:   Red, green, blue byte offsets (0-2) in dest buffer.
// Param:   Brightness (0.0 to 255.0).
// Param:   Gamma (1.0 = linear, 2.6 = typical LED curve). Gamma is a lossy
//          operation; might prefer to pass 1.0 and do adjustment on source
//          image instead w/dithering, or perhaps future poi code could do
//          this on-the-fly. But for now, on load.
// Returns: true on success, false on ANY error, does not distinguish
//          (file not found, no BMP signature, etc.).
bool loadBMP(FatVolume *fs, char *filename, uint8_t *dest,
             const uint16_t dest_width, const uint8_t rOffset,
             const uint8_t gOffset, const uint8_t bOffset,
             const float brightness, const float gamma) {
  File32 file;
  bool   status = false; // Assume error until success
  if ((file = fs->open(filename, FILE_READ))) {
    uint16_t sig;
    file.read(&sig, sizeof sig);          // Little-endian straight to var
    if (sig == 0x4D42) {                  // BMP signature?
      uint32_t offset;                    // Start of image data
      uint32_t header_size;               // Indicates BMP version
      int32_t  bmp_width, bmp_height;     // BMP width & height in pixels
      boolean  flip = true;               // BMP is stored bottom-to-top
      uint32_t compression = 0;           // BMP compression mode
      uint32_t colors = 0;                // Number of colors in palette
      uint16_t planes;
      uint16_t depth;

      file.seekCur(8); // Skip file size, creator bytes
      file.read(&offset     , sizeof offset);
      file.read(&header_size, sizeof header_size); // DIB header...
      file.read(&bmp_width  , sizeof bmp_width);
      file.read(&bmp_height , sizeof bmp_height);
      // If bmpHeight is negative, image is in top-down order.
      // This is not canon but has been observed in the wild.
      if (bmp_height < 0) {
        bmp_height *= -1;
        flip = false;
      }
      file.read(&planes, sizeof planes);
      file.read(&depth , sizeof depth);
      // Compression mode is present in later BMP versions (default = none)
      if (header_size > 12) {
        file.read(&compression, sizeof compression);
        file.seekCur(12);                  // Skip raw bitmap data size, etc.
        file.read(&colors, sizeof colors); // # of colors in palette; 0 = 2^depth
        file.seekCur(4);                   // Skip # of colors used
        // File position should now be at start of palette (if present)
      }

      if ((planes == 1) && (compression == 0)) { // Only uncompressed is handled
        uint8_t palette[3][256]; // Rude but code's easier than malloc check
        uint8_t b;               // Byte-holding var used in 1-8 bit modes

        if (depth < 16) { // Lower depths include a color palette
          if (!colors) colors = 1 << depth;
          for (uint16_t i = 0; i < colors; i++) {
            uint32_t rgb;
            file.read(&rgb, sizeof rgb);
            palette[rOffset][i] = (uint8_t)(pow((float)((rgb >> 16) & 0xFF) / 255.0, gamma) * brightness + 0.5);
            palette[gOffset][i] = (uint8_t)(pow((float)((rgb >>  8) & 0xFF) / 255.0, gamma) * brightness + 0.5);
            palette[bOffset][i] = (uint8_t)(pow((float)( rgb        & 0xFF) / 255.0, gamma) * brightness + 0.5);
          }
        } else {
          // But HEY, as long as we have that palette array taking up space
          // on the heap...use it to pre-compute a brightness/gamma table,
          // saves a TON of floating-point math on every pixel later.
          for (uint16_t i = 0; i < 256; i++) {
            palette[0][i] = (uint8_t)(pow((float)i / 255.0, gamma) * brightness + 0.5);
          }
        }

        // BMP rows are padded (if needed) to 4-byte boundary,
        // width loaded is cropped if needed to DotStar strand length.
        uint32_t row_size   = ((depth * bmp_width + 31) / 32) * 4;
        int      load_width = min(bmp_width, dest_width);

        for (int row = 0; row < bmp_height; row++) { // For each scanline...

          file.seekSet(offset + row_size * (flip ? bmp_height - 1 - row : row));
          uint8_t *d2 = dest + row * dest_width * 3;

          switch (depth) {
          case 32:
            for (int col = 0; col < load_width; col++, d2 += 3) {
              uint32_t rgba;
              file.read(&rgba, sizeof rgba);
              d2[rOffset] = palette[0][(rgba >> 16) & 0xFF]; // palette[0] is
              d2[gOffset] = palette[0][(rgba >>  8) & 0xFF]; // brightness/gamma
              d2[bOffset] = palette[0][ rgba        & 0xFF]; // adjustment table
            }
            break;
          case 24:
            for (int col = 0; col < load_width; col++, d2 += 3) {
              d2[bOffset] = palette[0][file.read()]; // palette[0] is
              d2[gOffset] = palette[0][file.read()]; // brightness/gamma
              d2[rOffset] = palette[0][file.read()]; // adjustment table
            }
            break;
          case 16:
            // Not currently supported but might be nice to have.
            // Will require dissecting DIB header bitfields.
            break;
          case 8:
            for (int col = 0; col < load_width; col++, d2 += 3) {
              b     = file.read();
              d2[0] = palette[0][b];
              d2[1] = palette[1][b];
              d2[2] = palette[2][b];
            }
            break;
          case 4:
            for (int col = 0; col < load_width; col++, d2 += 3) {
              uint8_t n; // 4-bit pixel value
              if (!(col & 1)) {
                b = file.read();
                n = b >> 4;
              } else {
                n = b & 0xF;
              }
              d2[0] = palette[0][n];
              d2[1] = palette[1][n];
              d2[2] = palette[2][n];
            }
            break;
          // A 2-bit BMP mode exists but is SUPER ESOTERIC (apparently
          // a Windows CE thing), not supported here (nor in Photoshop).
          case 2:
            break;
          case 1:
            for (int col = 0; col < load_width; col++, d2 += 3) {
              if (!(col & 7)) b = file.read();
              uint8_t n = (b >> (7 - (col & 7))) & 1;
              d2[0] = palette[0][n];
              d2[1] = palette[1][n];
              d2[2] = palette[2][n];
            }
            break;
          } // end switch

        } // end row
        status = true; // YAY
      } // end planes/compression check
    } // end signature
    file.close();
  } // end file open
  return status;
}
