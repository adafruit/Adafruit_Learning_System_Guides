// SPDX-FileCopyrightText: 2019 Phillip Burgess for Adafruit Industries
//
// SPDX-License-Identifier: MIT

//34567890123456789012345678901234567890123456789012345678901234567890123456

#define ARDUINOJSON_ENABLE_COMMENTS 1
#include <ArduinoJson.h>          // JSON config file functions
#include "globals.h"

extern Adafruit_Arcada arcada;

// CONFIGURATION FILE HANDLING ---------------------------------------------

// This function decodes an integer value from the JSON config file in a
// variety of different formats...for example, "foo" might be specified:
// "foo" : 42                         - As a signed decimal integer
// "foo" : "0x42"                     - Positive hexadecimal integer
// "foo" : "0xF800"                   - 16-bit RGB color
// "foo" : [ 255, 0, 0 ]              - RGB color using integers 0-255
// "foo" : [ "0xFF", "0x00", "0x00" ] - RGB using hexadecimal
// "foo" : [ 1.0, 0.0, 0.0 ]          - RGB using floats
// 24-bit RGB colors will be decimated to 16-bit format.
// 16-bit colors returned by this func will be big-endian.
// Hexadecimal values MUST be quoted -- JSON can only handle hex as strings.
// This is NOT bulletproof! It does handle many well-formatted (and a few
// not-so-well-formatted) numbers, but not every imaginable case, and makes
// some guesses about what's an RGB color vs what isn't. Doing what I can,
// JSON is picky and and at some point folks just gotta get it together.
static int32_t dwim(JsonVariant v, int32_t def = 0) { // "Do What I Mean"
  if(v.is<int>()) {                      // If integer...
    return v;                            // ...return value directly
  } else if(v.is<float>()) {             // If float...
    return (int)(v.as<float>() + 0.5);   // ...return rounded integer
  } else if(v.is<const char*>()) {             // If string...
    if((strlen(v) == 6) && !strncasecmp(v, "0x", 2)) { // 4-digit hex?
      uint16_t rgb = strtol(v, NULL, 0); // Probably a 16-bit RGB color,
      return __builtin_bswap16(rgb);     // convert to big-endian
    } else {
      return strtol(v, NULL, 0);         // Some other int/hex/octal
    }
  } else if(v.is<JsonArray>()) {         // If array...
    if(v.size() >= 3) {                  // ...and at least 3 elements...
      long cc[3];                        // ...parse RGB color components...
      for(uint8_t i=0; i<3; i++) {       // Handle int/hex/octal/float...
        if(v[i].is<int>()) {
          cc[i] = v[i].as<int>();
        } else if(v[i].is<float>()) {
          cc[i] = (int)(v[i].as<float>() * 255.999);
        } else if(v[i].is<const char*>()) {
          cc[i] = strtol(v[i], NULL, 0);
        }
        if(cc[i] > 255)    cc[i] = 255;  // Clip to 8-bit range
        else if(cc[i] < 0) cc[i] = 0;
      }
      uint16_t rgb = ((cc[0] & 0xF8) << 8) | // Decimate 24-bit RGB
                     ((cc[1] & 0xFC) << 3) | // to 16-bit
                     ( cc[2]         >> 3);
      return __builtin_bswap16(rgb);         // and return big-endian
    } else {                             // Some unexpected array
      if(v[0].is<int>()) {               // Return first element
        return v[0];                     // as a simple integer,
      } else {
        return strtol(v[0], NULL, 0);    // or int/hex/octal
      }
    }
  } else {                               // Not found in document
    return def;                          // ...return default value
  }
}

/*
static void getFilename(JsonVariant v, char **ptr) {
  if(*ptr) {          // If string already allocated,
    free(*ptr);       // delete old value...
    *ptr = NULL;
  }
  if(v.is<const char*>()) {
    *ptr = strdup(v); // Make a copy of string, save that
  }
}
*/

void loadConfig(char *filename) {
  File    file;
  uint8_t rotation = 3;

  if(file = arcada.open(filename, FILE_READ)) {
    StaticJsonDocument<2048> doc;

    yield();
    DeserializationError error = deserializeJson(doc, file);
    yield();
    if(error) {
      Serial.println("Config file error, using default settings");
      Serial.println(error.c_str());
    } else {
      uint8_t e;

      // Values common to both eyes or global program config...
      stackReserve    = dwim(doc["stackReserve"], stackReserve),
      eyeRadius       = dwim(doc["eyeRadius"]);
      eyelidIndex     = dwim(doc["eyelidIndex"]);
      irisRadius      = dwim(doc["irisRadius"]);
      slitPupilRadius = dwim(doc["slitPupilRadius"]);
      gazeMax         = dwim(doc["gazeMax"], gazeMax);
      JsonVariant v;
      v = doc["coverage"];
      if(v.is<int>() || v.is<float>()) coverage = v.as<float>();
      v = doc["upperEyelid"];
      if(v.is<const char*>())    upperEyelidFilename = strdup(v);
      v = doc["lowerEyelid"];
      if(v.is<const char*>())    lowerEyelidFilename = strdup(v);

      lightSensorMin   = doc["lightSensorMin"] | lightSensorMin;
      lightSensorMax   = doc["lightSensorMax"] | lightSensorMax;
      if(lightSensorMin > 1023)   lightSensorMin = 1023;
      else if(lightSensorMin < 0) lightSensorMin = 0;
      if(lightSensorMax > 1023)   lightSensorMax = 1023;
      else if(lightSensorMax < 0) lightSensorMax = 0;
      if(lightSensorMin > lightSensorMax) {
        uint16_t  temp = lightSensorMin;
        lightSensorMin = lightSensorMax;
        lightSensorMax = temp;
      }
      lightSensorCurve = doc["lightSensorCurve"] | lightSensorCurve;
      if(lightSensorCurve < 0.01) lightSensorCurve = 0.01;

      // The pupil size is represented somewhat differently in the code
      // than in the settings file. Expressing it as "pupilMin" (the
      // smallest pupil size as a fraction of iris size, from 0.0 to 1.0)
      // and pupilMax (the largest pupil size) seems easier for people
      // to grasp. But in the code it's actually represented as irisMin
      // (the inverse of pupilMax as described above) and irisRange
      // (an amount added to irisMin which yields the inverse of pupilMin).
      float pMax = doc["pupilMax"] | (1.0 - irisMin),
            pMin = doc["pupilMin"] | (1.0 - (irisMin + irisRange));
      if(pMin > 1.0)      pMin = 1.0;
      else if(pMin < 0.0) pMin = 0.0;
      if(pMax > 1.0)      pMax = 1.0;
      else if(pMax < 0.0) pMax = 0.0;
      if(pMin > pMax) {
        float temp = pMin;
        pMin = pMax;
        pMax = temp;
      }
      irisMin   = (1.0 - pMax);
      irisRange = (pMax - pMin);

      lightSensorPin = doc["lightSensor"]   | lightSensorPin;
      boopPin        = doc["boopSensor"]    | boopPin;
// Computed at startup, NOT from file now
//      boopThreshold  = doc["boopThreshold"] | boopThreshold;

      // Values that can be distinct per-eye but have a common default...
      uint16_t    pupilColor   = dwim(doc["pupilColor"] , eye[0].pupilColor),
                  backColor    = dwim(doc["backColor"]  , eye[0].backColor),
                  irisColor    = dwim(doc["irisColor"]  , eye[0].iris.color),
                  scleraColor  = dwim(doc["scleraColor"], eye[0].sclera.color),
                  irisMirror   = 0,
                  scleraMirror = 0,
                  irisAngle    = 0,
                  scleraAngle  = 0,
                  irisiSpin    = 0,
                  scleraiSpin  = 0;
      float       irisSpin     = 0.0,
                  scleraSpin   = 0.0;
      JsonVariant iristv       = doc["irisTexture"],
                  scleratv     = doc["scleraTexture"];

      rotation  = doc["rotate"] | rotation; // Screen rotation (GFX lib)
      rotation &= 3;

      v = doc["tracking"];
      if(v.is<bool>()) tracking = v.as<bool>();
      v = doc["squint"];
      if(v.is<float>()) {
        trackFactor = 1.0 - v.as<float>();
        if(trackFactor < 0.0)      trackFactor = 0.0;
        else if(trackFactor > 1.0) trackFactor = 1.0;
      }

      // Convert clockwise int (0-1023) or float (0.0-1.0) values to CCW int used internally:
      v = doc["irisSpin"];
      if(v.is<float>()) irisSpin   = v.as<float>() * -1024.0;
      v = doc["scleraSpin"];
      if(v.is<float>()) scleraSpin = v.as<float>() * -1024.0;
      v = doc["irisiSpin"];
      if(v.is<int>()) irisiSpin    = v.as<int>();
      v = doc["scleraiSpin"];
      if(v.is<int>()) scleraiSpin  = v.as<int>();
      v = doc["irisMirror"];
      if(v.is<bool>() || v.is<int>()) irisMirror   = v ? 1023 : 0;
      v = doc["scleraMirror"];
      if(v.is<bool>() || v.is<int>()) scleraMirror = v ? 1023 : 0;
      for(e=0; e<NUM_EYES; e++) {
        eye[e].pupilColor    = pupilColor;
        eye[e].backColor     = backColor;
        eye[e].iris.color    = irisColor;
        eye[e].sclera.color  = scleraColor;
        // The globally-set irisAngle and scleraAngle are read each
        // time through because each eye has a distinct default if
        // not set globally. Override only if set globally at first...
        v = doc["irisAngle"];
        if(v.is<int>())        irisAngle   = 1023 - (v.as<int>() & 1023);
        else if(v.is<float>()) irisAngle   = 1023 - ((int)(v.as<float>() * 1024.0) & 1023);
        else                   irisAngle   = eye[e].iris.angle;
        eye[e].iris.angle    = eye[e].iris.startAngle   = irisAngle;
        v = doc["scleraAngle"];
        if(v.is<int>())        scleraAngle = 1023 - (v.as<int>() & 1023);
        else if(v.is<float>()) scleraAngle = 1023 - ((int)(v.as<float>() * 1024.0) & 1023);
        else                   scleraAngle = eye[e].sclera.angle;
        eye[e].sclera.angle  = eye[e].sclera.startAngle = scleraAngle;
        eye[e].iris.mirror   = irisMirror;
        eye[e].sclera.mirror = scleraMirror;
        eye[e].iris.spin     = irisSpin;
        eye[e].sclera.spin   = scleraSpin;
        eye[e].iris.iSpin    = irisiSpin;
        eye[e].sclera.iSpin  = scleraiSpin;
        // iris and sclera filenames are strdup'd for each eye rather than
        // sharing a common pointer, reason being that it gets really messy
        // below when overriding one or the other and trying to do the right
        // thing with free/strdup. So this does waste a tiny bit of RAM but
        // it's only the size of the filenames and only during init. NBD.
        if(iristv.is<const char*>())   eye[e].iris.filename   = strdup(iristv);
        if(scleratv.is<const char*>()) eye[e].sclera.filename = strdup(scleratv);
        eye[e].rotation = rotation; // Might get override in per-eye code below
      }

#if NUM_EYES > 1
      // Process any distinct per-eye settings...
      // NOT EVERYTHING IS CONFIGURABLE PER-EYE. Color and texture stuff, yes.
      // Other things like iris size or pupil shape are not, reason being that
      // there isn't enough RAM for the polar angle/dist tables for two eyes.
      for(uint8_t e=0; e<NUM_EYES; e++) {
        eye[e].pupilColor    = dwim(doc[eye[e].name]["pupilColor"]  , eye[e].pupilColor);
        eye[e].backColor     = dwim(doc[eye[e].name]["backColor"]   , eye[e].backColor);
        eye[e].iris.color    = dwim(doc[eye[e].name]["irisColor"]   , eye[e].iris.color);
        eye[e].sclera.color  = dwim(doc[eye[e].name]["scleraColor"] , eye[e].sclera.color);
        v = doc[eye[e].name]["irisAngle"];
        if(v.is<int>())        eye[e].iris.angle   = 1023 - (v.as<int>()   & 1023);
        else if(v.is<float>()) eye[e].iris.angle   = 1023 - ((int)(v.as<float>()  * 1024.0) & 1023);
        eye[e].iris.startAngle = eye[e].iris.angle;
        v = doc[eye[e].name]["scleraAngle"];
        if(v.is<int>())        eye[e].sclera.angle = 1023 - (v.as<int>() & 1023);
        else if(v.is<float>()) eye[e].sclera.angle = 1023 - ((int)(v.as<float>() * 1024.0) & 1023);
        eye[e].sclera.startAngle = eye[e].sclera.angle;
        v = doc[eye[e].name]["irisSpin"];
        if(v.is<float>()) eye[e].iris.spin   = v.as<float>() * -1024.0;
        v = doc[eye[e].name]["scleraSpin"];
        if(v.is<float>()) eye[e].sclera.spin = v.as<float>() * -1024.0;
        v = doc[eye[e].name]["irisiSpin"];
        if(v.is<int>()) eye[e].iris.iSpin   = v.as<int>();
        v = doc[eye[e].name]["scleraiSpin"];
        if(v.is<int>()) eye[e].sclera.iSpin = v.as<int>();
        v = doc[eye[e].name]["irisMirror"];
        if(v.is<bool>() || v.is<int>()) eye[e].iris.mirror   = v ? 1023 : 0;
        v = doc[eye[e].name]["scleraMirror"];
        if(v.is<bool>() || v.is<int>()) eye[e].sclera.mirror = v ? 1023 : 0;
        v = doc[eye[e].name]["irisTexture"];
        if(v.is<const char*>()) {                           // Per-eye iris texture specified?
          if(eye[e].iris.filename) free(eye[e].iris.filename); // Remove old name if any
          eye[e].iris.filename = strdup(v);                    // Save new name
        }
        v = doc[eye[e].name]["scleraTexture"]; // Ditto w/sclera
        if(v.is<const char*>()) {
          if(eye[e].sclera.filename) free(eye[e].sclera.filename);
          eye[e].sclera.filename = strdup(v);
        }
        eye[e].rotation  = doc[eye[e].name]["rotate"] | rotation;
        eye[e].rotation &= 3;
      }
#endif
#if defined(ADAFRUIT_MONSTER_M4SK_EXPRESS)
      v = doc["voice"];
      if(v.is<bool>()) voiceOn = v.as<bool>();
      currentPitch = defaultPitch = doc["pitch"] | defaultPitch;
      gain = doc["gain"] | gain;
      modulate = doc["modulate"] | modulate;
      v = doc["waveform"];
      if(v.is<const char*>()) { // If string...
        if(!strncasecmp(     v, "sq", 2)) waveform = 1;
        else if(!strncasecmp(v, "si", 2)) waveform = 2;
        else if(!strncasecmp(v, "t" , 1)) waveform = 3;
        else if(!strncasecmp(v, "sa", 2)) waveform = 4;
        else                              waveform = 0;
      }
#endif // ADAFRUIT_MONSTER_M4SK_EXPRESS
    }
    file.close();
  } else {
    Serial.println("Can't open config file, using default settings");
  }

  // INITIALIZE DEFAULT VALUES if config file missing or in error ----------

  // Some defaults are initialized in globals.h (because there's no way to
  // check these for invalid input), others are initialized here if there's
  // an obvious flag (e.g. value of 0 means "use default").

  // Default eye size is set slightly larger than the screen. This is on
  // purpose, because displacement effect looks worst at its extremes...this
  // allows the pupil to move close to the edge of the display while keeping
  // a few pixels distance from the displacement limits.
  if(!eyeRadius) eyeRadius = DISPLAY_SIZE/2 + 5;
  else           eyeRadius = abs(eyeRadius);
  eyeDiameter  = eyeRadius * 2;
  eyelidIndex &= 0xFF;      // From table: learn.adafruit.com/assets/61921
  eyelidColor  = eyelidIndex * 0x0101; // Expand eyelidIndex to 16-bit RGB

  if(!irisRadius) irisRadius = DISPLAY_SIZE/4; // Size in screen pixels
  else            irisRadius = abs(irisRadius);
  slitPupilRadius = abs(slitPupilRadius);
  if(slitPupilRadius > irisRadius) slitPupilRadius = irisRadius;

  if(coverage < 0.0)      coverage = 0.0;
  else if(coverage > 1.0) coverage = 1.0;
  mapRadius   = (int)(eyeRadius * M_PI * coverage + 0.5);
  mapDiameter = mapRadius * 2;
}

// EYELID AND TEXTURE MAP FILE HANDLING ------------------------------------

// Load one eyelid, convert bitmap to 2 arrays (min, max values per column).
// Pass in filename, destination arrays (mins, maxes, 240 elements each).
ImageReturnCode loadEyelid(char *filename,
  uint8_t *minArray, uint8_t *maxArray, uint8_t init, uint32_t maxRam) {
  Adafruit_Image  image; // Image object is on stack, pixel data is on heap
  int32_t         w, h;
  uint32_t        tempBytes;
  uint8_t        *tempPtr = NULL;
  ImageReturnCode status;
  Adafruit_ImageReader *reader;

  yield();
  reader = arcada.getImageReader();
  if (!reader) {
     return IMAGE_ERR_FILE_NOT_FOUND;
  }

  memset(minArray, init, DISPLAY_SIZE); // Fill eyelid arrays with init value to
  memset(maxArray, init, DISPLAY_SIZE); // mark 'no eyelid data for this column'

  // This is the "booster seat" described in m4eyes.ino
  yield();
  if(reader->bmpDimensions(filename, &w, &h) == IMAGE_SUCCESS) {
    tempBytes = ((w + 7) / 8) * h; // Bitmap size in bytes
    if (maxRam > tempBytes) {
      if((tempPtr = (uint8_t *)malloc(maxRam - tempBytes)) != NULL) {
        // Make SOME tempPtr reference, or optimizer removes the alloc!
        tempPtr[0] = 0;
      }
    }
    // DON'T nest the image-reading case in here. If the fragmentation
    // culprit can be found, this block of code (and the free() block
    // later) are easily removed.
  }

  yield();
  if((status = reader->loadBMP(filename, image)) == IMAGE_SUCCESS) {
    if(image.getFormat() == IMAGE_1) { // MUST be 1-bit image
      uint16_t *palette = image.getPalette();
      uint8_t   white = (!palette || (palette[1] > palette[0]));
      int       x, y, ix, iy, sx1, sx2, sy1, sy2;
      // Center/clip eyelid image with respect to screen...
      sx1 = (DISPLAY_SIZE - image.width()) / 2;  // leftmost pixel, screen space
      sy1 = (DISPLAY_SIZE - image.height()) / 2; // topmost pixel, screen space
      sx2 = sx1 + image.width() - 1;    // rightmost pixel, screen space
      sy2 = sy1 + image.height() - 1;   // lowest pixel, screen space
      ix  = -sx1;                       // leftmost pixel, image space
      iy  = -sy1;                       // topmost pixel, image space
      if(sx1 <   0) sx1 =   0;          // image wider than screen
      if(sy1 <   0) sy1 =   0;          // image taller than screen
      if(sx2 > (DISPLAY_SIZE-1)) sx2 = DISPLAY_SIZE - 1; // image wider than screen
      if(sy2 > (DISPLAY_SIZE-1)) sy2 = DISPLAY_SIZE - 1; // image taller than screen
      if(ix   <   0) ix   =   0;        // image narrower than screen
      if(iy   <   0) iy   =   0;        // image shorter than screen

      GFXcanvas1 *canvas = (GFXcanvas1 *)image.getCanvas();
      uint8_t    *buffer = canvas->getBuffer();
      int         bytesPerLine = (image.width() + 7) / 8;
      for(x=sx1; x <= sx2; x++, ix++) { // For each column...
        yield();
        // Get initial pointer into image buffer
        uint8_t *ptr  = &buffer[iy * bytesPerLine + ix / 8];
        uint8_t  mask = 0x80 >> (ix & 7); // Column mask
        uint8_t  wbit = white ? mask : 0; // Bit value for white pixel
        int      miny = 255, maxy;
        for(y=sy1; y<=sy2; y++, ptr += bytesPerLine) {
          if((*ptr & mask) == wbit) { // Is pixel set?
            if(miny == 255) miny = y; // If 1st set pixel, set miny
            maxy = y;                 // If set pixel at all, set max
          }
        }
        if(miny != 255) {
          // Because of coordinate system used later (screen rotated),
          // min/max and Y coordinates are flipped before storing...
          maxArray[x] = DISPLAY_SIZE - 1 - miny;
          minArray[x] = DISPLAY_SIZE - 1 - maxy;
        }
      }
    } else {
      status = IMAGE_ERR_FORMAT; // Don't just return, need to dealloc...
    }
  }

  if(tempPtr) {
    free(tempPtr);
  }
  // image destructor will handle dealloc of that object's data

  return status;
}

ImageReturnCode loadTexture(char *filename, uint16_t **data,
  uint16_t *width, uint16_t *height, uint32_t maxRam) {
  Adafruit_Image  image; // Image object is on stack, pixel data is on heap
  int32_t         w, h;
  uint32_t        tempBytes;
  uint8_t        *tempPtr = NULL;
  ImageReturnCode status;
  Adafruit_ImageReader *reader;

  yield();
  reader = arcada.getImageReader();
  if (!reader) {
     return IMAGE_ERR_FILE_NOT_FOUND;
  }
  
  // This is the "booster seat" described in m4eyes.ino
  if(reader->bmpDimensions(filename, &w, &h) == IMAGE_SUCCESS) {
    tempBytes = w * h * 2; // Image size in bytes (converted to 16bpp)
    if (maxRam > tempBytes) {
      if((tempPtr = (uint8_t *)malloc(maxRam - tempBytes)) != NULL) {
        // Make SOME tempPtr reference, or optimizer removes the alloc!
        tempPtr[0] = 0;
      }
    }
    // DON'T nest the image-reading case in here. If the fragmentation
    // culprit can be found, this block of code (and the free() block
    // later) are easily removed.
  }

  yield();
  if((status = reader->loadBMP(filename, image)) == IMAGE_SUCCESS) {
    if(image.getFormat() == IMAGE_16) { // MUST be 16-bit image
      Serial.println("Texture loaded!");
      GFXcanvas16 *canvas = (GFXcanvas16 *)image.getCanvas();
      canvas->byteSwap(); // Match screen endianism for direct DMA xfer
      *width  = image.width();
      *height = image.height();
      *data = (uint16_t *)arcada.writeDataToFlash((uint8_t *)canvas->getBuffer(),
        (int)*width * (int)*height * 2);
    } else {
      status = IMAGE_ERR_FORMAT; // Don't just return, need to dealloc...
    }
  }

  if(tempPtr) {
    free(tempPtr);
  }
  // image destructor will handle dealloc of that object's data

  return status;
}
