// SPDX-FileCopyrightText: ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT
#include "TJpg_Decoder.h"
#include "esp_camera.h"
#include <Adafruit_AW9523.h>
#include <Adafruit_NeoPixel.h>
#include <Adafruit_ST7789.h> // Hardware-specific library for ST7789
#include <SdFat.h>

#ifndef TAG
#define TAG "PYCAM"
#endif

// These are defined within https://github.com/espressif/arduino-esp32/blob/master/variants/adafruit_camera_esp32s3/pins_arduino.h
// However, they are not updated to the production-ready pins within the PlatformIO ESP32 package, so we define them here.
#define TFT_BACKLIGHT 45
#define PYCAM_SCL 33
#define PYCAM_SDA 34

#define AW_DOWN_MASK (1UL << AWEXP_BUTTON_DOWN)
#define AW_LEFT_MASK (1UL << AWEXP_BUTTON_LEFT)
#define AW_UP_MASK (1UL << AWEXP_BUTTON_UP)
#define AW_RIGHT_MASK (1UL << AWEXP_BUTTON_RIGHT)
#define AW_OK_MASK (1UL << AWEXP_BUTTON_OK)
#define AW_SEL_MASK (1UL << AWEXP_BUTTON_SEL)
#define AW_CARDDET_MASK (1UL << AWEXP_SD_DET)
#define AW_INPUTS_MASK                                                         \
  (AW_DOWN_MASK | AW_LEFT_MASK | AW_UP_MASK | AW_RIGHT_MASK | AW_OK_MASK |     \
   AW_SEL_MASK | AW_CARDDET_MASK)

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

/**************************************************************************/
/**
 * @brief Main class for Adafruit PyCamera.
 *
 * @details This class extends Adafruit_ST7789 and provides functionalities
 * for operating the PyCamera.
 */
/**************************************************************************/
class Adafruit_PyCamera : public Adafruit_ST7789 {
public:
  /**************************************************************************/
  /**
   * @brief Construct a new Adafruit_PyCamera object.
   */
  /**************************************************************************/
  Adafruit_PyCamera();

  bool begin(void);

  bool initCamera(bool hwreset);
  bool initDisplay(void);
  bool initExpander(void);
  bool initAccel(void);
  bool initSD(void);
  void endSD(void);
  void I2Cscan(void);

  bool captureFrame(void);
  void blitFrame(void);
  bool takePhoto(const char *filename_base, framesize_t framesize);
  bool setFramesize(framesize_t framesize);
  bool setSpecialEffect(uint8_t effect);

  void speaker_tone(uint32_t tonefreq, uint32_t tonetime);

  float readBatteryVoltage(void);
  uint32_t readButtons(void);
  bool SDdetected(void);
  bool justReleased(uint8_t button_pin);
  bool justPressed(uint8_t button_pin);

  bool readAccelData(int16_t *x, int16_t *y, int16_t *z);
  bool readAccelData(float *x, float *y, float *z);

  void setNeopixel(uint32_t c);
  void setRing(uint32_t c);
  uint32_t Wheel(byte WheelPos);

  uint32_t timestamp(void);
  void timestampPrint(const char *msg);
  /** @brief Pointer to the camera sensor structure. */
  sensor_t *camera;
  /** @brief Pointer to the camera frame buffer. */
  camera_fb_t *frame = NULL;
  /** @brief Pointer to the PyCamera framebuffer object. */
  PyCameraFB *fb = NULL;

  /** @brief Adafruit NeoPixel object for single pixel control. */
  Adafruit_NeoPixel pixel;
  /** @brief Adafruit NeoPixel object for ring control. */
  Adafruit_NeoPixel ring;
  /** @brief Adafruit AW9523 object for I/O expander functionality. */
  Adafruit_AW9523 aw;
  /** @brief Pointer to the I2C device for accelerometer. */
  Adafruit_I2CDevice *lis_dev = NULL;

  /** @brief SdFat object for SD card operations. */
  SdFat sd;
  /** @brief Timestamp for internal timing operations. */
  uint32_t _timestamp;
  /** @brief Last state of the buttons. */
  uint32_t last_button_state = 0xFFFFFFFF;
  /** @brief Current state of the buttons. */
  uint32_t button_state = 0xFFFFFFFF;

  /** @brief Current photo size setting. */
  framesize_t photoSize = FRAMESIZE_VGA;
  /** @brief Current special effect setting. */
  int8_t specialEffect = 0;
  /** @brief Configuration structure for the camera. */
  camera_config_t camera_config;
};

#define LIS3DH_REG_STATUS1 0x07
#define LIS3DH_REG_OUTADC1_L 0x08 /**< 1-axis acceleration data. Low value */
#define LIS3DH_REG_OUTADC1_H 0x09 /**< 1-axis acceleration data. High value */
#define LIS3DH_REG_OUTADC2_L 0x0A /**< 2-axis acceleration data. Low value */
#define LIS3DH_REG_OUTADC2_H 0x0B /**< 2-axis acceleration data. High value */
#define LIS3DH_REG_OUTADC3_L 0x0C /**< 3-axis acceleration data. Low value */
#define LIS3DH_REG_OUTADC3_H 0x0D /**< 3-axis acceleration data. High value */
#define LIS3DH_REG_INTCOUNT                                                    \
  0x0E /**< INT_COUNTER register [IC7, IC6, IC5, IC4, IC3, IC2, IC1, IC0] */
#define LIS3DH_REG_WHOAMI 0x0F
#define LIS3DH_REG_TEMPCFG 0x1F
#define LIS3DH_REG_CTRL1 0x20
#define LIS3DH_REG_CTRL2 0x21
#define LIS3DH_REG_CTRL3 0x22
#define LIS3DH_REG_CTRL4 0x23
#define LIS3DH_REG_CTRL5 0x24
#define LIS3DH_REG_CTRL6 0x25
#define LIS3DH_REG_STATUS2 0x27
#define LIS3DH_REG_OUT_X_L 0x28 /**< X-axis acceleration data. Low value */
#define LIS3DH_LSB16_TO_KILO_LSB10 6400
