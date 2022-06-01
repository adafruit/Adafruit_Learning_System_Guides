// SPDX-FileCopyrightText: 2022 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_I2CDevice.h>  // requires https://github.com/adafruit/Adafruit_BusIO
#include <Adafruit_SSD1306.h>
#include <Fonts/FreeSans9pt7b.h>

#define SR04_I2CADDR 0x57
Adafruit_I2CDevice sonar_dev = Adafruit_I2CDevice(SR04_I2CADDR);
// dont have a i2c device on bus faster than 100KHz, doesnt like it!
Adafruit_SSD1306 display = Adafruit_SSD1306(128, 64, &Wire1); // connect to stemma qt - Wire1!


void setup() {
  Serial.begin(115200);

  // SSD1306_SWITCHCAPVCC = generate display voltage from 3.3V internally
  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3D)) {
    Serial.println(F("SSD1306 allocation failed"));
    for(;;); // Don't proceed, loop forever
  }
  
  display.display();
  delay(1000);

  //while (!Serial);

  // Clear the buffer.
  display.clearDisplay();
  display.display();
  display.setFont(&FreeSans9pt7b);
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);  
    
  if (! sonar_dev.begin(&Wire)) {
    Serial.println("Could not find I2C sonar!");
    while (1);
  }
  Serial.println("Found RCWL I2C sonar!");
}

void loop() {
  delay(50);
  uint32_t distance = ping_mm();
  delay(50);
  
  display.clearDisplay();

  display.setCursor(0, 30);
  display.print("I2C Sonar");
  display.setCursor(0, 50);
  
  display.print("Ping: "); 
  if (distance > 2) {
    display.print(distance, DEC); display.println(" mm");
  }

  Serial.print("Ping mm: "); Serial.println(distance);
  
  yield();
  display.display();
}

uint32_t ping_mm()
{
  uint32_t distance = 0;
  byte buffer[3];
  buffer[0] = 1;
  // write one byte then read 3 bytes
  if (! sonar_dev.write(buffer, 1)) {
    return 0;
  }
  delay(10);  // wait for the ping echo
  if (! sonar_dev.read(buffer, 3)) {
    return 0;
  }
  
  distance = ((uint32_t)buffer[0] << 16) | ((uint32_t)buffer[1] << 8) | buffer[2];
  distance /= 1000;
  
  if ((distance <= 1) || (distance >= 4500)) {   // reject readings too low and too high
    return 0;
  }

  return distance;
}
