// SPDX-FileCopyrightText: 2021 Phillip Burgess for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <bluefruit.h>

// packetbuffer holds inbound data
#define READ_BUFSIZE 20
uint8_t packetbuffer[READ_BUFSIZE + 1]; // +1 is for NUL string terminator

/**************************************************************************/
/*!
    @brief    Casts the four bytes at the specified address to a float.
    @param    ptr  Pointer into packet buffer.
    @returns  Floating-point value.
*/
/**************************************************************************/
float parsefloat(uint8_t *ptr) {
  float f;            // Make a suitably-aligned float variable,
  memcpy(&f, ptr, 4); // because in-buffer instance might be misaligned!
  return f;           // (You can't always safely parse in-place)
}

/**************************************************************************/
/*!
    @brief  Prints a series of bytes in 0xNN hexadecimal notation.
    @param  buf  Pointer to array of byte data.
    @param  len  Data length in bytes.
*/
/**************************************************************************/
void printHex(const uint8_t *buf, const uint32_t len) {
  for (uint32_t i=0; i < len; i++) {
    Serial.print(F("0x"));
    if (buf[i] <= 0xF) Serial.write('0'); // Zero-pad small values
    Serial.print(buf[i], HEX);
    if (i < (len - 1)) Serial.write(' '); // Space between bytes
  }
  Serial.println();
}

static const struct { // Special payloads from Bluefruit Connect app...
  char    id;         // Packet type identifier
  uint8_t len;        // Size of complete, well-formed packet of this type
} _app_packet[] = {
  {'A', 15}, // Accelerometer
  {'G', 15}, // Gyro
  {'M', 15}, // Magnetometer
  {'Q', 19}, // Quaterion
  {'B',  5}, // Button
  {'C',  6}, // Color
  {'L', 15}, // Location
};
#define NUM_PACKET_TYPES (sizeof _app_packet / sizeof _app_packet[0])
#define SHORTEST_PACKET_LEN 5 // Button, for now

/**************************************************************************/
/*!
    @brief    Given packet data, identify if it's one of the known
              Bluefruit Connect app packet types.
    @param    buf  Pointer to packet data.
    @param    len  Size of packet in bytes.
    @returns  Packet type index (0 to NUM_PACKET_TYPES-1) if recognized,
              -1 if unrecognized.
*/
/**************************************************************************/
int8_t packetType(uint8_t *buf, uint8_t len) {
  if ((len >= SHORTEST_PACKET_LEN) && (buf[0] == '!')) {
    for (int8_t type=0; type<NUM_PACKET_TYPES; type++) {
      if ((buf[1] == _app_packet[type].id) &&
          (len == _app_packet[type].len)) {
        return type;
      }
    }
  }
  return -1; // Length too short for a packet, or not a recognized type
}

/**************************************************************************/
/*!
    @brief    Wait for incoming data and determine if it's one of the
              special Bluefruit Connect app packet types.
    @param    ble      Pointer to BLE UART object.
              timeout  Character read timeout in milliseconds.
    @returns  Length of data, or 0 if checksum is invalid for the type of
              packet detected.
    @note     Packet buffer is not cleared. Calling function is expected
              to check return value before deciding whether to act on the
              data.
*/
/**************************************************************************/
uint8_t readPacket(BLEUart *ble, uint16_t timeout) {
  int8_t   type = -1; // App packet type, -1 if unknown or freeform string
  uint8_t  len = 0, xsum = 255; // Packet length and ~checksum so far
  uint32_t now, start_time = millis();
  do {
    now = millis();
    if (ble->available()) {
      char c = ble->read();
      if (c == '!') { // '!' resets buffer to start
        len = 0;
        xsum = 255;
      }
      packetbuffer[len++] = c;
      // Stop when buffer's full or packet type recognized
      if ((len >= READ_BUFSIZE) ||
          ((type = packetType(packetbuffer, len)) >= 0)) break;
      start_time = now; // Reset timeout on char received
      xsum -= c;        // Not last char, do checksum math
      type = -1;        // Reset packet type finder
    }
  } while((now - start_time) < timeout);

  // If packet type recognized, verify checksum (else freeform string)
  if ((type >= 0) && (xsum != packetbuffer[len-1])) { // Last byte = checksum
    Serial.print("Packet checksum mismatch: ");
    printHex(packetbuffer, len);
    return 0;
  }

  packetbuffer[len] = 0; // Terminate packet string

  return len; // Checksum is valid for packet, or it's a freeform string
}
