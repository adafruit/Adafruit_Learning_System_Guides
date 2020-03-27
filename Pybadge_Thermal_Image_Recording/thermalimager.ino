/*
  ThermalImager_009b - Collect thermal image values from a MLX90640 sensor array,
                       display them as color-mapped pixels on a TFT screen,
  include data capture to flash media, and a user configuration menu.
  Written by Eduardo using code from these sources.

  Arcada and MLX90640 libraries from adafruit.com

  Ver.  1 - Read temps, auto-range extremes, display gray squares on TFT
  Ver.  2 - Add Ironbow color palette, low+center+high markers
  Ver.  3 - Add crude BMP image write to SD
  Ver.  4 - Attach interrupts to improve button response
  Ver.  5 - Store BMPs to SD in an orderly manner, in folders
  Ver.  6 - Port to Teensy 3.2, where the libraries used are suited
  Ver.  7 - Port to Adafruit PyBadge using Arcada library.  Use simulated data while awaiting hardware release
  Ver.  8 - Convert menu to scrolling style and add settings for emissivity and frame rate, more if feasible.
  Ver.  9 - Bring in the current Adafruit library and read a real sensor.
*/

#include <Adafruit_MLX90640.h>
#include "Adafruit_Arcada.h"
Adafruit_MLX90640 mlx;
Adafruit_Arcada arcada;

#if !defined(USE_TINYUSB)
  #warning "Compile with TinyUSB selected!"
#endif

File myFile;

float mlx90640To[768];   // Here we receive the float vals acquired from MLX90640

#define DE_BOUNCE 200
  // Wait this many msec between button clicks
#define MENU_LEN 12
  // Number of total available menu choices
#define MENU_ROWS 9
  // Number of menu lines that can fit on screen
#define MENU_VPOS 6
#define GRAY_33 0x528A
#define BOTTOM_DIR "MLX90640"
#define DIR_FORMAT "/dir%05d"
#define BMP_FORMAT "/frm%05d.bmp"
#define CFG_FLNAME "/config.ini"
#define MAX_SERIAL 999

// BMP File Header, little end first, Photoshop ver.
const PROGMEM uint8_t BmpPSPHead[14] = {
 0x42, 0x4D,             // "BM" in hex
 0x38, 0x09, 0x00, 0x00, // File size, 2360
 0x00, 0x00,             // reserved for app data 1
 0x00, 0x00,             // reserved for app data 2
 0x36, 0x00, 0x00, 0x00  // Offset of first pixel, 54
};

// BMP 24-bit DIB Header, little end first, Photoshop ver.
const PROGMEM uint8_t DIBHeadPSP1[40] = {
 0x28, 0x00, 0x00, 0x00,  // Header size, 40
 0x20, 0x00, 0x00, 0x00,  // pixel width, 32
 0x18, 0x00, 0x00, 0x00,  // pixel height, 24
 0x01, 0x00,              // color planes, 1
 0x18, 0x00,              // bits per pixel, 24
 0x00, 0x00, 0x00, 0x00,  // Compression method, 0==none
 0x00, 0x00, 0x00, 0x00,  // Raw bitmap data size, dummy 0
 0x12, 0x0B, 0x00, 0x00,  // Pixels per meter H, 2834
 0x12, 0x0B, 0x00, 0x00,  // Pixels per meter V, 2834
 0x00, 0x00, 0x00, 0x00,  // Colors in palette, 0==default 2^n
 0x00, 0x00, 0x00, 0x00   // Number of important colors, 0
};

// BMP file data, 2 byte padding
const PROGMEM uint8_t PSPpad[2] = {0x00, 0x00};

//Byte arrays of bitmapped icons, 16 x 12 px:
const PROGMEM uint8_t battIcon[] = {
0x0f, 0x00, 0x3f, 0xc0, 0x20, 0x40, 0x20, 0x40, 0x20, 0x40, 0x20, 0x40, 
0x20, 0x40, 0x20, 0x40, 0x20, 0x40, 0x20, 0x40, 0x20, 0x40, 0x3f, 0xc0};

const PROGMEM uint8_t camIcon[] = {
0x01, 0xe0, 0x61, 0x20, 0xff, 0xf0, 0x80, 0x10, 0x86, 0x10, 0x89, 0x10, 
0x90, 0x90, 0x90, 0x90, 0x89, 0x10, 0x86, 0x10, 0x80, 0x10, 0xff, 0xf0};

const PROGMEM uint8_t SDicon[] = {
0x0f, 0xe0, 0x1f, 0xe0, 0x3c, 0x60, 0x78, 0x60, 0x70, 0x60, 0x60, 0x60, 
0x60, 0x60, 0x60, 0x60, 0x6f, 0x60, 0x60, 0x60, 0x7f, 0xe0, 0x7f, 0xe0};

const PROGMEM uint8_t snowIcon[] = {
0x15, 0x00, 0x4E, 0x40, 0xC4, 0x60, 0x75, 0xC0, 0x9F, 0x20, 0x0E, 0x00,
0x0E, 0x00, 0x9F, 0x20, 0x75, 0xC0, 0xC4, 0x60, 0x4E, 0x40, 0x15, 0x00};

uint8_t pixelArray[2304];   // BMP image body, 32 pixels * 24 rows * 3 bytes

// Some global values that several functions will use, including
// 5 floats to append to the BMP pixel data:
// coldest pixel, coldest color, center temp, hottest color, hottest pixel
float sneakFloats[5] = {3.1415926, 0.0, -11.7, 98.6, -12.34};      // Test values that get overwritten
uint16_t highAddr = 0, lowAddr = 0;                                // Append the pixel addresses, too

uint16_t backColor, lowPixel, highPixel, buttonRfunc = 1,
         emissivity = 95, frameRate = 4,
         thermRange = 0, paletteNum = 1, colorPal[256],            // Array for color palettes
         nextDirIndex = 0, nextBMPindex = 0, nextBMPsequence = 1;  // These keep count of SD files and dirs, 0==error
uint32_t deBounce = 0, buttonBits = 0;
boolean mirrorFlag = false, celsiusFlag = false, markersOn = true,
        screenDim = false, smoothing = false, showLastCap = false,
        save1frame = false, recordingInProg = false, buttonActive = false;
float battAverage = 0.0, colorLow = 0.0, colorHigh = 100.0;        // Values for managing color range
volatile boolean clickFlagMenu = false, clickFlagSelect = false;   // Volatiles for timer callback handling

void setup()
{
  if (!arcada.arcadaBegin()) {    // Start TFT and fill with black
    // Serial.print("Failed to begin");
    while (1);
  }
  arcada.filesysBeginMSD();       // Set up SD or QSPI flash as an external USB drive

  arcada.displayBegin();              // Activate TFT screen
  arcada.display->setRotation(1);     // wide orientation
  arcada.display->setTextWrap(false);
  arcada.setBacklight(255);           // Turn on backlight
  battAverage = arcada.readBatterySensor();

  Serial.begin(115200);
//  while(!Serial); // Wait for user to open terminal
  Serial.println("MLX90640 IR Array Example");

  if(arcada.filesysBegin()){              // Initialize flash storage, begin setting up indices for saving BMPs
    if(!arcada.exists(BOTTOM_DIR)) {      // Is base "MLX90640" directory absent?
      if(arcada.mkdir(BOTTOM_DIR))        // Can it be added?
        nextDirIndex = nextBMPindex = 1;  // Success, prepare to store numbered files & dirs
    } else {      // "MLX90640" directory exists, can we add files | directories?
      // Get the number of the next unused serial directory path
      nextDirIndex = availableFileNumber(1, BOTTOM_DIR + String(DIR_FORMAT));
      // and the next unused serial BMP name
      nextBMPindex = availableFileNumber(1, BOTTOM_DIR + String(BMP_FORMAT));
    }
  }  // By now each global index variable is either 0 (no nums available), or the next unclaimed serial num

  if(!mlx.begin(MLX90640_I2CADDR_DEFAULT, &Wire)) {
    Serial.println("MLX90640 not found!");
    arcada.haltBox("MLX90640 not found!");
    while(1)
      delay(10);  // Halt here
  }
  Serial.println("Found Adafruit MLX90640");

  Serial.print("Serial number: ");
  Serial.print(mlx.serialNumber[0], HEX);
  Serial.print(mlx.serialNumber[1], HEX);
  Serial.println(mlx.serialNumber[2], HEX);

  //mlx.setMode(MLX90640_INTERLEAVED);
  mlx.setMode(MLX90640_CHESS);
  mlx.setResolution(MLX90640_ADC_18BIT);

  switch(frameRate) {
    case 0: mlx.setRefreshRate(MLX90640_0_5_HZ); break; // 6 frame rates, 0.5 to 16 FPS in powers of 2
    case 1: mlx.setRefreshRate(MLX90640_1_HZ); break;
    case 2: mlx.setRefreshRate(MLX90640_2_HZ); break;
    case 3: mlx.setRefreshRate(MLX90640_4_HZ); break;
    case 4: mlx.setRefreshRate(MLX90640_8_HZ); break;
    default: mlx.setRefreshRate(MLX90640_16_HZ); break;
  }
  Wire.setClock(1000000); // max 1 MHz

  for(int counter01 = 0; counter01 < 2304; ++counter01)
    pixelArray[counter01] = counter01 / 9;  // Initialize BMP pixel buffer with a gradient

  loadPalette(paletteNum);             // Load false color palette
  backColor = GRAY_33;                 // 33% gray for BG
  setBackdrop(backColor, buttonRfunc); // Current BG, current button labels

  arcada.timerCallback(50, buttonCatcher);  // Assign a 50Hz callback function to catch button presses
}

void loop()
{
  static uint32_t frameCounter = 0;
  float scaledPix, highPix, lowPix;
  uint16_t markColor;

// Show the battery level indicator, 3.7V to 3.3V represented by a 7 segment bar
  battAverage = battAverage * 0.95 + arcada.readBatterySensor() * 0.05; // *Gradually* track battery level
  highPix = (int)constrain((battAverage - 3.3) * 15.0, 0.0, 6.0) + 1;   // Scale it to a 7-segment bar
  markColor = highPix > 2 ? 0x07E0 : 0xFFE0;                            // Is the battery level bar green or yellow?
  markColor = highPix > 1 ? markColor : 0xF800;                         // ...or even red?
  arcada.display->fillRect(146, 2, 12, 12, backColor);                  // Erase old battery icon
  arcada.display->drawBitmap(146, 2, battIcon, 16, 12, 0xC618);         // Redraw gray battery icon
  arcada.display->fillRect(150, 12 - highPix, 4, highPix, markColor);   // Add the level bar

// Fetch 768 fresh temperature values from the MLX90640
  arcada.display->drawBitmap(146, 18, camIcon, 16, 12, 0xF400); // Show orange camera icon during I2C acquisition
  if(mlx.getFrame(mlx90640To) != 0) {
    Serial.println("Failed");
    return;
  }
  arcada.display->fillRect(146, 18, 12, 12, backColor);         // Acquisition done, erase camera icon

// First pass: Find hottest and coldest pixels
  highAddr = lowAddr = 0;
  highPix  = lowPix  = mlx90640To[highAddr];

  for (int x = 1 ; x < 768 ; x++) { // Compare every pixel
    if(mlx90640To[x] > highPix) {   // Hotter pixel found?
      highPix = mlx90640To[x];      // Record its values
      highAddr = x;
    }
    if(mlx90640To[x] < lowPix) {    // Colder pixel found?
      lowPix = mlx90640To[x];       // Likewise
      lowAddr = x;
    }
  }
  if(thermRange == 0) {    // Are the colors set to auto-range?
    colorLow = lowPix;     // Then high and low color values get updated
    colorHigh = highPix;
  }
  sneakFloats[0] = lowPix;     // Retain these five temperature values
  sneakFloats[1] = colorLow;   // to append to the BMP file, if any
  sneakFloats[2] = mlx90640To[400];
  sneakFloats[3] = colorHigh;
  sneakFloats[4] = highPix;

// Second pass: Scale the float values down to 8-bit and plot colormapped pixels
  if(mirrorFlag) {                 // Mirrored display (selfie mode)?
    for(int y = 0; y < 24; ++y) {  // Rows count from bottom up
      for(int x = 0 ; x < 32 ; x++) {
        scaledPix = constrain((mlx90640To[32 * y + x] - colorLow) / (colorHigh - colorLow) * 255.9, 0.0, 255.0);
        pixelArray[3 * (32 * y + x)] = (uint8_t)scaledPix;                           // Store as a byte in BMP buffer
        arcada.display->fillRect(140 - x * 4, 92 - y * 4, 4, 4, colorPal[(uint16_t)scaledPix]);  // Filled rectangles, bottom up
      }
    }
  } else {  // Not mirrored
    for(int y = 0; y < 24; ++y) {
      for(int x = 0 ; x < 32 ; x++) {
        scaledPix = constrain((mlx90640To[32 * y + x] - colorLow) / (colorHigh - colorLow) * 255.9, 0.0, 255.0);
        pixelArray[3 * (32 * y + x)] = (uint8_t)scaledPix;
        arcada.display->fillRect(16 + x * 4, 92 - y * 4, 4, 4, colorPal[(uint16_t)scaledPix]);
      }
    }
  }

// Post pass: Screen print the lowest, center, and highest temperatures
  arcada.display->fillRect(  0, 96, 53, 12, colorPal[0]);                  // Contrasting mini BGs for cold temp
  arcada.display->fillRect(107, 96, 53, 12, colorPal[255]);                // and for hot temperature texts
  scaledPix = constrain((mlx90640To[400] - colorLow) / (colorHigh - colorLow) * 255.9, 0.0, 255.0);
  arcada.display->fillRect(53, 96, 54, 12, colorPal[(uint16_t)scaledPix]); // Color coded mini BG for center temp

  arcada.display->setTextSize(1);
  arcada.display->setCursor(10, 99);
  arcada.display->setTextColor(0xFFFF ^ colorPal[0]);   // Contrasting text color for coldest value
  arcada.display->print(celsiusFlag ? lowPix : lowPix * 1.8 + 32.0);  // Print Celsius or Fahrenheit

  arcada.display->setCursor(120, 99);
  arcada.display->setTextColor(0xFFFF ^ colorPal[255]); // Contrast text for hottest value
  arcada.display->print(celsiusFlag ? highPix : highPix * 1.8 + 32.0);  // Print Celsius or Fahrenheit

  arcada.display->setCursor(65, 99);
  if((mlx90640To[400] < (colorLow + colorHigh) * 0.5) == (paletteNum < 3))
    arcada.display->setTextColor(0xFFFF);               // A contrasting text color for center temp
  else
    arcada.display->setTextColor(0x0000);
  arcada.display->print(celsiusFlag ? mlx90640To[400] : mlx90640To[400] * 1.8 + 32.0);  // Pixel 12 * 32 + 16

  markColor = 0x0600;    // Deep green color to draw onscreen cross markers
  if(markersOn) {        // Show markers?
    if(mirrorFlag) {     // ...over a mirrored display?
      arcada.display->drawFastHLine(156 - (( lowAddr % 32) * 4 + 16), 93 - 4 * ( lowAddr / 32), 4, markColor); // Color crosses mark cold pixel,
      arcada.display->drawFastVLine(159 - (( lowAddr % 32) * 4 + 17), 92 - 4 * ( lowAddr / 32), 4, markColor);
      arcada.display->drawFastHLine(156 - ((highAddr % 32) * 4 + 16), 93 - 4 * (highAddr / 32), 4, markColor); // hot pixel,
      arcada.display->drawFastVLine(159 - ((highAddr % 32) * 4 + 17), 92 - 4 * (highAddr / 32), 4, markColor);
      arcada.display->drawFastHLine(76, 45, 4, markColor);                                                     // and center pixel
      arcada.display->drawFastVLine(78, 44, 4, markColor);
    } else {             // Not mirrored
      arcada.display->drawFastHLine(( lowAddr % 32) * 4 + 16, 93 - 4 * ( lowAddr / 32), 4, markColor); // Color crosses mark cold pixel,
      arcada.display->drawFastVLine(( lowAddr % 32) * 4 + 17, 92 - 4 * ( lowAddr / 32), 4, markColor);
      arcada.display->drawFastHLine((highAddr % 32) * 4 + 16, 93 - 4 * (highAddr / 32), 4, markColor); // hot pixel,
      arcada.display->drawFastVLine((highAddr % 32) * 4 + 17, 92 - 4 * (highAddr / 32), 4, markColor);
      arcada.display->drawFastHLine(80, 45, 4, markColor);                                             // and center pixel
      arcada.display->drawFastVLine(81, 44, 4, markColor);
    }
  }

// Print the frame count on the left sidebar
  arcada.display->setRotation(0);    // Vertical printing
  arcada.display->setCursor(48, 4);
  arcada.display->setTextColor(0xFFFF, backColor); // White text, current BG
  arcada.display->print("FRM ");
  arcada.display->print(++frameCounter);
  arcada.display->setRotation(1);    // Back to horizontal

// Handle any button presses
  if(!buttonActive && clickFlagMenu) {         // Was B:MENU button pressed?
    buttonActive = true;                       // Set button flag
    deBounce = millis() + DE_BOUNCE;           // and start debounce timer
    menuLoop(backColor);                       // Execute menu routine until finished
    clickFlagSelect = recordingInProg = false; // Clear unneeded flags
    nextBMPsequence = 1;
    setBackdrop(backColor, buttonRfunc);       // Repaint current BG & button labels
  }

  if(!buttonActive && clickFlagSelect) { // Was the A button pressed?
    buttonActive = true;                 // Set button flag
    deBounce = millis() + DE_BOUNCE;     // and start debounce timer

    if(buttonRfunc == 0) {                                           // Freeze requested?
      arcada.display->drawBitmap(146, 48, snowIcon, 16, 12, 0xC61F); // Freeze icon on
      while(buttonBits & ARCADA_BUTTONMASK_A)                        // Naive freeze: loop until button released
        delay(10);                                                   // Short pause
      deBounce = millis() + DE_BOUNCE;                               // Restart debounce timer
      arcada.display->fillRect(146, 48, 12, 12, backColor);          // Freeze icon off
    } else if(buttonRfunc == 1) {                         // Capture requested?
      if((nextBMPindex = availableFileNumber(nextBMPindex, BOTTOM_DIR + String(BMP_FORMAT))) != 0) { // Serialized BMP filename available?
        save1frame = true;                                // Set the flag to save a BMP
        arcada.display->fillRect(0, 96, 160, 12, 0x0600); // Display a green strip
        arcada.display->setTextColor(0xFFFF);             // with white capture message text
        arcada.display->setCursor(16, 99);
        arcada.display->print("Saving frame ");
        arcada.display->print(nextBMPindex);
      }
    } else {                            // Begin or halt recording a sequence of BMP files
      if(!recordingInProg) {            // "A:START RECORDING" was pressed
        if((nextDirIndex = availableFileNumber(nextDirIndex, BOTTOM_DIR + String(DIR_FORMAT))) != 0) { // Serialized directory name available?
          // Make the directory
          if(newDirectory()) {          // Success in making a new sequence directory?
            recordingInProg = true;     // Set the flag for saving BMP files
            nextBMPsequence = 1;        // ...numbered starting with 00001
            setBackdrop(backColor, 3);  // Show "A:STOP RECORDING" label
          } else                        // Couldn't make the new directory, so
            nextDirIndex = 0;           // disable further sequences
        }
      } else {                          // "A:STOP RECORDING" was pressed
        recordingInProg = false;
        setBackdrop(backColor, 2);      // Clear "A:STOP RECORDING" label
      }
    }
  }

// Saving any BMP images to flash media happens here
  if(save1frame || recordingInProg) {      // Write a BMP file to SD?
    arcada.display->drawBitmap(146, 32, SDicon, 16, 12, 0x07E0); // Flash storage activity icon on

    prepForSave();                         // Save to flash.  Use global values for parameters
    nextBMPsequence += recordingInProg ? 1 : 0;  // If recording a series, increment frame count
    save1frame = false;                    // If one frame saved, clear the flag afterwards

    arcada.display->fillRect(146, 32, 12, 12, backColor);        // Flash storage activity icon off
  }

  if(showLastCap) {                      // Redisplay the last BMP saved?
    buttonActive = true;                 // Set button flag
    deBounce = millis() + DE_BOUNCE;     // and start debounce timer
    recallLastBMP(backColor);            // Redisplay last bitmap from buffer until finished
    setBackdrop(backColor, buttonRfunc); // Repaint current BG & button labels
    showLastCap = false;
  }

// Here we protect against button bounces while the function loops
  if(buttonActive && millis() > deBounce && (buttonBits
     & (ARCADA_BUTTONMASK_B | ARCADA_BUTTONMASK_A)) == 0)  // Has de-bounce wait expired & all buttons released?
    buttonActive = false;                // Clear flag to allow another button press

  clickFlagMenu = clickFlagSelect = false; // End of the loop, clear all interrupt flags
}

// Compute and fill an array with 256 16-bit color values
void loadPalette(uint16_t palNumber) {
  uint16_t x, y;
  float fleX, fleK;

  switch(palNumber) {
    case 1:  // Compute ironbow palette
      for(x = 0; x < 256; ++x) {
        fleX = (float)x / 255.0;

        // fleK = 65535.9 * (1.02 - (fleX - 0.72) * (fleX - 0.72) * 1.96);
        // fleK = (fleK > 65535.0) || (fleX > 0.75) ? 65535.0 : fleK;  // Truncate red curve
        fleK = 63487.0 * (1.02 - (fleX - 0.72) * (fleX - 0.72) * 1.96);
        fleK = (fleK > 63487.0) || (fleX > 0.75) ? 63487.0 : fleK;  // Truncate red curve
        colorPal[x] = (uint16_t)fleK & 0xF800;                      // Top 5 bits define red

        // fleK = fleX * fleX * 2047.9;
        fleK = fleX * fleX * 2015.0;
        colorPal[x] += (uint16_t)fleK & 0x07E0;  // Middle 6 bits define green

        // fleK = 31.9 * (14.0 * (fleX * fleX * fleX) - 20.0 * (fleX * fleX) + 7.0 * fleX);
        fleK = 30.9 * (14.0 * (fleX * fleX * fleX) - 20.0 * (fleX * fleX) + 7.0 * fleX);
        fleK = fleK < 0.0 ? 0.0 : fleK;          // Truncate blue curve
        colorPal[x] += (uint16_t)fleK & 0x001F;  // Bottom 5 bits define blue
      }
      break;
    case 2:  // Compute quadratic "firebow" palette
      for(x = 0; x < 256; ++x) {
        fleX = (float)x / 255.0;

        // fleK = 65535.9 * (1.00 - (fleX - 1.0) * (fleX - 1.0));
        fleK = 63487.0 * (1.00 - (fleX - 1.0) * (fleX - 1.0));
        colorPal[x] = (uint16_t)fleK & 0xF800;                      // Top 5 bits define red

        // fleK = fleX < 0.25 ? 0.0 : (fleX - 0.25) * 1.3333 * 2047.9;
        fleK = fleX < 0.25 ? 0.0 : (fleX - 0.25) * 1.3333 * 2015.0;
        colorPal[x] += (uint16_t)fleK & 0x07E0;  // Middle 6 bits define green

        // fleK = fleX < 0.5 ? 0.0 : (fleX - 0.5) * (fleX - 0.5) * 127.9;
        fleK = fleX < 0.5 ? 0.0 : (fleX - 0.5) * (fleX - 0.5) * 123.0;
        colorPal[x] += (uint16_t)fleK & 0x001F;  // Bottom 5 bits define blue
      }
      break;
    case 3:  // Compute "alarm" palette
      for(x = 0; x < 256; ++x) {
        fleX = (float)x / 255.0;

        fleK = 65535.9 * (fleX < 0.875 ? 1.00 - (fleX * 1.1428) : 1.0);
        colorPal[x] = (uint16_t)fleK & 0xF800;                      // Top 5 bits define red

        fleK = 2047.9 * (fleX < 0.875 ? 1.00 - (fleX * 1.1428) : (fleX - 0.875) * 8.0);
        colorPal[x] += (uint16_t)fleK & 0x07E0;  // Middle 6 bits define green

        fleK = 31.9 * (fleX < 0.875 ? 1.00 - (fleX * 1.1428) : 0.0);
        colorPal[x] += (uint16_t)fleK & 0x001F;  // Bottom 5 bits define blue
      }
      break;
    case 4:  // Compute negative gray palette, black hot
      for(x = 0; x < 256; ++x)
        colorPal[255 - x] = (((uint16_t)x << 8) & 0xF800) + (((uint16_t)x << 3) & 0x07E0) + (((uint16_t)x >> 3) & 0x001F);
      break;
    default:  // Compute gray palette, white hot
      for(x = 0; x < 256; ++x)
        colorPal[x] = (((uint16_t)x << 8) & 0xF800) + (((uint16_t)x << 3) & 0x07E0) + (((uint16_t)x >> 3) & 0x001F);
      break;
  }
}

void setColorRange(int presetIndex) { // Set coldest/hottest values in color range
  switch(presetIndex) {
    case 1:  // Standard range, from FLIR document: 50F to 90F
      colorLow = 10.0;
      colorHigh = 32.22;
      break;
    case 2:  // Cool/warm range, for detecting mammals outdoors
      colorLow = 5.0;
      colorHigh = 32.0;
      break;
    case 3:  // Warm/warmer range, for detecting mammals indoors
      colorLow = 20.0;
      colorHigh = 32.0;
      break;
    case 4:  // Hot spots, is anything hotter than it ought to be?
      colorLow = 20.0;
      colorHigh = 50.0;
      break;
    case 5:  // Fire & ice, extreme temperatures only!
      colorLow = -10.0;
      colorHigh = 200.0;
      break;
    default:  // Default is autorange, so these values will change with every frame
      colorLow = 0.0;
      colorHigh = 100.0;
      break;
  }
}

// Draw the stationary screen elements behind the live camera window
void setBackdrop(uint16_t bgColor, uint16_t buttonFunc) {
  arcada.display->fillScreen(bgColor);

  for(int x = 0; x < 160; ++x)   // Paint current palette across bottom
    arcada.display->drawFastVLine(x, 110, 6, colorPal[map(x, 0, 159, 0, 255)]);

  arcada.display->setCursor(16, 120);
  arcada.display->setTextColor(0xFFFF, bgColor);    // White text, current BG for button labels
  switch(buttonFunc) {
    case 0:
      arcada.display->print("B:MENU        A:FREEZE");
      break;
    case 1:
      arcada.display->print("B:MENU       ");
      if(nextBMPindex == 0)                         // No room to store a BMP in flash media?
        arcada.display->setTextColor(GRAY_33 >> 1); // Grayed button label
      arcada.display->print("A:CAPTURE");
      break;
    case 2:
      arcada.display->print("B:MENU    ");
      if(nextDirIndex == 0)                         // Has flash storage no room for a new directory?
        arcada.display->setTextColor(GRAY_33 >> 1); // Grayed button label
      arcada.display->print("A:START RECORD");
      break;
    case 3:
      arcada.display->print("B:MENU    ");
      arcada.display->setTextColor(0xFFFF, 0xF800);  // White text, red BG recording indicator
      arcada.display->print("A:STOP RECORD");
      break;
    case 4:
      arcada.display->print("               A:EXIT"); // Use for bitmap redisplay only
      break;
  }
}

void prepForSave() {
  for(int x = 0; x < 768; ++x)
    pixelArray[3 * x + 2] = pixelArray[3 * x + 1] = pixelArray[3 * x];  // Copy each blue byte into R & G for 256 grays in 24 bits

  if(!writeBMP()) {                                      // Did BMP write to flash fail?
    arcada.display->fillRect(0, 96, 160, 12, 0xF800);    // Red error signal
    arcada.display->setTextColor(0xFFFF);                // with white text
    arcada.display->setCursor(20, 99);
    arcada.display->print("Storage error!");
  }
}

boolean newDirectory() { // Create a subdirectory, converting the name between char arrays and string objects
  char fileArray[64];
  String fullPath;

  sprintf(fileArray, DIR_FORMAT, nextDirIndex); // Generate subdirectory name
  fullPath = BOTTOM_DIR + String(fileArray);    // Make a filepath out of it, then
  return arcada.mkdir(fullPath.c_str());        // try to make a real subdirectory from it
}

// Here we write the actual bytes of a BMP file (plus extras) to flash media
boolean writeBMP() {
  uint16_t counter1, shiftedFloats[14]; // A buffer for the appended floats and uint16_t's
  uint32_t timeStamp;
  float shiftAssist;
  char fileArray[64];
  String fullPath;

// First, figure out a name and path for our new BMP
  fullPath = BOTTOM_DIR;                              // Build a filepath starting with the base subdirectory
  if(buttonRfunc == 2) {                              // BMP sequence recording in progress?
    sprintf(fileArray, DIR_FORMAT, nextDirIndex);     // Generate subdirectory name
    fullPath += String(fileArray);                    // Add it to the path
    sprintf(fileArray, BMP_FORMAT, nextBMPsequence);  // Generate a sequential filename
    fullPath += String(fileArray);                    // Complete the filepath string
  } else {                                            // Not a sequence, solitary BMP file
    sprintf(fileArray, BMP_FORMAT, nextBMPindex);     // Generate a serial filename
    fullPath += String(fileArray);                    // Complete the filepath string
  }

  myFile = arcada.open(fullPath.c_str(), FILE_WRITE); // Only one file can be open at a time

  if(myFile) {                      // If the file opened okay, write to it:
    myFile.write(BmpPSPHead, 14);   // BMP header 1
    myFile.write(DIBHeadPSP1, 40);  // BMP header 2
    myFile.write(pixelArray, 2304); // Array of 768 BGR byte triples
    myFile.write(PSPpad, 2);        // Pad with 2 zeros 'cause Photoshop does it.

    // My BMP hack - append 5 fixed-point temperature values as 40 extra bytes
    for(counter1 = 0; counter1 < 5; ++counter1) {    // Shift 5 floats
      shiftAssist = sneakFloats[counter1] + 1000.0;  // Offset MLX90640 temps to positive
      shiftedFloats[counter1 * 2] = (uint16_t)shiftAssist;
      shiftAssist = (shiftAssist - (float)shiftedFloats[counter1 * 2]) * 49152.0; // Scale up fraction
      shiftedFloats[counter1 * 2 + 1] = (uint16_t)shiftAssist;
    }

    shiftedFloats[10] = lowAddr;   // Two more appended numbers, the 2 extreme pixel addresses
    shiftedFloats[11] = highAddr;

    timeStamp = millis();         // Recycle this variable to append a time stamp
    lowAddr = timeStamp & 0xFFFF;
    highAddr = timeStamp >> 16;
    shiftedFloats[12] = lowAddr;
    shiftedFloats[13] = highAddr;

    myFile.write(shiftedFloats, 28);  // Write appended uint16_t's

    myFile.close();
    return true;
  } else {          // The file didn't open, return error
    return false;
  }
}

void recallLastBMP(uint16_t bgColor) {  // Display 8-bit values left in buffer from the last BMP save
  int counter1, counter2;
  boolean exitFlag = false;

  setBackdrop(bgColor, 4);  // Clear screen, just a color palette & "A:EXIT" in the BG

  for(int counter1 = 0; counter1 < 24; ++counter1) {  // Redraw using leftover red byte values, not yet overwritten
    for(int counter2 = 0 ; counter2 < 32 ; ++counter2) {
      arcada.display->fillRect(16 + counter2 * 4, 92 - counter1 * 4, 4, 4,
                   colorPal[(uint16_t)pixelArray[3 * (32 * counter1 + counter2) + 2]]);
    }
  }

  while(!exitFlag) {  // Loop here until exit button
    if(!buttonActive && (buttonBits & ARCADA_BUTTONMASK_A)) { // "A:EXIT" button freshly pressed?
      exitFlag = true;
      buttonActive = true;
      deBounce = millis() + DE_BOUNCE;
    }

    if(buttonActive && millis() > deBounce
       && (buttonBits & (ARCADA_BUTTONMASK_A | ARCADA_BUTTONMASK_B)) == 0)  // Has de-bounce wait expired & all buttons released?
      buttonActive = false;               // Clear flag to allow another button press
  }
}

uint16_t availableFileNumber(uint16_t startNumber, String formatBase) { // Find unclaimed serial number for file series
  uint16_t counter1;
  char nameArray[80];

  for(counter1 = startNumber; counter1 % MAX_SERIAL != 0; ++counter1) { // Start counting
    sprintf(nameArray, formatBase.c_str(), counter1);                   // Generate a serialized filename
    if(!arcada.exists(nameArray))                                       // If it doesn't already exist
      return counter1;                                                  // return the number as available
  }
  return 0; // Loop finished, no free number found, return fail
}

boolean menuLoop(uint16_t bgColor) {  // Lay out a menu screen, interact to change values
  int counter1 = 0, scrollPosition = 0;
  boolean exitFlag = false, settingsChanged = false;
  uint32_t menuButtons;

  arcada.display->fillScreen(bgColor);
  arcada.display->fillRect(0, 12 * (counter1 + scrollPosition) + MENU_VPOS - 2, 160, 12, 0x0000);  // Black stripe cursor on menu

  arcada.display->setTextColor(0xFFFF);             // White text
  arcada.display->setCursor(16, 120);               // at screen bottom
  arcada.display->print("B:ADVANCE     A:CHANGE");  // for button labels

  for(counter1 = 0; counter1 < MENU_ROWS; ++counter1) {  // Display menu texts
    menuLines(counter1, scrollPosition);
  }
  counter1 = 0;

  while(!exitFlag) { // Loop until exit is activated
    if(!buttonActive && (buttonBits & ARCADA_BUTTONMASK_B)) {  // Fresh press of B:ADVANCE button?
      buttonActive = true;                                     // Set button flag
      deBounce = millis() + DE_BOUNCE;                         // and start debounce timer.

      arcada.display->fillRect(0, 12 * (counter1 - scrollPosition) + MENU_VPOS - 2, 160, 12, bgColor); // Erase cursor & text
      menuLines(counter1, scrollPosition);                     // Refresh menu text line
      counter1 = (counter1 + 1) % MENU_LEN;                    // Advance menu counter

      if(counter1 == 0) {                                      // Have we cycled around to the menu top?
        scrollPosition = 0;
        for(int counter2 = 0; counter2 < MENU_ROWS; ++counter2) {  // Redisplay all menu texts
          arcada.display->fillRect(0, 12 * counter2 + MENU_VPOS - 2, 160, 12, bgColor); // Erase old text
          menuLines(counter2 + scrollPosition, scrollPosition);    // Redraw each text line
        }
      } else if((counter1 + 1 < MENU_LEN) && (counter1 - scrollPosition == MENU_ROWS - 1)) { // Should we scroll down 1 menu line?
        ++scrollPosition;
        for(int counter2 = 0; counter2 < MENU_ROWS; ++counter2) {  // Redisplay all menu texts
          arcada.display->fillRect(0, 12 * counter2 + MENU_VPOS - 2, 160, 12, bgColor); // Erase old text
          menuLines(counter2 + scrollPosition, scrollPosition);    // Redraw each text line
        }
      }

      arcada.display->fillRect(0, 12 * (counter1 - scrollPosition) + MENU_VPOS - 2, 160, 12, 0x0000);  // New black cursor
      menuLines(counter1, scrollPosition);                     // Refresh text line
      deBounce = millis() + DE_BOUNCE;                         // Restart debounce timer, just for safety
    }

    if(!buttonActive && (buttonBits & ARCADA_BUTTONMASK_A)) {  // Fresh press of A:CHANGE button?
      buttonActive = true;                                     // Set button flag
      deBounce = millis() + DE_BOUNCE;                         // and start debounce timer.

      switch(counter1) {       // Change whichever setting is currently hilighted
        case 0:
          showLastCap = true;  // Set flag to display the last frame captured to SD
          exitFlag = true;     // and exit
          break;
        case 1:
          celsiusFlag = !celsiusFlag; // Toggle Celsius/Fahrenheit
          break;
        case 2:
          buttonRfunc = (buttonRfunc + 1) % 3; // Step through button functions
          break;
        case 3:
          loadPalette(paletteNum = (paletteNum + 1) % 5); // Step through various color palettes
          break;
        case 4:
          thermRange = (thermRange + 1) % 6; // Step through various temp range presets
          break;
        case 5:
          markersOn = !markersOn; // Toggle hot/cold marker visibility
          break;
        case 6:
          mirrorFlag = !mirrorFlag; // Toggle mirrored display
          break;
        case 7:
          switch(frameRate = (frameRate + 1) % 6) {              // 6 frame rates, 0.5 to 16 in powers of 2
            case 0: mlx.setRefreshRate(MLX90640_0_5_HZ); break;
            case 1: mlx.setRefreshRate(MLX90640_1_HZ); break;
            case 2: mlx.setRefreshRate(MLX90640_2_HZ); break;
            case 3: mlx.setRefreshRate(MLX90640_4_HZ); break;
            case 4: mlx.setRefreshRate(MLX90640_8_HZ); break;
            default: mlx.setRefreshRate(MLX90640_16_HZ); break;
          }
          break;
        case 8:
          emissivity = (emissivity + 90) % 100; // Step from 95% to 5% by -10%
          break;
        case 9:
          smoothing = !smoothing; // Toggle pixel smoothing
          break;
        case 10:
          arcada.setBacklight((screenDim = !screenDim) ? 64 : 255); // Change backlight LED
          break;
        default:
          exitFlag = true;
          break;
      }
      if((counter1 > 0) && (counter1 < MENU_LEN - 1))    // Was any setting just changed?
        settingsChanged = true;

      arcada.display->fillRect(0, 12 * (counter1 - scrollPosition) + MENU_VPOS - 2, 160, 12, 0x0000); // Erase hilit menu line
      menuLines(counter1, scrollPosition);   // Retype hilit menu line
    }

    if(buttonActive && millis() > deBounce
       && (buttonBits & (ARCADA_BUTTONMASK_A | ARCADA_BUTTONMASK_B)) == 0)  // Has de-bounce wait expired & all buttons released?
      buttonActive = false;               // Clear flag to allow another button press
  }
  return(settingsChanged);
}

void menuLines(int lineNumber, int scrollPos) {  // Screen print a single line in the settings menu

  arcada.display->setTextColor(0xFFFF);               // White text
  arcada.display->setCursor(10, 12 * (lineNumber - scrollPos) + MENU_VPOS); // Menu lines 12 pixels apart

  if(lineNumber - scrollPos == 0 && scrollPos > 0) {  // Are any menu lines scrolled off screen top?
    arcada.display->print("           ^");            // Print a small up arrow indicator
  } else if(lineNumber - scrollPos == 8 && lineNumber + 1 < MENU_LEN) { // How about off the bottom?
    arcada.display->print("           v");            // Print a small down arrow indicator... yeah, it's a v
  } else {

    switch(lineNumber) {
      case 0:
        arcada.display->print("  Display last capture");
        break;
      case 1:
        arcada.display->print("     Scale - ");
        arcada.display->print(celsiusFlag ? "CELSIUS" : "FAHRENHEIT");
        break;
      case 2:
        arcada.display->print(" Rt button - ");
        switch(buttonRfunc) {
          case 1:
            arcada.display->print("CAPTURE"); break;
          case 2:
            arcada.display->print("RECORD"); break;
          default:
            arcada.display->print("FREEZE"); break;
        }
        break;
      case 3:
        arcada.display->print("   Palette - ");
        for(int xPos = 0; xPos < 72; ++xPos)   // Display the current heat spectrum colors
          arcada.display->drawFastVLine(xPos + 87, (lineNumber - scrollPos) * 12 + MENU_VPOS,
                                        8, colorPal[map(xPos, 0, 71, 0, 255)]);
        switch(paletteNum) {
          case 1:
            arcada.display->print("IRONBOW");
            break;
          case 2:
            arcada.display->print("FIREBOW");
            break;
          case 3:
            arcada.display->setTextColor(0x0000);    // Black text for reverse contrast
            arcada.display->print("ALARM");
            break;
          case 4:
            arcada.display->setTextColor(0x0000);    // Black text
            arcada.display->print("BLACK HOT");
            break;
          default:
            arcada.display->print("WHITE HOT");
            break;
        }
        break;
      case 4:
        arcada.display->print("Temp range - ");
        setColorRange(thermRange);
        switch(thermRange) {
          case 1:
            arcada.display->print("STANDARD"); break;
          case 2:
            arcada.display->print("COOL/WARM"); break;
          case 3:
            arcada.display->print("WARM/WARMER"); break;
          case 4:
            arcada.display->print("HOT SPOTS"); break;
          case 5:
            arcada.display->print("FIRE & ICE"); break;
          default:
            arcada.display->print("AUTO-RANGE"); break;
        }
        break;
      case 5:
        arcada.display->print("   Markers - ");
        arcada.display->print(markersOn ? "ON" : "OFF");
        break;
      case 6:
        arcada.display->print("     Image - ");
        arcada.display->print(mirrorFlag ? "MIRRORED" : "FORWARD");
        break;
      case 7:
        arcada.display->print("Frame rate - ");
        arcada.display->print((float)(1 << frameRate) * 0.5);
        arcada.display->print(" FPS");
        break;
      case 8:
        arcada.display->setTextColor(GRAY_33 << 1); // Grayed menu item
        arcada.display->print("Emissivity - ");
        arcada.display->print(emissivity);
        arcada.display->print("%");
        break;
      case 9:
        arcada.display->setTextColor(GRAY_33 << 1); // Grayed menu item
        arcada.display->print(" Smoothing - ");
        arcada.display->print(smoothing ? "ON" : "OFF");
        break;
      case 10:
        arcada.display->print(" Backlight - ");
        arcada.display->print(screenDim ? "DIM" : "FULL");
        break;
      case 11:
        arcada.display->print("       Exit menu");
    }
  }
}

// This is the function that substitutes for GPIO external interrupts
// It will check for A and B button presses at 50Hz
void buttonCatcher(void) {
  buttonBits = arcada.readButtons();
  clickFlagMenu |= (buttonBits & ARCADA_BUTTONMASK_B) != 0;
  clickFlagSelect |= (buttonBits & ARCADA_BUTTONMASK_A) != 0;
}