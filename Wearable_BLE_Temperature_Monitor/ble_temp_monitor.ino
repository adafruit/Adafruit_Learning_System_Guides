// SPDX-FileCopyrightText: 2020 Brent Rubell for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*********************************************************************
 Learn Guide: BLE Temperature Monitoring Armband

 Adafruit invests time and resources providing this open source code,
 please support Adafruit and open-source hardware by purchasing
 products from Adafruit!

 MIT license, check LICENSE for more information
 All text above, and the splash screen below must be included in
 any redistribution
*********************************************************************/
#include <bluefruit.h>
#include <Adafruit_LittleFS.h>
#include <InternalFileSystem.h>
#include <Wire.h>
#include <Adafruit_NeoPixel.h>
#include "Adafruit_MCP9808.h"

// Read temperature in degrees Fahrenheit
#define TEMPERATURE_F
// uncomment the following line if you want to read temperature in degrees Celsius
//#define TEMPERATURE_C

// Feather NRF52840 Built-in NeoPixel
#define PIN 16
Adafruit_NeoPixel pixels(1, PIN, NEO_GRB + NEO_KHZ800);

// Maximum temperature value for armband's fever indicator
// NOTE: This is in degrees Fahrenheit
float fever_temp = 100.4;

// temperature calibration offset is +0.5 to +1.0 degree
// to make axillary temperature comparible to ear or temporal.
float temp_offset = 0.5;

// Sensor read delay, in minutes
int sensor_delay = 1;

// Measuring your armpit temperature for a minimum of 12 minutes
// is equivalent to measuring your core body temperature.
int calibration_time = 12;

// BLE transmit buffer
char temperature_buf [8];

// BLE Service
BLEDfu  bledfu;  // OTA DFU service
BLEDis  bledis;  // device information
BLEUart bleuart; // uart over ble
BLEBas  blebas;  // battery

// Create the MCP9808 temperature sensor object
Adafruit_MCP9808 tempsensor = Adafruit_MCP9808();

void setup() {
  Serial.begin(115200);
  Serial.println("Wearable BlueFruit Temperature Sensor");
  Serial.println("-------------------------------------\n");


  if (!tempsensor.begin(0x18)) {
    Serial.println("Couldn't find MCP9808! Check your connections and verify the address is correct.");
    while (1);
  }
  Serial.println("Found MCP9808!");

  // Sets the resolution of reading
  tempsensor.setResolution(3);

  // Configure BLE
  // Setup the BLE LED to be enabled on CONNECT
  // Note: This is actually the default behaviour, but provided
  // here in case you want to control this LED manually via PIN 19
  Bluefruit.autoConnLed(true);

  // Config the peripheral connection with maximum bandwidth 
  Bluefruit.configPrphBandwidth(BANDWIDTH_MAX);

  Bluefruit.begin();
  Bluefruit.setTxPower(4);    // Check bluefruit.h for supported values
  Bluefruit.setName("Bluefruit52");
  Bluefruit.Periph.setConnectCallback(connect_callback);
  Bluefruit.Periph.setDisconnectCallback(disconnect_callback);

  // To be consistent OTA DFU should be added first if it exists
  bledfu.begin();

  // Configure and Start Device Information Service
  bledis.setManufacturer("Adafruit Industries");
  bledis.setModel("Bluefruit Feather52");
  bledis.begin();

  // Configure and Start BLE Uart Service
  bleuart.begin();

  // Start BLE Battery Service
  blebas.begin();
  blebas.write(100);

  // Set up and start advertising
  startAdv();

  Serial.println("Please use Adafruit's Bluefruit LE app to connect in UART mode");

  // initialize neopixel object
  pixels.begin();

  // set all pixel colors to 'off'
  pixels.clear();
}

void loop() {

  // wakes up MCP9808 - power consumption ~200 mikro Ampere
  Serial.println("Wake up MCP9808");
  tempsensor.wake();

  // read and print the temperature
  Serial.print("Temp: "); 
  #if defined(TEMPERATURE_F)
    float temp = tempsensor.readTempF();
    // add temperature offset
    temp += temp_offset;
    Serial.print(temp);
    Serial.println("*F.");
  #elif defined(TEMPERATURE_C)
    float temp = tempsensor.readTempC();
    // add temperature offset
    temp += temp_offset;
    Serial.print(temp);
    Serial.println("*C.");
  #else
    #warning "Must define TEMPERATURE_C or TEMPERATURE_F!"
  #endif

  // set NeoPixels to RED if fever_temp
  if (temp >= fever_temp) {
    pixels.setPixelColor(1, pixels.Color(255, 0, 0));
    pixels.show();
  }

  // float to buffer
  snprintf(temperature_buf, sizeof(temperature_buf) - 1, "%0.*f", 1, temp);

  if (calibration_time == 0) {
      Serial.println("Writing to UART");
      // write to UART
      bleuart.write(temperature_buf);
  }
  else {
    Serial.print("Calibration time:");
    Serial.println(calibration_time);
    calibration_time-=1;
  }

  // shutdown MSP9808 - power consumption ~0.1 mikro Ampere
  Serial.println("Shutting down MCP9808");
  tempsensor.shutdown_wake(1);

  // sleep for sensor_delay minutes
  // NOTE: NRF delay() puts mcu into a low-power sleep mode
  delay(1000*60*sensor_delay);
}

void startAdv(void)
{
  // Advertising packet
  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  Bluefruit.Advertising.addTxPower();

  // Include bleuart 128-bit uuid
  Bluefruit.Advertising.addService(bleuart);

  // Secondary Scan Response packet (optional)
  // Since there is no room for 'Name' in Advertising packet
  Bluefruit.ScanResponse.addName();
  
  /* Start Advertising
   * - Enable auto advertising if disconnected
   * - Interval:  fast mode = 20 ms, slow mode = 152.5 ms
   * - Timeout for fast mode is 30 seconds
   * - Start(timeout) with timeout = 0 will advertise forever (until connected)
   * 
   * For recommended advertising interval
   * https://developer.apple.com/library/content/qa/qa1931/_index.html   
   */
  Bluefruit.Advertising.restartOnDisconnect(true);
  Bluefruit.Advertising.setInterval(32, 244);    // in unit of 0.625 ms
  Bluefruit.Advertising.setFastTimeout(30);      // number of seconds in fast mode
  Bluefruit.Advertising.start(0);                // 0 = Don't stop advertising after n seconds  
}

// callback invoked when central connects
void connect_callback(uint16_t conn_handle)
{
  // Get the reference to current connection
  BLEConnection* connection = Bluefruit.Connection(conn_handle);

  char central_name[32] = { 0 };
  connection->getPeerName(central_name, sizeof(central_name));

  Serial.print("Connected to ");
  Serial.println(central_name);
}

/**
 * Callback invoked when a connection is dropped
 * @param conn_handle connection where this event happens
 * @param reason is a BLE_HCI_STATUS_CODE which can be found in ble_hci.h
 */
void disconnect_callback(uint16_t conn_handle, uint8_t reason)
{
  (void) conn_handle;
  (void) reason;

  Serial.println();
  Serial.print("Disconnected, reason = 0x"); Serial.println(reason, HEX);
}
