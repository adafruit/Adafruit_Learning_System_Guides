// SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Uses the Adafruit ESP32-S3 TFT with the MAX3421E FeatherWing
// Acts as a USB keyboard to BLE converter

#include <Arduino.h>
#include "Adafruit_TinyUSB.h"
#include "BLEDevice.h"
#include "BLEHIDDevice.h"
#include "HIDTypes.h"
#include "HIDKeyboardTypes.h"
#include "Adafruit_MAX1704X.h"
#include "Adafruit_LC709203F.h"
#include <Adafruit_ST7789.h> 
#include <Fonts/FreeSans12pt7b.h>

Adafruit_USBH_Host USBHost(&SPI, 10, 9);

#define US_KEYBOARD 1
#define DEVICE_NAME "ESP32 Keyboard"
#define BLE_MANUFACTURER "TinyUSB"

Adafruit_LC709203F lc_bat;
Adafruit_MAX17048 max_bat;

Adafruit_ST7789 display = Adafruit_ST7789(TFT_CS, TFT_DC, TFT_RST);
BLEHIDDevice* hid;
BLECharacteristic* input;
BLECharacteristic* output;
String keyInput = "";

GFXcanvas16 canvas(240, 135);

bool maxfound = false;
bool lcfound = false;
bool isBleConnected = false;

unsigned long previousMillis = 0;
const long interval = 500;

void setup() {
    Serial.begin(115200);
    // while ( !Serial ) delay(10);   // wait for native usb
    // turn on the TFT / I2C power supply
    pinMode(TFT_I2C_POWER, OUTPUT);
    digitalWrite(TFT_I2C_POWER, HIGH);
    pinMode(TFT_BACKLITE, OUTPUT);
    digitalWrite(TFT_BACKLITE, HIGH);
    display.init(135, 240);           // Init ST7789 240x135
    display.setRotation(3);
    canvas.setFont(&FreeSans12pt7b);
    canvas.setTextColor(ST77XX_WHITE);
    canvas.fillScreen(ST77XX_BLACK);
    canvas.setCursor(0, 25);
    canvas.println("Connecting to BLE..");
    display.drawRGBBitmap(0, 0, canvas.getBuffer(), 240, 135);
    // start Bluetooth task
    xTaskCreate(bluetoothTask, "bluetooth", 20000, NULL, 5, NULL);
    canvas.fillScreen(ST77XX_BLACK);
    canvas.setCursor(0, 25);
    canvas.println("BLE Connected!");
    canvas.println("Finding USB device..");
    display.drawRGBBitmap(0, 0, canvas.getBuffer(), 240, 135);
    // init host stack on controller (rhport) 1
    USBHost.begin(1);
    Serial.println("TinyUSB Dual: HID Device to ESP BLE Keyboard");
    canvas.fillScreen(ST77XX_BLACK);
    canvas.setCursor(0, 25);
    canvas.println("BLE Connected!");
    canvas.println("USB Connected!");
    display.drawRGBBitmap(0, 0, canvas.getBuffer(), 240, 135);
    
  if (lc_bat.begin()) {
    Serial.println("Found LC709203F");
    Serial.print("Version: 0x"); Serial.println(lc_bat.getICversion(), HEX);
    lc_bat.setPackSize(LC709203F_APA_500MAH);
    lcfound = true;
  }
  else {
    Serial.println(F("Couldnt find Adafruit LC709203F?\nChecking for Adafruit MAX1704X.."));
    delay(200);
    if (!max_bat.begin()) {
      Serial.println(F("Couldnt find Adafruit MAX1704X?\nMake sure a battery is plugged in!"));
      while (1) delay(10);
    }
    Serial.print(F("Found MAX17048"));
    Serial.print(F(" with Chip ID: 0x")); 
    Serial.println(max_bat.getChipID(), HEX);
    maxfound = true;
  }
}

void loop() {  
  unsigned long currentMillis = millis();
  USBHost.task();
  //Serial.flush();
  if (currentMillis - previousMillis >= interval) {
      previousMillis = currentMillis;
      canvas.fillScreen(ST77XX_BLACK);
      canvas.setCursor(0, 25);
      canvas.setTextColor(ST77XX_RED);
      canvas.println("Adafruit Feather");
      canvas.setTextColor(ST77XX_YELLOW);
      canvas.println("USB Host -> BLE");
      canvas.setTextColor(ST77XX_GREEN); 
      canvas.print("Battery: ");
      canvas.setTextColor(ST77XX_WHITE);
      if (lcfound == true) {
        canvas.print(lc_bat.cellVoltage(), 1);
        canvas.print(" V  /  ");
        canvas.print(lc_bat.cellPercent(), 0);
        canvas.println("%");
        hid->setBatteryLevel(lc_bat.cellPercent());
      } else {
        canvas.print(max_bat.cellVoltage(), 1);
        canvas.print(" V  /  ");
        canvas.print(max_bat.cellPercent(), 0);
        canvas.println("%");
        hid->setBatteryLevel(max_bat.cellPercent());
      }
      canvas.setTextColor(ST77XX_BLUE); 
      canvas.print("Sent: ");
      canvas.setTextColor(ST77XX_WHITE);
      canvas.println(keyInput);
      display.drawRGBBitmap(0, 0, canvas.getBuffer(), 240, 135);
      
    }
}
void tuh_hid_report_received_cb(uint8_t dev_addr, uint8_t instance, uint8_t const *msg, uint16_t len);


// Message (report) sent when a key is pressed or released
struct InputReport {
    uint8_t modifiers;       // bitmask: CTRL = 1, SHIFT = 2, ALT = 4
    uint8_t reserved;        // must be 0
    uint8_t pressedKeys[6];  // up to six concurrenlty pressed keys
};

// The report map describes the HID device (a keyboard in this case) and
// the messages (reports in HID terms) sent and received.
static const uint8_t REPORT_MAP[] = {
    USAGE_PAGE(1),      0x01,       // Generic Desktop Controls
    USAGE(1),           0x06,       // Keyboard
    COLLECTION(1),      0x01,       // Application
    REPORT_ID(1),       0x01,       //   Report ID (1)
    USAGE_PAGE(1),      0x07,       //   Keyboard/Keypad
    USAGE_MINIMUM(1),   0xE0,       //   Keyboard Left Control
    USAGE_MAXIMUM(1),   0xE7,       //   Keyboard Right Control
    LOGICAL_MINIMUM(1), 0x00,       //   Each bit is either 0 or 1
    LOGICAL_MAXIMUM(1), 0x01,
    REPORT_COUNT(1),    0x08,       //   8 bits for the modifier keys
    REPORT_SIZE(1),     0x01,       
    HIDINPUT(1),        0x02,       //   Data, Var, Abs
    REPORT_COUNT(1),    0x01,       //   1 byte (unused)
    REPORT_SIZE(1),     0x08,
    HIDINPUT(1),        0x01,       //   Const, Array, Abs
    REPORT_COUNT(1),    0x06,       //   6 bytes (for up to 6 concurrently pressed keys)
    REPORT_SIZE(1),     0x08,
    LOGICAL_MINIMUM(1), 0x00,
    LOGICAL_MAXIMUM(1), 0x65,       //   101 keys
    USAGE_MINIMUM(1),   0x00,
    USAGE_MAXIMUM(1),   0x65,
    HIDINPUT(1),        0x00,       //   Data, Array, Abs
    REPORT_COUNT(1),    0x05,       //   5 bits (Num lock, Caps lock, Scroll lock, Compose, Kana)
    REPORT_SIZE(1),     0x01,
    USAGE_PAGE(1),      0x08,       //   LEDs
    USAGE_MINIMUM(1),   0x01,       //   Num Lock
    USAGE_MAXIMUM(1),   0x05,       //   Kana
    LOGICAL_MINIMUM(1), 0x00,
    LOGICAL_MAXIMUM(1), 0x01,
    HIDOUTPUT(1),       0x02,       //   Data, Var, Abs
    REPORT_COUNT(1),    0x01,       //   3 bits (Padding)
    REPORT_SIZE(1),     0x03,
    HIDOUTPUT(1),       0x01,       //   Const, Array, Abs
    END_COLLECTION(0)               // End application collection
};

const InputReport NO_KEY_PRESSED = { };

/*
 * Callbacks related to BLE connection
 */
class BleKeyboardCallbacks : public BLEServerCallbacks {

    void onConnect(BLEServer* server) {
        isBleConnected = true;

        // Allow notifications for characteristics
        BLE2902* cccDesc = (BLE2902*)input->getDescriptorByUUID(BLEUUID((uint16_t)0x2902));
        cccDesc->setNotifications(true);

        Serial.println("Client has connected");
    }

    void onDisconnect(BLEServer* server) {
        isBleConnected = false;

        // Disallow notifications for characteristics
        BLE2902* cccDesc = (BLE2902*)input->getDescriptorByUUID(BLEUUID((uint16_t)0x2902));
        cccDesc->setNotifications(false);

        Serial.println("Client has disconnected");
    }
};

void bluetoothTask(void*) {

    BLEDevice::init(DEVICE_NAME);
    BLEServer* server = BLEDevice::createServer();
    server->setCallbacks(new BleKeyboardCallbacks());

    // create an HID device
    hid = new BLEHIDDevice(server);
    input = hid->inputReport(1); // report ID

    // set manufacturer name
    hid->manufacturer()->setValue(BLE_MANUFACTURER);
    // set USB vendor and product ID
    hid->pnp(0x02, 0xe502, 0xa111, 0x0210);
    // information about HID device: device is not localized, device can be connected
    hid->hidInfo(0x00, 0x02);
    // Security: device requires bonding
    BLESecurity* security = new BLESecurity();
    security->setAuthenticationMode(ESP_LE_AUTH_BOND);

    // set report map
    hid->reportMap((uint8_t*)REPORT_MAP, sizeof(REPORT_MAP));
    hid->startServices();

    // set battery level to 100%
    hid->setBatteryLevel(100);

    // advertise the services
    BLEAdvertising* advertising = server->getAdvertising();
    advertising->setAppearance(HID_KEYBOARD);
    advertising->addServiceUUID(hid->hidService()->getUUID());
    advertising->addServiceUUID(hid->deviceInfo()->getUUID());
    advertising->addServiceUUID(hid->batteryService()->getUUID());
    advertising->start();

    Serial.println("BLE ready");
    delay(portMAX_DELAY);
};

extern "C" {

// Invoked when device with hid interface is mounted
// Report descriptor is also available for use.
// tuh_hid_parse_report_descriptor() can be used to parse common/simple enough
// descriptor. Note: if report descriptor length > CFG_TUH_ENUMERATION_BUFSIZE,
// it will be skipped therefore report_desc = NULL, desc_len = 0
void tuh_hid_mount_cb(uint8_t dev_addr, uint8_t instance, uint8_t const *desc_report, uint16_t desc_len) {
  
  (void) desc_report;
  (void) desc_len;
  uint16_t vid, pid;
  tuh_vid_pid_get(dev_addr, &vid, &pid);
  
  Serial.printf("HID device address = %d, instance = %d is mounted\r\n", dev_addr, instance);
  Serial.printf("VID = %04x, PID = %04x\r\n", vid, pid);
  hid->pnp(0x02, vid, 0xa111, pid);
  if (!tuh_hid_receive_report(dev_addr, instance)) {
    Serial.printf("Error: cannot request to receive report\r\n");
  }
}

// Invoked when device with hid interface is un-mounted
void tuh_hid_umount_cb(uint8_t dev_addr, uint8_t instance) {
  Serial.printf("HID device address = %d, instance = %d is unmounted\r\n", dev_addr, instance);
}

// Invoked when received report from device via interrupt endpoint
void tuh_hid_report_received_cb(uint8_t dev_addr, uint8_t instance, uint8_t const *msg, uint16_t len) {
  // continue to request to receive report
  //unsigned long a = millis();
    if (!isBleConnected) return;
    //Serial.println(messageLength);
    if (msg[2] != 0) {
      for (uint8_t i = 2; i < len; i++) {
          // translate character to key combination
          // Assuming your USB message fits the format required by the BLE keyboard
          // You might need to adjust this depending on your actual USB message format
          
          InputReport report = {
              .modifiers = msg[0], // No modifier for now
              .reserved = 0,
              .pressedKeys = {msg[i], 0, 0, 0, 0, 0}
          };
          input->setValue((uint8_t*)&report, sizeof(report));
          input->notify();
          delay(1);
          // release all keys between two characters; otherwise two identical
          // consecutive characters are treated as just one key press
          input->setValue((uint8_t*)&NO_KEY_PRESSED, sizeof(NO_KEY_PRESSED));
          input->notify();
          delay(1);
        }
      char formattedString[6]; // Large enough for "0x" + 2 hex digits + null terminator
      sprintf(formattedString, "0x%02X", msg[2]);
      //if (strcmp(formattedString, "0x00") != 0) {
      keyInput = "";
      keyInput = formattedString;
        //Serial.println(keyInput);
      //}
    }
  //sendUSBMessageOverBLE(report, len);
  if (!tuh_hid_receive_report(dev_addr, instance)) {
    Serial.printf("Error: cannot request to receive report\r\n");
  }
  //unsigned long b = millis();
  //Serial.println(b-a);
}

} // extern C
