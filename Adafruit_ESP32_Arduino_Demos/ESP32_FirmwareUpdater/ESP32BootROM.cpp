// SPDX-FileCopyrightText: 2015 Arduino SA
//
// SPDX-License-Identifier: GPL-2.1-or-later
/*
  ESP32BootROM - part of the Firmware Updater for the
  Arduino MKR WiFi 1010, Arduino MKR Vidor 4000, and Arduino UNO WiFi Rev.2.

  Copyright (c) 2018 Arduino SA. All rights reserved.

  This library is free software; you can redistribute it and/or
  modify it under the terms of the GNU Lesser General Public
  License as published by the Free Software Foundation; either
  version 2.1 of the License, or (at your option) any later version.

  This library is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
  Lesser General Public License for more details.

  You should have received a copy of the GNU Lesser General Public
  License along with this library; if not, write to the Free Software
  Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
*/

#include "ESP32BootROM.h"

//#define DEBUG 1

ESP32BootROMClass::ESP32BootROMClass(HardwareSerial& serial, int gpio0Pin, int resetnPin) :
  _serial(&serial),
  _gpio0Pin(gpio0Pin),
  _resetnPin(resetnPin)
{

}

int ESP32BootROMClass::begin(unsigned long baudrate)
{
  _serial->begin(115200);

  pinMode(_gpio0Pin, OUTPUT);
  pinMode(_resetnPin, OUTPUT);

  digitalWrite(_gpio0Pin, LOW);

  digitalWrite(_resetnPin, LOW);
  delay(10);
  digitalWrite(_resetnPin, HIGH);
  delay(100);

  int synced = 0;

  for (int retries = 0; !synced && (retries < 5); retries++) {
    synced = sync();
  }

  if (!synced) {
    return 0;
  }

#if defined(ARDUINO_SAMD_MKRVIDOR4000) || defined(ARDUINO_AVR_UNO_WIFI_REV2)
  (void)baudrate;
#else
  if (baudrate != 115200) {
    if (!changeBaudrate(baudrate)) {
      return 0;
    }

    delay(100);

    _serial->end();
    _serial->begin(baudrate);
  }
#endif

  if (!spiAttach()) {
    return 0;
  }

  return 1;
}

void ESP32BootROMClass::end() {
  _serial->end();
}

int ESP32BootROMClass::sync()
{
  const uint8_t data[] = {
    0x07, 0x07, 0x12, 0x20,
    0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55
  };

  command(0x08, data, sizeof(data));

  int results[8];

  for (int i = 0; i < 8; i++) {
    results[i] = response(0x08, 100);
  }

  return (results[0] == 0);
}

int ESP32BootROMClass::changeBaudrate(unsigned long baudrate)
{
  const uint32_t data[2] = {
    baudrate,
    0
  };

  command(0x0f, data, sizeof(data));

  return (response(0x0f, 3000) == 0);
}

int ESP32BootROMClass::spiAttach()
{
  const uint8_t data[] = {
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
  };

  command(0x0d, data, sizeof(data));

  return (response(0x0d, 3000) == 0);
}

int ESP32BootROMClass::beginFlash(uint32_t offset, uint32_t size, uint32_t chunkSize) {
  const uint32_t data[4] = {
    size,
    size / chunkSize,
    chunkSize,
    offset
  };

  command(0x02, data, sizeof(data));

  _flashSequenceNumber = 0;
  _chunkSize = chunkSize;

  return (response(0x02, 120000) == 0);
}

int ESP32BootROMClass::dataFlash(const void* data, uint32_t length)
{
  uint32_t cmdData[4 + (_chunkSize / 4)];

  cmdData[0] = length;
  cmdData[1] = _flashSequenceNumber++;
  cmdData[2] = 0;
  cmdData[3] = 0;

  memcpy(&cmdData[4], data, length);

  if (length < _chunkSize) {
    memset(&cmdData[4 + (length / 4)], 0xff, _chunkSize - length);
  }

  command(0x03, cmdData, sizeof(cmdData));

  return (response(0x03, 3000) == 0);
}

int ESP32BootROMClass::endFlash(uint32_t reboot) {
  const uint32_t data[1] = {
    reboot
  };

  command(0x04, data, sizeof(data));

  return (response(0x04, 3000) == 0);
}

int ESP32BootROMClass::md5Flash(uint32_t offset, uint32_t size, uint8_t* result)
{
  const uint32_t data[4] = {
    offset,
    size,
    0,
    0
  };

  command(0x13, data, sizeof(data));

  uint8_t asciiResult[32];

  if (response(0x13, 3000, asciiResult) != 0) {
    return 0;
  }

  char temp[3] = { 0, 0, 0 };

  for (int i = 0; i < 16; i++) {
    temp[0] = asciiResult[i * 2];
    temp[1] = asciiResult[i * 2 + 1];

    result[i] = strtoul(temp, NULL, 16);
  }

  return 1;
}

void ESP32BootROMClass::command(int opcode, const void* data, uint16_t length)
{
  uint32_t checksum = 0;

  if (opcode == 0x03) {
    checksum = 0xef; // seed

    for (uint16_t i = 16; i < length; i++) {
      checksum ^= ((const uint8_t*)data)[i];
    }
  }

  _serial->write(0xc0);
  _serial->write((uint8_t)0x00); // direction
  _serial->write(opcode);
  _serial->write((uint8_t*)&length, sizeof(length));
  writeEscapedBytes((uint8_t*)&checksum, sizeof(checksum));
  writeEscapedBytes((uint8_t*)data, length);
  _serial->write(0xc0);
#ifdef ARDUINO_SAMD_MKRVIDOR4000
  // _serial->flush(); // doesn't work!
#else
  _serial->flush();
#endif
}

int ESP32BootROMClass::response(int opcode, unsigned long timeout, void* body)
{
  uint8_t data[10 + 256];
  uint16_t index = 0;

  uint8_t responseLength = 4;

  for (unsigned long start = millis(); (index < (uint16_t)(10 + responseLength)) && (millis() - start) < timeout;) {
    if (_serial->available()) {
      data[index] = _serial->read();

      if (index == 3) {
        responseLength = data[index];
      }

      index++;
    }
  }

#ifdef DEBUG
  if (index) {
    for (int i = 0; i < index; i++) {
      byte b = data[i];

      if (b < 0x10) {
        Serial.print('0');
      }

      Serial.print(b, HEX);
      Serial.print(' ');
    }
    Serial.println();
  }
#endif

  if (index != (uint16_t)(10 + responseLength)) {
    return -1;
  }

  if (data[0] != 0xc0 || data[1] != 0x01 || data[2] != opcode || data[responseLength + 5] != 0x00 || data[responseLength + 6] != 0x00 || data[responseLength + 9] != 0xc0) {
    return -1;
  }

  if (body) {
    memcpy(body, &data[9], responseLength - 4);
  }

  return data[responseLength + 5];
}

void ESP32BootROMClass::writeEscapedBytes(const uint8_t* data, uint16_t length)
{
  uint16_t written = 0;

  while (written < length) {
    uint8_t b = data[written++];

    if (b == 0xdb) {
      _serial->write(0xdb);
      _serial->write(0xdd);
    } else if (b == 0xc0) {
      _serial->write(0xdb);
      _serial->write(0xdc);
    } else {
      _serial->write(b);
    }
  }
}

ESP32BootROMClass ESP32BootROM(SerialNina, NINA_GPIO0, NINA_RESETN);
