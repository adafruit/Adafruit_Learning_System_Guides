// SPDX-FileCopyrightText: 2023 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*******************************************************************************
 * Motion JPEG Image Viewer
 * This is a simple Motion JPEG image viewer example

encode with
ffmpeg -i "wash.mp4" -vf "fps=10,vflip,hflip,scale=-1:480:flags=lanczos,crop=480:480" -pix_fmt yuvj420p -q:v 9 wash.mjpeg

 ******************************************************************************/
#define MJPEG_FOLDER       "/videos" // cannot be root!
#define MJPEG_OUTPUT_SIZE  (480 * 480 * 2)      // memory for a output image frame
#define MJPEG_BUFFER_SIZE (MJPEG_OUTPUT_SIZE / 5) // memory for a single JPEG frame
#define MJPEG_LOOPS        0

#include <Arduino_GFX_Library.h>
#include <Adafruit_CST8XX.h>
//#include <SD.h>      // uncomment either SD or SD_MMC
#include <SD_MMC.h>

Arduino_XCA9554SWSPI *expander = new Arduino_XCA9554SWSPI(
    PCA_TFT_RESET, PCA_TFT_CS, PCA_TFT_SCK, PCA_TFT_MOSI,
    &Wire, 0x3F);
    
Arduino_ESP32RGBPanel *rgbpanel = new Arduino_ESP32RGBPanel(
    TFT_DE, TFT_VSYNC, TFT_HSYNC, TFT_PCLK,
    TFT_R1, TFT_R2, TFT_R3, TFT_R4, TFT_R5,
    TFT_G0, TFT_G1, TFT_G2, TFT_G3, TFT_G4, TFT_G5,
    TFT_B1, TFT_B2, TFT_B3, TFT_B4, TFT_B5,
    1 /* hsync_polarity */, 50 /* hsync_front_porch */, 2 /* hsync_pulse_width */, 44 /* hsync_back_porch */,
    1 /* vsync_polarity */, 16 /* vsync_front_porch */, 2 /* vsync_pulse_width */, 18 /* vsync_back_porch */
    //,1, 30000000
    );

Arduino_RGB_Display *gfx = new Arduino_RGB_Display(
// 2.1" 480x480 round display
    480 /* width */, 480 /* height */, rgbpanel, 0 /* rotation */, true /* auto_flush */,
    expander, GFX_NOT_DEFINED /* RST */, TL021WVC02_init_operations, sizeof(TL021WVC02_init_operations));

Adafruit_CST8XX ctp = Adafruit_CST8XX();  // This library also supports FT6336U!
#define I2C_TOUCH_ADDR 0x15
bool touchOK = false;

#include <SD_MMC.h>

#include "MjpegClass.h"
static MjpegClass mjpeg;
File mjpegFile, video_dir;
uint8_t *mjpeg_buf;
uint16_t *output_buf;

unsigned long total_show_video = 0;

void setup()
{
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  //while(!Serial) delay(10);
  Serial.println("MJPEG Video Playback Demo");

#ifdef GFX_EXTRA_PRE_INIT
  GFX_EXTRA_PRE_INIT();
#endif

  // Init Display
  Wire.setClock(400000); // speed up I2C 
  if (!gfx->begin()) {
    Serial.println("gfx->begin() failed!");
  }
  gfx->fillScreen(BLUE);

  expander->pinMode(PCA_TFT_BACKLIGHT, OUTPUT);
  expander->digitalWrite(PCA_TFT_BACKLIGHT, HIGH);

  //while (!SD.begin(ss, SPI, 64000000UL))
  //SD_MMC.setPins(SCK /* CLK */, MOSI /* CMD/MOSI */, MISO /* D0/MISO */);
  SD_MMC.setPins(SCK, MOSI /* CMD/MOSI */, MISO /* D0/MISO */, A0 /* D1 */, A1 /* D2 */, SS /* D3/CS */); // quad MMC!
  while (!SD_MMC.begin("/root", true))
  {
    Serial.println(F("ERROR: File System Mount Failed!"));
    gfx->println(F("ERROR: File System Mount Failed!"));
    delay(1000);
  }
  Serial.println("Found SD Card");

  //  open filesystem
  //video_dir = SD.open(MJPEG_FOLDER);
  video_dir = SD_MMC.open(MJPEG_FOLDER);
  if (!video_dir || !video_dir.isDirectory()){
     Serial.println("Failed to open " MJPEG_FOLDER " directory");
     while (1) delay(100);
  }
  Serial.println("Opened Dir");

  mjpeg_buf = (uint8_t *)malloc(MJPEG_BUFFER_SIZE);
  if (!mjpeg_buf) {
    Serial.println(F("mjpeg_buf malloc failed!"));
    while (1) delay(100);
  }
  Serial.println("Allocated decoding buffer");

  output_buf = (uint16_t *)heap_caps_aligned_alloc(16, MJPEG_OUTPUT_SIZE, MALLOC_CAP_8BIT);
  if (!output_buf) {
    Serial.println(F("output_buf malloc failed!"));
    while (1) delay(100);
  }

  expander->pinMode(PCA_BUTTON_UP, INPUT);
  expander->pinMode(PCA_BUTTON_DOWN, INPUT);

  if (!ctp.begin(&Wire, I2C_TOUCH_ADDR)) {
    Serial.println("No touchscreen found");
    touchOK = false;
  } else {
    Serial.println("Touchscreen found");
    touchOK = true;
  }
}

void loop()
{
  /* variables */
  int total_frames = 0;
  unsigned long total_read_video = 0;
  unsigned long total_decode_video = 0;
  unsigned long start_ms, curr_ms;
  uint8_t check_UI_count = 0;
  int16_t x = -1, y = -1, w = -1, h = -1;
  total_show_video = 0;

  if (mjpegFile) mjpegFile.close();
  Serial.println("looking for a file...");

  if (!video_dir || !video_dir.isDirectory()){
     Serial.println("Failed to open " MJPEG_FOLDER " directory");
     while (1) delay(100);
  }

  // look for first mjpeg file
  while ((mjpegFile = video_dir.openNextFile()) != 0) {
    if (!mjpegFile.isDirectory()) {
      Serial.print("  FILE: ");
      Serial.print(mjpegFile.name());
      Serial.print("  SIZE: ");
      Serial.println(mjpegFile.size());
      if ((strstr(mjpegFile.name(), ".mjpeg") != 0) || (strstr(mjpegFile.name(), ".MJPEG") != 0)) {
        Serial.println("   <---- found a video!");
        break;
      }
    }
    if (mjpegFile) mjpegFile.close();
  }

  if (!mjpegFile || mjpegFile.isDirectory())
  {
    Serial.println(F("ERROR: Failed to find a MJPEG file for reading, resetting..."));
    //gfx->println(F("ERROR: Failed to find a MJPEG file for reading"));

    // We kept getting hard crashes when trying to rewindDirectory or close/open dir
    // so we're just going to do a softreset
    esp_sleep_enable_timer_wakeup(1000);
    esp_deep_sleep_start(); 
  }

  bool done_looping = false;
  while (!done_looping) {
    mjpegFile.seek(0);
    total_frames = 0;
    total_read_video = 0;
    total_decode_video = 0;
    total_show_video = 0;

    Serial.println(F("MJPEG start"));
  
    start_ms = millis();
    curr_ms = millis();
    if (! mjpeg.setup(&mjpegFile, mjpeg_buf, output_buf, MJPEG_OUTPUT_SIZE, true /* useBigEndian */)) {
       Serial.println("mjpeg.setup() failed");
       while (1) delay(100);
    }
  
    while (mjpegFile.available() && mjpeg.readMjpegBuf())
    {
      // Read video
      total_read_video += millis() - curr_ms;
      curr_ms = millis();

      // Play video
      mjpeg.decodeJpg();
      total_decode_video += millis() - curr_ms;
      curr_ms = millis();

      if (x == -1) {
        w = mjpeg.getWidth();
        h = mjpeg.getHeight();
        x = (w > gfx->width()) ? 0 : ((gfx->width() - w) / 2);
        y = (h > gfx->height()) ? 0 : ((gfx->height() - h) / 2);
      }
      gfx->draw16bitBeRGBBitmap(x, y, output_buf, w, h);
      total_show_video += millis() - curr_ms;

      curr_ms = millis();
      total_frames++;
      check_UI_count++;
      if (check_UI_count >= 5) {
        check_UI_count = 0;
        Serial.print('.');
        
        if (! expander->digitalRead(PCA_BUTTON_DOWN)) {
          Serial.println("\nDown pressed");
          done_looping = true;
          while (! expander->digitalRead(PCA_BUTTON_DOWN)) delay(10);
          break;
        }
        if (! expander->digitalRead(PCA_BUTTON_UP)) {
          Serial.println("\nUp pressed");
          done_looping = true;
          while (! expander->digitalRead(PCA_BUTTON_UP)) delay(10);
          break;
        }
  
        if (touchOK && ctp.touched()) {
          CST_TS_Point p = ctp.getPoint(0);
          Serial.printf("(%d, %d)\n", p.x, p.y);
          done_looping = true;
          break;
        }
      }
    }
    int time_used = millis() - start_ms;
    Serial.println(F("MJPEG end"));
    
    float fps = 1000.0 * total_frames / time_used;
    total_decode_video -= total_show_video;
    Serial.printf("Total frames: %d\n", total_frames);
    Serial.printf("Time used: %d ms\n", time_used);
    Serial.printf("Average FPS: %0.1f\n", fps);
    Serial.printf("Read MJPEG: %lu ms (%0.1f %%)\n", total_read_video, 100.0 * total_read_video / time_used);
    Serial.printf("Decode video: %lu ms (%0.1f %%)\n", total_decode_video, 100.0 * total_decode_video / time_used);
    Serial.printf("Show video: %lu ms (%0.1f %%)\n", total_show_video, 100.0 * total_show_video / time_used);
  }
}
