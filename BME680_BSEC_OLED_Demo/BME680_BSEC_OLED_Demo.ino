// SPDX-FileCopyrightText: 2020 Limor Fried for Adafruit Industries
// SPDX-FileCopyrightText: 2020 Kevin Townsend for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/***************************************************************************
  This is a library for the BME68X gas, humidity, temperature & pressure sensor

  Designed specifically to work with the Adafruit BME68X Breakout
  ----> http://www.adafruit.com/products/3660

  These sensors use I2C or SPI to communicate, 2 or 4 pins are required
  to interface.

  Adafruit invests time and resources providing this open source code,
  please support Adafruit and open-source hardware by purchasing products
  from Adafruit!

  Written by Limor Fried & Kevin Townsend for Adafruit Industries.
  BSD license, all text above must be included in any redistribution
 ***************************************************************************/

#include <Adafruit_SSD1306.h>
#include "bsec.h"

Adafruit_SSD1306 display = Adafruit_SSD1306(128, 64, &Wire);

Bsec iaqSensor;
String output;


void setup() {
  Serial.begin(9600);
  //while (!Serial);
  
  Serial.println(F("BME68X test"));
  
  // SSD1306_SWITCHCAPVCC = generate display voltage from 3.3V internally
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3D)) { // Address 0x3D for 128x64
    Serial.println(F("SSD1306 allocation failed"));
    for(;;); // Don't proceed, loop forever
  }
  Serial.println("OLED begun");

  display.display();
  delay(100);
  display.clearDisplay();
  display.display();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setRotation(0);
  
  iaqSensor.begin(BME68X_I2C_ADDR_LOW, Wire);
  output = "\nBSEC library version " + String(iaqSensor.version.major) + "." + String(iaqSensor.version.minor) + "." + String(iaqSensor.version.major_bugfix) + "." + String(iaqSensor.version.minor_bugfix);
  Serial.println(output);
  checkIaqSensorStatus();
  bsec_virtual_sensor_t sensorList[10] = {
    BSEC_OUTPUT_RAW_TEMPERATURE,
    BSEC_OUTPUT_RAW_PRESSURE,
    BSEC_OUTPUT_RAW_HUMIDITY,
    BSEC_OUTPUT_RAW_GAS,
    BSEC_OUTPUT_IAQ,
    BSEC_OUTPUT_STATIC_IAQ,
    BSEC_OUTPUT_CO2_EQUIVALENT,
    BSEC_OUTPUT_BREATH_VOC_EQUIVALENT,
    BSEC_OUTPUT_SENSOR_HEAT_COMPENSATED_TEMPERATURE,
    BSEC_OUTPUT_SENSOR_HEAT_COMPENSATED_HUMIDITY,
  };

  iaqSensor.updateSubscription(sensorList, 10, BSEC_SAMPLE_RATE_LP);
  checkIaqSensorStatus();
  // Print the header
  output = "Timestamp [ms], raw temperature [°C], pressure [hPa], raw relative humidity [%], gas [Ohm], IAQ, IAQ accuracy, temperature [°C], relative humidity [%], Static IAQ, CO2 equivalent, breath VOC equivalent";
  Serial.println(output);
}

void loop() {
  display.setCursor(0,0);
  display.clearDisplay();

  unsigned long time_trigger = millis();
  if (! iaqSensor.run()) { // If no data is available
    checkIaqSensorStatus();
    return;
  }
  
  output = String(time_trigger);
  output += ", " + String(iaqSensor.rawTemperature);
  output += ", " + String(iaqSensor.pressure);
  output += ", " + String(iaqSensor.rawHumidity);
  output += ", " + String(iaqSensor.gasResistance);
  output += ", " + String(iaqSensor.iaq);
  output += ", " + String(iaqSensor.iaqAccuracy);
  output += ", " + String(iaqSensor.temperature);
  output += ", " + String(iaqSensor.humidity);
  output += ", " + String(iaqSensor.staticIaq);
  output += ", " + String(iaqSensor.co2Equivalent);
  output += ", " + String(iaqSensor.breathVocEquivalent);
  Serial.println(output);

  
  Serial.print("Temperature = "); Serial.print(iaqSensor.temperature); Serial.println(" *C");
  display.print("Temperature: "); display.print(iaqSensor.temperature); display.println(" *C");

  Serial.print("Pressure = "); Serial.print(iaqSensor.pressure / 100.0); Serial.println(" hPa");
  display.print("Pressure: "); display.print(iaqSensor.pressure / 100); display.println(" hPa");

  Serial.print("Humidity = "); Serial.print(iaqSensor.humidity); Serial.println(" %");
  display.print("Humidity: "); display.print(iaqSensor.humidity); display.println(" %");

  Serial.print("IAQ = "); Serial.print(iaqSensor.staticIaq); Serial.println("");
  display.print("IAQ: "); display.print(iaqSensor.staticIaq); display.println("");
  
  Serial.print("CO2 equiv = "); Serial.print(iaqSensor.co2Equivalent); Serial.println("");
  display.print("CO2eq: "); display.print(iaqSensor.co2Equivalent); display.println("");
  
  Serial.print("Breath VOC = "); Serial.print(iaqSensor.breathVocEquivalent); Serial.println("");
  display.print("VOC: "); display.print(iaqSensor.breathVocEquivalent); display.println("");
  
  Serial.println();
  display.display();
  delay(2000);
}


// Helper function definitions
void checkIaqSensorStatus(void)
{
  if (iaqSensor.bsecStatus != BSEC_OK) {
    if (iaqSensor.bsecStatus < BSEC_OK) {
      output = "BSEC error code : " + String(iaqSensor.bsecStatus);
      Serial.println(output);
      display.setCursor(0,0);
      display.println(output);
      display.display();
      for (;;)  delay(10);
    } else {
      output = "BSEC warning code : " + String(iaqSensor.bsecStatus);
      Serial.println(output);
    }
  }

  if (iaqSensor.bme68xStatus != BME68X_OK) {
    if (iaqSensor.bme68xStatus < BME68X_OK) {
      output = "BME68X error code : " + String(iaqSensor.bme68xStatus);
      Serial.println(output);
      display.setCursor(0,0);
      display.println(output);
      display.display();
      for (;;)  delay(10);
    } else {
      output = "BME68X warning code : " + String(iaqSensor.bme68xStatus);
      Serial.println(output);
    }
  }
}
