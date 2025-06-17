// SPDX-FileCopyrightText: ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT
#include "Adafruit_PyCamera.h"

static uint16_t *jpeg_buffer = NULL;

/**************************************************************************/
/**
 * @brief Outputs the buffer for JPEG decoding.
 *
 * @param x The x-coordinate where the bitmap starts.
 * @param y The y-coordinate where the bitmap starts.
 * @param w The width of the bitmap.
 * @param h The height of the bitmap.
 * @param bitmap Pointer to the bitmap data.
 *
 * @return true if the buffer is successfully outputted, false otherwise.
 *
 * @details This function is used as a callback for JPEG decoding. It outputs
 * the decoded bitmap to a specified location in the `jpeg_buffer`. The function
 * checks for the validity of `jpeg_buffer` and ensures that the drawing
 * operations stay within the bounds of the buffer.
 */
/**************************************************************************/
bool buffer_output(int16_t x, int16_t y, uint16_t w, uint16_t h,
                   uint16_t *bitmap) {
  if (!jpeg_buffer)
    return false;
  // Serial.printf("Drawing [%d, %d] to (%d, %d)\n", w, h, x, y);
  for (int xi = x; xi < x + w; xi++) {
    if (xi >= 240)
      continue;
    if (xi < 0)
      continue;
    for (int yi = y; yi < y + h; yi++) {
      if (yi >= 240)
        continue;
      if (yi < 0)
        continue;
      jpeg_buffer[yi * 240 + xi] = bitmap[(yi - y) * w + (xi - x)];
    }
  }
  return true;
}

/**************************************************************************/
/**
 * @brief Construct a new Adafruit_PyCamera object.
 *
 * @details Initializes the display with specified TFT parameters.
 *
 */
/**************************************************************************/
Adafruit_PyCamera::Adafruit_PyCamera(void)
    : Adafruit_ST7789(TFT_CS, TFT_DC, TFT_RESET) {}

/**************************************************************************/
/**
 * @brief Initializes the PyCamera.
 *
 * @details Sets up the speaker, Neopixel, Neopixel Ring, shutter button, and
 * performs I2C scan. Initializes the display, expander, camera, frame size, SD
 * card (if detected), and accelerometer. Creates a new framebuffer for the
 * camera.
 *
 * @return true if initialization is successful, false otherwise.
 */
/**************************************************************************/
bool Adafruit_PyCamera::begin() {
  Serial.println("Init PyCamera obj");
  // Setup and turn off speaker
  pinMode(SPEAKER, OUTPUT);
  digitalWrite(SPEAKER, LOW);

  // Setup and turn off Neopixel
  pixel.setPin(PIN_NEOPIXEL);
  pixel.updateLength(1);
  pixel.begin();
  pixel.setBrightness(50);
  setNeopixel(0x0);

  // Setup and turn off Neopixel Ring
  ring.setPin(A1);
  ring.updateType(NEO_GRBW + NEO_KHZ800);
  ring.updateLength(8);
  ring.begin();
  ring.setBrightness(255);
  setRing(0x0);

  // boot button is also shutter
  pinMode(SHUTTER_BUTTON, INPUT_PULLUP);

  I2Cscan();

  if (!initDisplay())
    return false;
  if (!initExpander())
    return false;
  if (!initCamera(true))
    return false;
  if (!setFramesize(FRAMESIZE_240X240))
    return false;
  if (SDdetected())
    initSD();
  if (!initAccel())
    return false;

  fb = new PyCameraFB(240, 240);

  _timestamp = millis();

  return true;
}

/**************************************************************************/
/**
 * @brief Initializes the SD card.
 *
 * @details Checks for SD card presence and attempts initialization. Performs a
 * power reset, reinitializes SPI for SD card communication, and checks for
 * errors during SD card initialization. Also lists files on the SD card if
 * initialization is successful.
 *
 * @return true if SD card is successfully initialized, false otherwise.
 */
/**************************************************************************/
bool Adafruit_PyCamera::initSD(void) {

  if (!SDdetected()) {
    Serial.println("No SD card inserted");
    return false;
  }

  Serial.println("SD card inserted, trying to init");

  // power reset
  aw.pinMode(AWEXP_SD_PWR, OUTPUT);
  aw.digitalWrite(AWEXP_SD_PWR, HIGH); // turn off

  pinMode(SD_CS, OUTPUT);
  digitalWrite(SD_CS, LOW);

  Serial.println("De-initing SPI");
  SPI.end();
  pinMode(SCK, OUTPUT);
  digitalWrite(SCK, LOW);
  pinMode(MOSI, OUTPUT);
  digitalWrite(MISO, LOW);
  pinMode(MISO, OUTPUT);
  digitalWrite(MISO, LOW);

  delay(50);

  Serial.println("Re-init SPI");
  digitalWrite(SD_CS, HIGH);
  SPI.begin();
  aw.digitalWrite(AWEXP_SD_PWR, LOW); // turn on
  delay(100);

  if (!sd.begin(SD_CS, SD_SCK_MHZ(4))) {
    if (sd.card()->errorCode()) {
      Serial.printf("SD card init failure with code 0x%x data %d\n",
                    sd.card()->errorCode(), (int)sd.card()->errorData());
    } else if (sd.vol()->fatType() == 0) {
      Serial.println("Can't find a valid FAT16/FAT32 partition.");
    } else {
      Serial.println("SD begin failed, can't determine error type");
    }
    aw.digitalWrite(AWEXP_SD_PWR, HIGH); // turn off power
    return false;
  }

  Serial.println("Card successfully initialized");
  uint32_t size = sd.card()->sectorCount();
  if (size == 0) {
    Serial.println("Can't determine the card size");
  } else {
    uint32_t sizeMB = 0.000512 * size + 0.5;
    Serial.printf("Card size: %d MB FAT%d\n", (int)sizeMB, sd.vol()->fatType());
  }
  Serial.println("Files found (date time size name):");
  sd.ls(LS_R | LS_DATE | LS_SIZE);
  return true;
}

/**************************************************************************/
/**
 * @brief Ends the SD card session.
 *
 * @details Powers off the SD card to end the session.
 */
/**************************************************************************/
void Adafruit_PyCamera::endSD() {
  // aw.pinMode(AWEXP_SD_PWR, OUTPUT);
  // aw.digitalWrite(AWEXP_SD_PWR, HIGH); // start off
}

/**************************************************************************/
/**
 * @brief Initializes the AW9523 I/O expander.
 *
 * @details Sets up the AW9523 expander, configuring speaker, SD power, and SD
 * detection pins.
 *
 * @return true if the expander is successfully initialized, false otherwise.
 */
/**************************************************************************/
bool Adafruit_PyCamera::initExpander(void) {
  Serial.print("Init AW9523...");
  if (!aw.begin(0x58, &Wire)) {
    Serial.println("AW9523 not found!");
    return false;
  }
  Serial.println("OK!");
  aw.pinMode(AWEXP_SPKR_SD, OUTPUT);
  aw.digitalWrite(AWEXP_SPKR_SD, LOW); // start muted
  aw.pinMode(AWEXP_SD_PWR, OUTPUT);
  aw.digitalWrite(AWEXP_SD_PWR, LOW); // start SD powered
  aw.pinMode(AWEXP_SD_DET, INPUT);
  return true;
}

/**************************************************************************/
/**
 * @brief Initializes the display.
 *
 * @details This method sets up the display for the PyCamera. It starts by
 * initializing the backlight control, then initializes the ST7789 screen with
 * the specified dimensions and rotation. Finally, it fills the screen with a
 * green color and turns on the backlight.
 *
 * @return true if the display is successfully initialized, false otherwise.
 */
/**************************************************************************/
bool Adafruit_PyCamera::initDisplay(void) {
  Serial.print("Init display....");

  pinMode(TFT_BACKLIGHT, OUTPUT);
  digitalWrite(TFT_BACKLIGHT, LOW);
  init(240, 240); // Initialize ST7789 screen
  setRotation(1);
  fillScreen(ST77XX_GREEN);

  digitalWrite(TFT_BACKLIGHT, HIGH);
  Serial.println("done!");
  return true;
}

/**************************************************************************/
/**
 * @brief Sets the frame size for the camera.
 *
 * @details Configures the camera to use the specified frame size. If the frame
 * size cannot be set, it outputs an error message with the error code.
 *
 * @param framesize The desired frame size to set for the camera.
 * @return true if the frame size is successfully set, false if there is an
 * error.
 */
/**************************************************************************/
bool Adafruit_PyCamera::setFramesize(framesize_t framesize) {
  uint8_t ret = camera->set_framesize(camera, framesize);
  if (ret != 0) {
    Serial.printf("Could not set resolution: error 0x%x\n", ret);
    return false;
  }
  return true;
}

/**************************************************************************/
/**
 * @brief Sets a special effect on the camera.
 *
 * @details Applies a specified special effect to the camera's output. If the
 * effect cannot be set, it outputs an error message with the error code.
 *
 * @param effect The special effect identifier to apply.
 * @return true if the special effect is successfully set, false if there is an
 * error.
 */
/**************************************************************************/
bool Adafruit_PyCamera::setSpecialEffect(uint8_t effect) {
  uint8_t ret = camera->set_special_effect(camera, effect);
  if (ret != 0) {
    Serial.printf("Could not set effect: error 0x%x\n", ret);
    return false;
  }
  return true;
}

/**************************************************************************/
/**
 * @brief Initializes the camera module.
 *
 * @details Configures and initializes the camera with specified settings.
 * It sets up various camera parameters like LEDC channel and timer, pin
 * configuration, XCLK frequency, frame buffer location, pixel format, frame
 * size, and JPEG quality. It also handles the hardware reset if specified.
 * After configuration, it initializes the camera and checks for errors. If
 * successful, it retrieves the camera sensor information and sets horizontal
 * mirror and vertical flip settings.
 *
 * @param hwreset Flag to determine if a hardware reset is needed.
 * @return true if the camera is successfully initialized, false if there is an
 * error.
 */
/**************************************************************************/
bool Adafruit_PyCamera::initCamera(bool hwreset) {
  Serial.print("Config camera...");
  Wire.begin(PYCAM_SDA, PYCAM_SCL);

  if (hwreset) {
  }

  camera_config.ledc_channel = LEDC_CHANNEL_0;
  camera_config.ledc_timer = LEDC_TIMER_0;
  camera_config.pin_d0 = Y2_GPIO_NUM;
  camera_config.pin_d1 = Y3_GPIO_NUM;
  camera_config.pin_d2 = Y4_GPIO_NUM;
  camera_config.pin_d3 = Y5_GPIO_NUM;
  camera_config.pin_d4 = Y6_GPIO_NUM;
  camera_config.pin_d5 = Y7_GPIO_NUM;
  camera_config.pin_d6 = Y8_GPIO_NUM;
  camera_config.pin_d7 = Y9_GPIO_NUM;
  camera_config.pin_xclk = XCLK_GPIO_NUM;
  camera_config.pin_pclk = PCLK_GPIO_NUM;
  camera_config.pin_vsync = VSYNC_GPIO_NUM;
  camera_config.pin_href = HREF_GPIO_NUM;
  camera_config.pin_sccb_sda = -1;
  camera_config.pin_sccb_scl = -1;
  // use the built in I2C port
  camera_config.sccb_i2c_port = 0; // use the 'first' i2c port
  camera_config.pin_pwdn = 21;
  camera_config.pin_reset = 47;
  camera_config.xclk_freq_hz = 20000000;
  camera_config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  camera_config.fb_location = CAMERA_FB_IN_PSRAM;

  Serial.print("Config format...");
  /*
     // using RGB565 for immediate blitting
     camera_config.pixel_format = PIXFORMAT_RGB565;
     camera_config.frame_size = FRAMESIZE_240X240;
     camera_config.fb_count = 1;
   */
  camera_config.pixel_format = PIXFORMAT_JPEG;
  camera_config.frame_size =
      FRAMESIZE_UXGA; // start with biggest possible image supported!!! do not
                      // change this
  camera_config.jpeg_quality = 4;
  camera_config.fb_count = 2;

  Serial.print("Initializing...");
  // camera init
  esp_err_t err = esp_camera_init(&camera_config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n\r", err);
    return false;
  }

  Serial.println("OK");

  camera = esp_camera_sensor_get();
  Serial.printf("Found camera PID %04X\n\r", camera->id.PID);
  camera->set_hmirror(camera, 0);
  camera->set_vflip(camera, 1);

  return true;
}

/**************************************************************************/
/**
 * @brief Reads the battery voltage.
 *
 * @details Measures the battery voltage through the BATT_MONITOR pin.
 * The reading is scaled to account for the voltage divider and ADC resolution.
 *
 * @return The battery voltage in volts.
 */
/**************************************************************************/
float Adafruit_PyCamera::readBatteryVoltage(void) {
  return analogRead(BATT_MONITOR) * 2.0 * 3.3 / 4096;
}

/**************************************************************************/
/**
 * @brief Checks if an SD card is detected.
 *
 * @details Reads the state of the SD card detection pin using the AW9523
 * expander. A high state indicates that an SD card is present.
 *
 * @return true if an SD card is detected, false otherwise.
 */
/**************************************************************************/
bool Adafruit_PyCamera::SDdetected(void) {
  return aw.digitalRead(AWEXP_SD_DET);
}

/**************************************************************************/
/**
 * @brief Reads the current state of the buttons.
 *
 * @details Retrieves the state of all buttons connected to the AW9523 expander
 * and the shutter button. The state is updated and stored in the button_state
 * variable. The previous state is stored in last_button_state.
 *
 * @return The current state of the buttons as a 32-bit unsigned integer.
 */
/**************************************************************************/
uint32_t Adafruit_PyCamera::readButtons(void) {
  last_button_state = button_state;
  button_state = aw.inputGPIO() & AW_INPUTS_MASK;
  button_state |= (bool)digitalRead(SHUTTER_BUTTON);
  return button_state;
}

/**************************************************************************/
/**
 * @brief Checks if a button was just pressed.
 *
 * @details Determines if the specified button has transitioned from a
 * non-pressed to a pressed state since the last read. This function is useful
 * for detecting button press events.
 *
 * @param button_pin The pin number of the button to check.
 * @return true if the button was just pressed, false otherwise.
 */
/**************************************************************************/
bool Adafruit_PyCamera::justPressed(uint8_t button_pin) {
  return ((last_button_state & (1UL << button_pin)) && // was not pressed before
          !(button_state & (1UL << button_pin)));      // and is pressed now
}

/**************************************************************************/
/**
 * @brief Checks if a button was just released.
 *
 * @details Determines if the specified button has transitioned from a pressed
 * to a non-pressed state since the last read. This function is useful for
 * detecting button release events.
 *
 * @param button_pin The pin number of the button to check.
 * @return true if the button was just released, false otherwise.
 */
/**************************************************************************/
bool Adafruit_PyCamera::justReleased(uint8_t button_pin) {
  return (!(last_button_state & (1UL << button_pin)) && // was pressed before
          (button_state & (1UL << button_pin)));        // and isnt pressed now
}

/**************************************************************************/
/**
 * @brief Plays a tone through the speaker.
 *
 * @details Generates a tone of a specified frequency and duration through the
 * speaker. It unmutes the speaker before playing the tone and mutes it again
 * after the tone is played. The function uses a blocking delay for the duration
 * of the tone.
 *
 * @param tonefreq The frequency of the tone in Hertz.
 * @param tonetime The duration of the tone in milliseconds.
 */
/**************************************************************************/
void Adafruit_PyCamera::speaker_tone(uint32_t tonefreq, uint32_t tonetime) {
  aw.digitalWrite(AWEXP_SPKR_SD, HIGH); // un-mute
  tone(SPEAKER, tonefreq, tonetime);    // tone1 - B5
  delay(tonetime);
  aw.digitalWrite(AWEXP_SPKR_SD, LOW); // mute
}

/**************************************************************************/
/**
 * @brief Captures a photo and saves it to an SD card.
 *
 * @details This function captures a photo with the camera at the specified
 * resolution, and saves it to the SD card with a filename based on the provided
 * base name. It handles SD card detection, initialization, and file creation.
 * The function also manages camera frame buffer acquisition and release, and
 * sets the camera resolution.
 *
 * @param filename_base Base name for the file to be saved. The function appends
 * a numerical suffix to create a unique filename.
 * @param framesize The resolution at which the photo should be captured.
 * @return true if the photo is successfully captured and saved, false
 * otherwise.
 */
/**************************************************************************/
bool Adafruit_PyCamera::takePhoto(const char *filename_base,
                                  framesize_t framesize) {
  bool ok = false;
  File file;
  // esp_err_t res = ESP_OK;

  if (!SDdetected()) {
    Serial.println("No SD card inserted");
    return false;
  }

  if (!sd.card() || (sd.card()->sectorCount() == 0)) {
    Serial.println("No SD card found");
    // try to initialize?
    if (!initSD())
      return false;
  }

  // we're probably going to succeed in saving the file so we should
  // change rez now since we need to grab two frames worth to clear out a cache
  Serial.println("Reconfiguring resolution");
  if (!setFramesize(framesize))
    return false;

  // capture and toss first internal buffer
  frame = esp_camera_fb_get();
  if (!frame) {
    esp_camera_fb_return(frame);
    setFramesize(FRAMESIZE_240X240);
    Serial.println("Couldnt capture first frame");
    return false;
  }
  Serial.printf("\t\t\tSnapped 1st %d bytes (%d x %d) in %d ms\n\r", frame->len,
                frame->width, frame->height, (int)timestamp());
  esp_camera_fb_return(frame);

  // capture and toss second internal buffer
  frame = esp_camera_fb_get();
  if (!frame) {
    esp_camera_fb_return(frame);
    Serial.println("Couldnt capture second frame");
    setFramesize(FRAMESIZE_240X240);
    return false;
  }
  Serial.printf("\t\t\tSnapped 2nd %d bytes (%d x %d) in %d ms\n\r", frame->len,
                frame->width, frame->height, (int)timestamp());
  char fullfilename[64];
  for (int inc = 0; inc <= 1000; inc++) {
    if (inc == 1000)
      return false;
    snprintf(fullfilename, sizeof(fullfilename), "%s%03d.jpg", filename_base,
             inc);
    if (!sd.exists(fullfilename))
      break;
  }
  // Create the file
  if (file.open(fullfilename, FILE_WRITE)) {
    if (file.write(frame->buf, frame->len)) {
      Serial.printf("Saved JPEG to filename %s\n\r", fullfilename);
      file.close();
      // check what we wrote!
      sd.ls(LS_R | LS_DATE | LS_SIZE);

      ok = true;
    } else {
      Serial.println("Couldn't write JPEG data to file");
    }
  }

  // even if it doesnt work out, reset camera size and close file
  esp_camera_fb_return(frame);
  file.close();
  setFramesize(FRAMESIZE_240X240);
  return ok;
}

/**************************************************************************/
/**
 * @brief Returns the time elapsed since the last call to this function.
 *
 * @details This function calculates the time difference (in milliseconds)
 * between the current time and the last time this function was called. It
 * updates the internal timestamp to the current time at each call.
 *
 * @return The time elapsed (in milliseconds) since the last call to this
 * function.
 */
/**************************************************************************/
uint32_t Adafruit_PyCamera::timestamp(void) {
  uint32_t delta = millis() - _timestamp;
  _timestamp = millis();
  return delta;
}

/**************************************************************************/
/**
 * @brief Prints a timestamped message to the Serial output.
 *
 * @details This function prints a message to the Serial output, prefixed with a
 * timestamp. The timestamp represents the time elapsed in milliseconds since
 * the last call to `timestamp()` function. It is useful for debugging and
 * performance measurement.
 *
 * @param msg The message to be printed along with the timestamp.
 */
/**************************************************************************/
void Adafruit_PyCamera::timestampPrint(const char *msg) {
  Serial.printf("%s: %d ms elapsed\n\r", msg, (int)timestamp());
}

/**************************************************************************/
/**
 * @brief Captures a frame from the camera and processes it.
 *
 * @details This function captures a frame from the camera and processes it
 * based on the current pixel format setting. It handles both JPEG and RGB565
 * formats. For JPEG, it scales and draws the image onto a framebuffer. For
 * RGB565, it flips the endians of the frame buffer. This function is essential
 * for capturing and displaying camera frames.
 *
 * @return bool Returns true if the frame was successfully captured and
 * processed, false otherwise.
 */
/**************************************************************************/
bool Adafruit_PyCamera::captureFrame(void) {
  // Serial.println("Capturing...");
  // esp_err_t res = ESP_OK;
#if ARDUHAL_LOG_LEVEL >= ARDUHAL_LOG_LEVEL_INFO
  int64_t fr_start = esp_timer_get_time();
#endif

  frame = esp_camera_fb_get();

  if (!frame) {
    ESP_LOGE(TAG, "Camera frame capture failed");
    return false;
  }

  /*
  Serial.printf("\t\t\tFramed %d bytes (%d x %d) in %d ms\n\r",
                frame->len,
                frame->width, frame->height,
                timestamp());
  */
  if (camera_config.pixel_format == PIXFORMAT_JPEG) {
    // Serial.print("JPEG");
    //  create the framebuffer if we haven't yet
    if (!fb->getBuffer() || !jpeg_buffer) {
      jpeg_buffer = (uint16_t *)malloc(240 * 240 * 2);
      fb->setFB(jpeg_buffer);
    }
    uint16_t w = 0, h = 0, scale = 1;
    int xoff = 0, yoff = 0;
    TJpgDec.getJpgSize(&w, &h, frame->buf, frame->len);
    if (w <= 240 || h <= 240) {
      scale = 1;
      xoff = yoff = 0;
    } else if (w <= 480 || h <= 480) {
      scale = 2;
      xoff = (480 - w) / 2;
      yoff = (480 - h) / 2;
    } else if (w <= 960 || h <= 960) {
      scale = 4;
    } else {
      scale = 8;
    }
    // Serial.printf(" size: %d x %d, scale %d\n\r", w, h, scale);
    TJpgDec.setJpgScale(scale);
    TJpgDec.setCallback(buffer_output);
    TJpgDec.drawJpg(xoff, yoff, frame->buf, frame->len);
    fb->setFB(jpeg_buffer);
  } else if (camera_config.pixel_format == PIXFORMAT_RGB565) {
    // flip endians
    uint8_t temp;
    for (uint32_t i = 0; i < frame->len; i += 2) {
      temp = frame->buf[i + 0];
      frame->buf[i + 0] = frame->buf[i + 1];
      frame->buf[i + 1] = temp;
    }
    fb->setFB((uint16_t *)frame->buf);
  }

  return true;
}

/**************************************************************************/
/**
 * @brief Blits the current frame buffer to the display.
 *
 * @details This function draws the current frame buffer onto the display at the
 * specified coordinates. It is used to update the display with the latest
 * camera frame. After drawing, it returns the frame buffer to the camera for
 * reuse.
 */
/**************************************************************************/
void Adafruit_PyCamera::blitFrame(void) {
  drawRGBBitmap(0, 0, (uint16_t *)fb->getBuffer(), 240, 240);

  esp_camera_fb_return(frame);
}

/**************************************************************************/
/**
 * @brief Initializes the accelerometer.
 *
 * @details This function initializes the accelerometer by setting up the I2C
 * device, checking the chip ID, and configuring the control registers for
 * normal mode, data rate, resolution, and range. It ensures that the
 * accelerometer is ready for data reading.
 *
 * @return bool Returns true if the accelerometer is successfully initialized,
 * false otherwise.
 */
/**************************************************************************/
bool Adafruit_PyCamera::initAccel(void) {
  lis_dev = new Adafruit_I2CDevice(0x19, &Wire);
  if (!lis_dev->begin()) {
    return false;
  }
  Adafruit_BusIO_Register _chip_id =
      Adafruit_BusIO_Register(lis_dev, LIS3DH_REG_WHOAMI, 1);
  if (_chip_id.read() != 0x33) {
    return false;
  }
  Adafruit_BusIO_Register _ctrl1 =
      Adafruit_BusIO_Register(lis_dev, LIS3DH_REG_CTRL1, 1);
  _ctrl1.write(0x07); // enable all axes, normal mode
  Adafruit_BusIO_RegisterBits data_rate_bits =
      Adafruit_BusIO_RegisterBits(&_ctrl1, 4, 4);
  data_rate_bits.write(0b0111); // set to 400Hz update

  Adafruit_BusIO_Register _ctrl4 =
      Adafruit_BusIO_Register(lis_dev, LIS3DH_REG_CTRL4, 1);
  _ctrl4.write(0x88); // High res & BDU enabled
  Adafruit_BusIO_RegisterBits range_bits =
      Adafruit_BusIO_RegisterBits(&_ctrl4, 2, 4);
  range_bits.write(0b11);

  Serial.println("Found LIS3DH");
  return true;
}

/**************************************************************************/
/**
 * @brief Reads accelerometer data.
 *
 * @details This function reads the X, Y, and Z acceleration data from the
 * accelerometer. It sets up the register address for auto-increment to read
 * consecutive data registers and then reads the 6 bytes of data corresponding
 * to the X, Y, and Z axes.
 *
 * @param[out] x Pointer to store the X-axis acceleration data.
 * @param[out] y Pointer to store the Y-axis acceleration data.
 * @param[out] z Pointer to store the Z-axis acceleration data.
 * @return bool Returns true if the data is successfully read, false otherwise.
 */
/**************************************************************************/
bool Adafruit_PyCamera::readAccelData(int16_t *x, int16_t *y, int16_t *z) {
  uint8_t register_address = LIS3DH_REG_OUT_X_L;
  register_address |= 0x80; // set [7] for auto-increment

  Adafruit_BusIO_Register xl_data =
      Adafruit_BusIO_Register(lis_dev, register_address, 6);

  uint8_t buffer[6];
  if (!xl_data.read(buffer, 6))
    return false;

  *x = buffer[0];
  *x |= ((uint16_t)buffer[1]) << 8;
  *y = buffer[2];
  *y |= ((uint16_t)buffer[3]) << 8;
  *z = buffer[4];
  *z |= ((uint16_t)buffer[5]) << 8;

  return true;
}

/**************************************************************************/
/**
 * @brief Reads accelerometer data and converts it to g-force values.
 *
 * @details This function reads the raw accelerometer data for X, Y, and Z axes
 * using readAccelData() and then converts these values to g-force. The
 * conversion factor depends on the accelerometer's sensitivity setting (here
 * assumed for 16G range).
 *
 * @param[out] x_g Pointer to store the X-axis acceleration in g-force.
 * @param[out] y_g Pointer to store the Y-axis acceleration in g-force.
 * @param[out] z_g Pointer to store the Z-axis acceleration in g-force.
 * @return bool Returns true if the data is successfully read and converted,
 * false otherwise.
 */
/**************************************************************************/
bool Adafruit_PyCamera::readAccelData(float *x_g, float *y_g, float *z_g) {
  int16_t x, y, z;
  if (!readAccelData(&x, &y, &z))
    return false;

  uint8_t lsb_value = 48; // for 16G
  *x_g = lsb_value * ((float)x / LIS3DH_LSB16_TO_KILO_LSB10);
  *y_g = lsb_value * ((float)y / LIS3DH_LSB16_TO_KILO_LSB10);
  *z_g = lsb_value * ((float)z / LIS3DH_LSB16_TO_KILO_LSB10);
  return true;
}

/**************************************************************************/
/**
 * @brief Scans the I2C bus and prints the addresses of all connected devices.
 *
 * @details This function iterates through all possible I2C addresses (0x00 to
 * 0x7F) and attempts to initiate a transmission to each. If a device
 * acknowledges the transmission, its address is printed to the Serial output.
 * This is useful for debugging and identifying connected I2C devices.
 */
/**************************************************************************/
void Adafruit_PyCamera::I2Cscan(void) {
  Wire.begin(PYCAM_SDA, PYCAM_SCL);
  Serial.print("I2C Scan: ");
  for (int addr = 0; addr <= 0x7F; addr++) {
    Wire.beginTransmission(addr);
    bool found = (Wire.endTransmission() == 0);
    if (found) {
      Serial.print("0x");
      Serial.print(addr, HEX);
      Serial.print(", ");
    }
  }
  Serial.println();
}

/**************************************************************************/
/**
 * @brief Sets the color of the Neopixel.
 *
 * @param c The color to set the Neopixel to, in 32-bit RGB format.
 *
 * @details This function sets the color of the Neopixel LED. It uses the `fill`
 * method of the Adafruit_NeoPixel class to set all pixels to the specified
 * color and then calls `show` to update the LED with the new color.
 */
/**************************************************************************/
void Adafruit_PyCamera::setNeopixel(uint32_t c) {
  pixel.fill(c);
  pixel.show(); // Initialize all pixels to 'off'
}

/**************************************************************************/
/**
 * @brief Sets the color of the Neopixel Ring.
 *
 * @param c The color to set the Neopixel Ring to, in 32-bit RGB format.
 *
 * @details This function sets the color of the Neopixel Ring. It uses the
 * `fill` method of the Adafruit_NeoPixel class to set all pixels in the ring to
 * the specified color and then calls `show` to update the ring with the new
 * color.
 */
/**************************************************************************/
void Adafruit_PyCamera::setRing(uint32_t c) {
  ring.fill(c);
  ring.show(); // Initialize all pixels to 'off'
}

/**************************************************************************/
/*!
    @brief   Input a value 0 to 255 to get a color value. The colours are a
   transition r - g - b - back to r.
    @param  WheelPos The position in the wheel, from 0 to 255
    @returns  The 0xRRGGBB color
*/
/**************************************************************************/
uint32_t Adafruit_PyCamera::Wheel(byte WheelPos) {
  WheelPos = 255 - WheelPos;
  if (WheelPos < 85) {
    return Adafruit_NeoPixel::Color(255 - WheelPos * 3, 0, WheelPos * 3);
  }
  if (WheelPos < 170) {
    WheelPos -= 85;
    return Adafruit_NeoPixel::Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
  WheelPos -= 170;
  return Adafruit_NeoPixel::Color(WheelPos * 3, 255 - WheelPos * 3, 0);
}
