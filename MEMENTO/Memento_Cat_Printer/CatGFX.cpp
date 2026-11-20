// SPDX-FileCopyrightText: 2022 Claus Näveke
//
// SPDX-License-Identifier: Unlicense
// https://github.com/TheNitek/CatGFX

#include "CatGFX.h"

CatPrinter::CatPrinter(uint16_t h): 
  Adafruit_GFX(384, h),
  WIDTH_BYTE((WIDTH + 7)/8),
  SERVICE_UUID("0000AE30-0000-1000-8000-00805F9B34FB"),
  CHAR_UUID_DATA("0000AE01-0000-1000-8000-00805F9B34FB")
{
  if (this->NAME_ARRAY_SIZE >= 5)
  {
    strcpy(this->printerNames[0], "GT01");
    strcpy(this->printerNames[1], "GB01");
    strcpy(this->printerNames[2], "GB02");
    strcpy(this->printerNames[3], "MX09");
    strcpy(this->printerNames[4], "MX06");
    for (int i = 4; i < this->NAME_ARRAY_SIZE; i ++)
    strcpy(this->printerNames[i], "");
  }
  else if (this->NAME_ARRAY_SIZE >= 1)
    strcpy(this->printerNames[0], "");
}

void CatPrinter::begin(byte *buffer, uint16_t size) {
  pixelBuffer = buffer;
  pixelBufferSize = size;

  BTStatus status = BLE.begin("ESP32");
  if (!status) {
    Serial.printf("BLE init failed: %s\n", status.toString());
    return;
  }
  BLE.getScan().setActiveScan(true); // Printer names arrive in scan responses
}

void CatPrinter::fillBuffer(const byte value) {
  if (pixelBuffer != nullptr)
    memset(pixelBuffer, value, pixelBufferSize);
}

bool CatPrinter::connect(void) {
  // Scan for 5 seconds, then pick the first device whose name is on the list.
  blePrinterAddress = BTAddress();
  BLEScan::Results results = BLE.getScan().startBlocking(5000);
  for (const BLEAdvertisedDevice &dev : results) {
    if (isPrinterName(dev.getName().c_str())) {
      blePrinterAddress = dev.getAddress();
      Serial.print("Found Printer: ");
      Serial.println(blePrinterAddress.toString());
      break;
    }
  }
  if (!blePrinterAddress) {
    return false;
  }
  return connect(blePrinterAddress);
}

bool CatPrinter::connect(BTAddress &address) {
  // A fresh client per connection; assigning releases any previous one.
  bleClient = BLE.createClient();
  if (!bleClient) {
    Serial.println("Could not create BLE client");
    return false;
  }
  BTStatus status = bleClient.connect(address);
  if (!status) {
    Serial.printf("Connect failed: %s\n", status.toString());
    return false;
  }
  if (!bleClient.discoverServices()) {
    bleClient.disconnect();
    Serial.println("Service discovery failed");
    return false;
  }

  BLERemoteService remoteService = bleClient.getService(SERVICE_UUID);
  if (remoteService) {
    remoteCharacteristicData = remoteService.getCharacteristic(CHAR_UUID_DATA);
    if (remoteCharacteristicData) {
      Serial.println("Got data transfer characteristic!");
      return true;
    }
    bleClient.disconnect();
    Serial.println("Data characteristic not found");
  }
  else {
      bleClient.disconnect();
      Serial.println("Data service not found");
  }
  return false;
}

void CatPrinter::disconnect(void) {
  if (bleClient) {
    bleClient.disconnect();
  }
  remoteCharacteristicData = BLERemoteCharacteristic();
  blePrinterAddress = BTAddress();
}

void CatPrinter::sendLine(const byte *data, const uint8_t len, const bool compressed) {
  //Serial.println("send line..");
  if(compressed) {
    //Serial.println("compressed");
    byte comp[WIDTH_BYTE] = {0};
    uint8_t cb = 0;

    // Get color of first pixel
    comp[0] = data[0] & 0x80;

    for (uint16_t i=0; i<len; i++) {
      for(uint8_t j=0; j<8; j++) {
        if(((data[i] >> (7-j)) & 0x01) != (comp[cb] >> 7) || ((comp[cb] & 0x7F) == 0x7F)) {
          cb++;
          if(cb >= WIDTH_BYTE) {
            // Not a compressable line, so dont
            sendLine(data, len, false);
            return;
          }
          comp[cb] = ((data[i] >> (7-j)) & 0x01) << 7;
        }
        comp[cb]++;
      }
    }
    cb++;
    sendCmd(CatPrinter::Cmd::PRINT_COMPRESSED, comp, cb);
  } else  {
    //Serial.println("not compressed");
    byte buff[WIDTH_BYTE];
  //delay(200);
    for (uint8_t i=0; i<len; i++) {
      buff[i] = MIRROR_TABLE[data[i]];
    }
  //Serial.println("sending command..");
    sendCmd(CatPrinter::Cmd::PRINT, buff, len);
  delay(10);
  }
}

void CatPrinter::feed(uint8_t lines) {
  byte data[] = {lines, 0};
  sendCmd(CatPrinter::Cmd::PAPER_FEED,  data, sizeof(data));
}

void CatPrinter::printBuffer(void) {
  Serial.println("print buffer..");
  startGraphics();

  // Print the graphics
  byte *s = pixelBuffer;
  for (uint16_t y=0; y<HEIGHT; y++) {
  //delay(10);
    sendLine(s, WIDTH_BYTE, false);
    s += WIDTH_BYTE;
    // Stop if the rest of the buffer is empty
    if(s[0] == 0 && !memcmp(s, s+1, (HEIGHT-y-1)*WIDTH_BYTE-1)) {
      break;
    }
  }
  //Serial.println("end of print buffer");
  endGraphics();
}

bool CatPrinter::isPrinterName(const char *name) const {
  for (uint8_t i = 0; i < NAME_ARRAY_SIZE && strcmp(printerNames[i], "") != 0; i++) {
    if (strcmp(name, printerNames[i]) == 0) {
      return true;
    }
  }
  return false;
}


void CatPrinter::sendCmd(const CatPrinter::Cmd cmd, const byte *data, const uint8_t len) {
  //Serial.println("send cmd");
    byte buffer[WIDTH_BYTE+8] = {0x51, 0x78};
    buffer[2] = static_cast<byte>(cmd);
    buffer[4] = len;
    memcpy(buffer + 6, data, len);
    buffer[6 + len] = crc(data, len);
    buffer[6 + len + 1] = 0xFF;

    writeData(buffer, len+8);
  delay(10);
}

byte CatPrinter::crc(const byte *data, const uint8_t len) {
  byte cs = 0;

  for (uint8_t i=0; i<len; i++) {
    cs = CRC_TABLE[(cs ^ data[i])];
  }
  return cs;
}

void CatPrinter::writeData(byte *data, uint8_t len) {
  //Serial.println("write data");
  if (!bleClient || !bleClient.isConnected() || !remoteCharacteristicData) {
      return;
  }

  // Write in smaller packages, because bigger ones don't work for unkown reason
  while (len > PACKET_SIZE) {
    delay(2);
      Serial.print(".");
      remoteCharacteristicData.writeValue(data, PACKET_SIZE, false);
      data += PACKET_SIZE;
      len -= PACKET_SIZE;
    //Serial.println("wrote packet, len > packet_size");
    //delay(200);
  }
  if (len) {
  delay(2);
    remoteCharacteristicData.writeValue(data, len, false);
  //delay(200);
    Serial.println(".");
  //Serial.println("wrote packet, len < packet_size");
  }
}

void CatPrinter::startGraphics(void) {
  Serial.println("starting graphics..");
  byte data[2] = {0x80, 0x3E};
  sendCmd(CatPrinter::Cmd::ENERGY, data, 2);
  //delay(10);
  data[0] = 0x33;
  sendCmd(CatPrinter::Cmd::QUALITY, data, 1);
  //delay(10);
  data[0] = 0x00;
  sendCmd(CatPrinter::Cmd::DRAWING_MODE, data, 1);
  //delay(10);
  sendCmd(CatPrinter::Cmd::LATTICE, LATTICE_START, sizeof(LATTICE_START));
  //delay(10);
}

void CatPrinter::endGraphics(void) {
  sendCmd(CatPrinter::Cmd::LATTICE, LATTICE_END, sizeof(LATTICE_END));
  delay(200);
  Serial.println("ended graphics");
}

void CatPrinter::drawPixel(int16_t x, int16_t y, uint16_t color) {
  if ((x < 0) || (x >= width()) || (y < 0) || (y >= height())) {
    // Out of bounds
    return;
  }
  uint16_t byteNo = x/8 + (y * WIDTH_BYTE);
  uint8_t bitNo = 7-(x%8);
  pixelBuffer[byteNo] = (pixelBuffer[byteNo] & ~(1 << bitNo)) | ((!color ? 1 : 0) << bitNo);
}

void CatPrinter::fillScreen(uint16_t color) {
  fillBuffer((!color ? 0xFF : 0x00));
}

void CatPrinter::resetNameArray(void)
{
  for (uint8_t i = 0; i < this->NAME_ARRAY_SIZE; i ++)
    strcpy(this->printerNames[i], "");
}

bool CatPrinter::addNameArray(char *newname)
{
  uint8_t i = 0;

  if (strlen(newname) >= NAME_STRING_SIZE)
    return (false);
  while (i < this->NAME_ARRAY_SIZE)
  {
    if (strcmp(this->printerNames[i], "") != 0)
      i ++;
    else
      break ;
  }
  if (i >= this->NAME_ARRAY_SIZE - 1)
    return (false);
  strcpy(this->printerNames[i], newname);
  return (true);
}

void CatPrinter::printNameArray(void)
{
  for (uint8_t i = 0; i < NAME_ARRAY_SIZE; i ++)
    Serial.println(this->printerNames[i]);
}
