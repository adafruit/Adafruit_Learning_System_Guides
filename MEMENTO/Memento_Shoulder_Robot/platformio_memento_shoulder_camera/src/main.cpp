// SPDX-FileCopyrightText: 2018 me-no-dev for Espressif Systems
//
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// Modified by Brent Rubell for Adafruit Industries for use with Adafruit
// MEMENTO as a shoulder-mounted camera robot
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
#include <ESP32Servo.h>
#include <SPI.h>
#include <Wire.h>
#include <vector>

// Servo configuration
#define SERVO_PIN A1

// Delay before the servo moves back to the center position, in milliseconds
#define DELAY_SERVO_CENTER 3000

// Delay between each attempt at new face detection, in milliseconds
#define DELAY_DETECTION 1000

// How much the object needs to move past the "dead zones" before the servo is
// moved
#define SERVO_HYSTERESIS 2

// Factor used to scale the servo's movement
#define SERVO_MOVEMENT_FACTOR 0.4

// The servo's center position
#define SERVO_CENTER 90

// Pin used for the NeoPixel ring
#define PIXELS_PIN A0
// Number of NeoPixels on the ring
#define NUMPIXELS 12
// NeoPixel ring object
Adafruit_NeoPixel pixels(NUMPIXELS, PIXELS_PIN, NEO_RGBW + NEO_KHZ800);

// TFT display object
Adafruit_ST7789 tft = Adafruit_ST7789(TFT_CS, TFT_DC, TFT_RESET);

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

// Pointer for the camera's framebuffer
camera_fb_t *fb = NULL;
// Pointer for the TFT's framebuffer
PyCameraFB *pyCameraFb = NULL;
// Face recognizer model
FaceRecognition112V1S8 recognizer;
// Configuration for two-stage face detection
HumanFaceDetectMSR01 s1(0.1F, 0.5F, 10, 0.2F);
HumanFaceDetectMNP01 s2(0.5F, 0.3F, 5);

// Filters how often a new face is detected
bool isTrackingFace;
unsigned long prvDetectTime = 0UL;

// The bounding box's midpoint coordinates for the current frame
int cur_face_box_x_midpoint = 0;
// The bounding box's midpoint coordinates for the previous frame
int prv_face_box_x_midpoint = 0;
// "Dead zone" filtering values for the bounding box
int deadzoneStart, deadzoneEnd;

// Servo object
Servo headServo;
// Current servo position
int curServoPos = 0;
// Previous servo position
int prvServoPos = 0;

/*
 * @brief Draws face boxes and landmarks on the framebuffer, modified to work
 * with ST7789 TFT display.
 *
 * @param fb Pointer to the framebuffer data.
 * @param results Pointer to the list of detected faces.
 */
static void draw_face_boxes(fb_data_t *fb,
                            std::list<dl::detect::result_t> *results) {
  int x, y, w, h;
  uint32_t color = ST77XX_GREEN;

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

    // draw a bounding box around the face
    tft.drawFastHLine(x, y, w, color);
    tft.drawFastHLine(x, y + h - 1, w, color);
    tft.drawFastVLine(x, y, h, color);
    tft.drawFastVLine(x + w - 1, y, h, color);
    Serial.printf("Bounding box width: %d px\n", w);
    Serial.printf("Bounding box height: %d px\n", h);

    // Calculate the current bounding box's x-midpoint so we can compare it
    // against the previous midpoint
    cur_face_box_x_midpoint = x + (w / 2);

    // Draw a circle at the midpoint of the bounding box
    tft.fillCircle(cur_face_box_x_midpoint, y + (h / 2), 5, ST77XX_BLUE);

    // Draw vertical lines to show the deadzones relative to the bounding box
    tft.drawFastVLine(deadzoneStart, y, h, ST77XX_BLUE);
    tft.drawFastVLine(deadzoneEnd, y, h, ST77XX_BLUE);

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

/**
 * @brief  Initialize the MEMENTO's camera
 *
 * @return True if camera initialized successfully, False otherwise.
 */
bool initCamera() {
  Wire.begin(34, 33);
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

/**
 * @brief  Perform face detection on a frame
 *
 * @return List of detected faces.
 *         NOTE: The returned list size is 0 if no faces are detected
 */
std::list<dl::detect::result_t> performFaceDetection() {
  // Capture a frame from the camera into the frame buffer
  fb = esp_camera_fb_get();
  if (!fb) {
    Serial.printf("ERROR: Camera capture failed\n");
    return std::list<dl::detect::result_t>();
  }

  // Perform face detection
  std::list<dl::detect::result_t> candidates =
      s1.infer((uint16_t *)fb->buf, {(int)fb->height, (int)fb->width, 3});
  std::list<dl::detect::result_t> results = s2.infer(
      (uint16_t *)fb->buf, {(int)fb->height, (int)fb->width, 3}, candidates);
  return results;
}

/**
 * @brief Moves a servo to track a face's location.
 */
void trackFace() {
  // Check if the bounding box has moved and if this is the first frame with a
  // face detected, just save the coordinates
  if ((cur_face_box_x_midpoint != prv_face_box_x_midpoint) &&
      (prv_face_box_x_midpoint != 0)) {
    Serial.printf("x_midpoint (curr. face):      %d px\n",
                  cur_face_box_x_midpoint);
    Serial.printf("x_midpoint (prv. face):       %d px\n",
                  prv_face_box_x_midpoint);

    // Calculate the difference between the new bounding box midpoint and the
    // previous bounding box midpoint, in pixels
    int mp_diff_pixels = abs(cur_face_box_x_midpoint - prv_face_box_x_midpoint);
    Serial.printf("Difference between midpoints: %d px\n", mp_diff_pixels);

    // Only move the servo if the magnitude of the difference between the
    // midpoints is greater than SERVO_HYSTERESIS
    // NOTE: This smooths the servo's motion to avoid the servo from
    // "jittering".
    if (mp_diff_pixels > SERVO_HYSTERESIS) {
      // Calculate how many steps, in degrees, the servo should move
      int servoStepAmount = mp_diff_pixels * SERVO_MOVEMENT_FACTOR;

      // Move the servo to the left or right, depending where x_midpoint is
      // located relative to the dead zones
      if (cur_face_box_x_midpoint < deadzoneStart)
        curServoPos += servoStepAmount;
      else if (cur_face_box_x_midpoint > deadzoneEnd)
        curServoPos -= servoStepAmount;
    }

    // Move the servo to the new position
    if (curServoPos != prvServoPos) {
      curServoPos = abs(curServoPos);
      Serial.printf("Moving servo to new position: %d degrees\n", curServoPos);
      headServo.write(curServoPos);
    }
  }

  // Update the previous midpoint coordinates with the new coordinates
  prv_face_box_x_midpoint = cur_face_box_x_midpoint;

  // Save the current servo position for the next comparison
  prvServoPos = curServoPos;
}

void setup() {
  Serial.begin(115200);
  Serial.println();

  if (!initCamera())
    Serial.println("Camera init failed!");
  Serial.println("Camera init OK!");

  if (!initDisplay())
    Serial.println("Display init failed!");
  Serial.println("Display init OK!");

  // Initialize the TFT's framebuffer
  pyCameraFb = new PyCameraFB(240, 240);

  // Initialize NeoPixel ring
  pixels.begin();
  pixels.setBrightness(15);
  pixels.clear();
  pixels.show();

  // Initialize servo
  // Allow allocation of all timers
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);
  // Attach a standard 50 hz servo to SERVO_PIN
  headServo.setPeriodHertz(50);
  headServo.attach(SERVO_PIN, 1000, 2000);
  // Move the servo to the center
  curServoPos = SERVO_CENTER;
  headServo.write(curServoPos);

  // Initialize face recognition filter and partition
  ra_filter_init(&ra_filter, 20);
  recognizer.set_partition(ESP_PARTITION_TYPE_DATA, ESP_PARTITION_SUBTYPE_ANY,
                           "fr");

  // Calculate the dead zone for the bounding box
  deadzoneStart = 240 / 2 - 10;
  deadzoneEnd = 240 / 2 + 10;
  isTrackingFace = false;

  Serial.println("Setup OK!\nSearching for a face...");
}

void loop() {
  // Capture a frame from the camera and perform face detection on it
  std::list<dl::detect::result_t> detectionResults = performFaceDetection();

  // Did we detect a face?
  if (detectionResults.size() > 0) {
    // Fill NeoPixel ring with a blue color while tracking
    pixels.fill(pixels.Color(0, 0, 255), 0, pixels.numPixels());
    pixels.show();
    if ((!isTrackingFace) && ((millis() - prvDetectTime) > DELAY_DETECTION)) {
      Serial.println("Face Detected!\nTracking new face...");
      isTrackingFace = true;
    }

    // Write to TFT
    tft.setCursor(0, 230);
    tft.setTextColor(ST77XX_GREEN);
    tft.print("TRACKING FACE");

    // Draw face detection boxes and landmarks on the framebuffer
    fb_data_t rfb;
    rfb.width = fb->width;
    rfb.height = fb->height;
    rfb.data = fb->buf;
    rfb.bytes_per_pixel = 2;
    rfb.format = FB_RGB565;
    draw_face_boxes(&rfb, &detectionResults);

    // Move the servo to track the face's location
    trackFace();

    // Update the timer used to detect when we last "saw" the face
    prvDetectTime = millis();
  } else {
    // We aren't tracking a face anymore
    isTrackingFace = false;

    // No face has been detected for DELAY_SERVO_CENTER seconds, re-center the
    // servo
    if ((millis() - prvDetectTime) > DELAY_SERVO_CENTER) {
      Serial.println("Lost track of face, moving servo to center position!");
      curServoPos = SERVO_CENTER;
      headServo.write(curServoPos);

      // Reset the previous detection time
      prvDetectTime = millis();

      // Re-center the bounding box at the middle of the TFT
      prv_face_box_x_midpoint = 120;

      // Clear the NeoPixels while we're not tracking a face
      pixels.clear();
      pixels.show();
    }
  }

  // Blit out the framebuffer to the TFT
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