// SPDX-FileCopyrightText: 2018 me-no-dev for Espressif Systems
//
// SPDX-License-Identifier: LGPL-2.1-only
//
// Modified by Brent Rubell for Adafruit Industries
#include "TJpg_Decoder.h"
#include "esp_camera.h"
#include "face_recognition_112_v1_s8.hpp"
#include "face_recognition_tool.hpp"
#include "fb_gfx.h"
#include "human_face_detect_mnp01.hpp"
#include "human_face_detect_msr01.hpp"
#include "ra_filter.h"
#include <Adafruit_GFX.h>
#include <Adafruit_NeoPixel.h>
#include <Adafruit_ST7789.h>
#include <SPI.h>
#include <WiFi.h>
#include <Wire.h>
#include <vector>

// The number of faces to save
// NOTE - these faces are saved to the ESP32's flash memory and survive between
// reboots
#define FACE_ID_SAVE_NUMBER 4

// Threshold (0.0 - 1.0) to determine whether the face detected is a positive
// match NOTE - This value is adjustable, you may "tune" it for either a more
// confident match
#define FR_CONFIDENCE_THRESHOLD 0.7

// True if you want to save faces to flash memory and load them on boot, False
// otherwise
#define SAVE_FACES_TO_FLASH false

// NeoPixel ring used to indicate face recognition status
#define PIXELS_PIN A1
#define NUMPIXELS 12
// NeoPixel brightness, from 0 to 225 (0% to 100%)
#define PIXEL_BRIGHTNESS 25
Adafruit_NeoPixel pixels(NUMPIXELS, PIXELS_PIN, NEO_GRB + NEO_KHZ800);

Adafruit_ST7789 tft =
    Adafruit_ST7789(TFT_CS, TFT_DC, TFT_RESET); ///< TFT display
/**************************************************************************/
/**
 * @brief Framebuffer class for PyCamera.
 *
 * @details This class extends GFXcanvas16 to provide a framebuffer for the
 * PyCamera.
 */
/**************************************************************************/
class PyCameraFB : public GFXcanvas16 {
public:
  /**************************************************************************/
  /**
   * @brief Construct a new PyCameraFB object.
   *
   * @param w Width of the framebuffer.
   * @param h Height of the framebuffer.
   */
  /**************************************************************************/
  PyCameraFB(uint16_t w, uint16_t h) : GFXcanvas16(w, h) {
    free(buffer);
    buffer = NULL;
  };

  /**************************************************************************/
  /**
   * @brief Set the framebuffer.
   *
   * @param fb Pointer to the framebuffer data.
   */
  /**************************************************************************/
  void setFB(uint16_t *fb) { buffer = fb; }
};

/**** FR and FD ****/

// pointer to the camera's framebuffer
camera_fb_t *fb = NULL;
// pointer to the TFT's framebuffer
PyCameraFB *pyCameraFb = NULL;

// Recognizer model
// S8 model - faster but less accurate
FaceRecognition112V1S8 recognizer;
// Use two-stage fd and weights
HumanFaceDetectMSR01 s1(0.1F, 0.5F, 10, 0.2F);
HumanFaceDetectMNP01 s2(0.5F, 0.3F, 5);
static int8_t is_enrolling = 0; // 0: not enrolling, 1: enrolling

/*
 * @brief Draws face boxes and landmarks on the framebuffer, modified to work
 * with ST7789 TFT display.
 *
 * @param fb Pointer to the framebuffer data.
 * @param results Pointer to the list of detected faces.
 * @param face_id The ID of the detected face.
 */
static void draw_face_boxes(fb_data_t *fb,
                            std::list<dl::detect::result_t> *results,
                            int face_id) {
  int x, y, w, h;
  uint32_t color = ST77XX_YELLOW;
  if (face_id < 0) {
    color = ST77XX_RED;
  } else if (face_id > 0) {
    color = ST77XX_GREEN;
  }
  if (fb->bytes_per_pixel == 2) {
    // color = ((color >> 8) & 0xF800) | ((color >> 3) & 0x07E0) | (color &
    // 0x001F);
    color = ((color >> 16) & 0x001F) | ((color >> 3) & 0x07E0) |
            ((color << 8) & 0xF800);
  }
  int i = 0;
  for (std::list<dl::detect::result_t>::iterator prediction = results->begin();
       prediction != results->end(); prediction++, i++) {

    // create boxes
    x = (int)prediction->box[0];
    y = (int)prediction->box[1];
    w = (int)prediction->box[2] - x + 1;
    h = (int)prediction->box[3] - y + 1;
    if ((x + w) > fb->width) {
      w = fb->width - x;
    }
    if ((y + h) > fb->height) {
      h = fb->height - y;
    }
    // draw boxes
    tft.drawFastHLine(x, y, w, color);
    tft.drawFastHLine(x, y + h - 1, w, color);
    tft.drawFastVLine(x, y, h, color);
    tft.drawFastVLine(x + w - 1, y, h, color);

    // draw  landmarks (left eye, mouth left, nose, right eye, mouth right)
    int x0, y0, j;
    for (j = 0; j < 10; j += 2) {
      x0 = (int)prediction->keypoint[j];
      y0 = (int)prediction->keypoint[j + 1];
      tft.fillRect(x0, y0, 3, 3, color);
    }
  }
}

/**
 * @brief Run face recognition on the framebuffer.
 *
 * @param fb Pointer to the framebuffer data.
 * @param results Pointer to the list of detected faces.
 * @return int The ID of the recognized face.
 */
static int run_face_recognition(fb_data_t *fb,
                                std::list<dl::detect::result_t> *results) {
  std::vector<int> landmarks = results->front().keypoint;
  int id = -1;
  (void)id;

  Tensor<uint8_t> tensor;
  tensor.set_element((uint8_t *)fb->data)
      .set_shape({fb->height, fb->width, 3})
      .set_auto_free(false);

  int enrolled_count = recognizer.get_enrolled_id_num();

  if (enrolled_count < FACE_ID_SAVE_NUMBER && is_enrolling) {
    int id = recognizer.enroll_id(tensor, landmarks, "", true);
    (void)id;

    Serial.printf("Enrolled ID: %d", id);
    tft.setCursor(0, 230);
    tft.setTextColor(ST77XX_CYAN);
    tft.print("Enrolled a new face with ID #");
    tft.print(id);
    is_enrolling = false;
  } else if (enrolled_count > FACE_ID_SAVE_NUMBER) {
    Serial.println(
        "ERROR: Already enrolled the maximum number of faces, can not "
        "enroll more!");
  }

  face_info_t recognize = recognizer.recognize(tensor, landmarks);
  if (recognize.id >= 0 && recognize.similarity >= FR_CONFIDENCE_THRESHOLD) {
    // Face was recognized, print out to serial and TFT
    Serial.printf("Recognized ID: %d", recognize.id);
    Serial.printf("with similarity of: %0.2f", recognize.similarity);
    tft.setCursor(0, 220);
    tft.setTextColor(ST77XX_CYAN);
    tft.print("Recognized Face ID #");
    tft.print(id);
    tft.print("\nSimilarity: ");
    tft.print(recognize.similarity);
    // Set pixel ring to green to indicate a recognized face
    for (int i = 0; i <= NUMPIXELS; i++) {
      pixels.setPixelColor(i, pixels.Color(0, 255, 0));
    }
    pixels.show();
    delay(2500);
  } else if (recognizer.get_enrolled_id_num() > 0) {
    // Face was not recognized but we have faces enrolled
    Serial.println("Intruder alert - face not recognized as an enrolled face!");
    Serial.printf("This face has a similarity of: %0.2f\n",
                  recognize.similarity);
    // Set pixel ring to green to indicate a recognized face
    for (int i = 0; i <= NUMPIXELS; i++) {
      pixels.setPixelColor(i, pixels.Color(255, 0, 0));
    }
    pixels.show();
    delay(1000);
  } else {
    // Face was not recognized and we have nothing enrolled
    Serial.println("Face not recognized, but nothing enrolled!");
  }
  return recognize.id;
}

/**
 * @brief  Initialize the Adafruit MEMENTO's TFT display
 *
 * @return True if TFT display initialized successfully, False otherwise.
 */
bool initDisplay() {
  pinMode(45, OUTPUT);
  digitalWrite(45, LOW);
  tft.init(240, 240); // Initialize ST7789 screen
  tft.setRotation(1);
  tft.fillScreen(ST77XX_GREEN);
  digitalWrite(45, HIGH);
  return true;
}

bool initCamera() {
  Wire.begin(34, 33);
  pinMode(SHUTTER_BUTTON, INPUT_PULLUP);

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = -1;
  config.pin_sccb_scl = -1;
  // use the built in I2C port
  // config.sccb_i2c_port = 0; // use the 'first' i2c port
  config.pin_pwdn = 21;
  config.pin_reset = 47;
  config.xclk_freq_hz = 20000000;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.frame_size = FRAMESIZE_240X240;
  config.pixel_format = PIXFORMAT_RGB565;
  config.fb_count = 2;

  // Initialize the camera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("ERROR: Camera init failed with code 0x%x", err);
    return false;
  }

  // Configure the camera's sensor
  sensor_t *s = esp_camera_sensor_get();
  s->set_vflip(s, 1);
  s->set_hmirror(s, 0);

  return true;
}

void setup() {
  Serial.begin(115200);
  Serial.println();

  if (!initCamera()) {
    Serial.println("Camera init failed!");
  }

  if (!initDisplay()) {
    Serial.println("Display init failed!");
  }
  // Initialize the TFT's framebuffer
  pyCameraFb = new PyCameraFB(240, 240);

  // Initialize NeoPixel ring
  pixels.begin();
  pixels.clear();
  pixels.show();
  pixels.setBrightness(PIXEL_BRIGHTNESS);

  // Initialize face recognition filter and partition
  ra_filter_init(&ra_filter, 20);
  recognizer.set_partition(ESP_PARTITION_TYPE_DATA, ESP_PARTITION_SUBTYPE_ANY,
                           "fr");
#ifdef SAVE_FACES_TO_FLASH
  // Optionally load face ids from flash partition
  recognizer.set_ids_from_flash();
#endif
}

void loop() {
  // If the shutter button is pressed, enroll a new face
  if (digitalRead(SHUTTER_BUTTON) == LOW) {
    is_enrolling = true;
    // Signal to the user on the TFT and serial that we're enrolling a face
    Serial.println("Enrolling face..");
    tft.setCursor(0, 230);
    tft.setTextColor(ST77XX_CYAN);
    tft.print("Enrolling Face...");
    // Make pixel ring light up bright white to better capture facial features
    for (int i = 0; i <= NUMPIXELS; i++) {
      pixels.setPixelColor(i, pixels.Color(255, 255, 255));
    }
    pixels.show();
  }

  // capture from the camera into the frame buffer
  Serial.printf("Capturing frame...\n");
  fb = esp_camera_fb_get();
  if (!fb) {
    Serial.printf("ERROR: Camera capture failed\n");
  } else {
    Serial.printf("Frame capture successful!\n");
    // Face detection
    std::list<dl::detect::result_t> &candidates =
        s1.infer((uint16_t *)fb->buf, {(int)fb->height, (int)fb->width, 3});
    std::list<dl::detect::result_t> &results = s2.infer(
        (uint16_t *)fb->buf, {(int)fb->height, (int)fb->width, 3}, candidates);
    if (results.size() > 0) {
      Serial.println("Detected face!");
      int face_id = 0;
      fb_data_t rfb;
      rfb.width = fb->width;
      rfb.height = fb->height;
      rfb.data = fb->buf;
      rfb.bytes_per_pixel = 2;
      rfb.format = FB_RGB565;
      // Face recognition is SLOW! So, only attempt it if we are enrolling a
      // new face, or have previously enrolled a face
      if (recognizer.get_enrolled_id_num() > 0 || is_enrolling) {
        face_id = run_face_recognition(&rfb, &results);
      } else {
        face_id = 0;
        tft.setCursor(0, 230);
        tft.setTextColor(ST77XX_GREEN);
        tft.print("DETECTED FACE!");
      }
      // Draw face detection boxes and landmarks on the framebuffer
      draw_face_boxes(&rfb, &results, face_id);
      // Turn off pixel ring after we've detected a face
      pixels.clear();
      pixels.show();
    }
  }
  // Blit framebuffer to TFT
  uint8_t temp;
  for (uint32_t i = 0; i < fb->len; i += 2) {
    temp = fb->buf[i + 0];
    fb->buf[i + 0] = fb->buf[i + 1];
    fb->buf[i + 1] = temp;
  }
  pyCameraFb->setFB((uint16_t *)fb->buf);
  tft.drawRGBBitmap(0, 0, (uint16_t *)pyCameraFb->getBuffer(), 240, 240);
  // Release the framebuffer
  esp_camera_fb_return(fb);
}