// SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT
/*
 * ESP-NOW Walkie Talkie for ESP32-S3 Reverse TFT Feather
 * Hold button to record, release to send over ESP-NOW.
 * Incoming audio plays back automatically.
 * Status shown on built-in TFT
 */

#include <esp_now.h>
#include <WiFi.h>
#include <driver/i2s.h>
#include <Adafruit_ST7789.h>
#include <Fonts/FreeSans9pt7b.h>
#include <Fonts/FreeSansBold12pt7b.h>

// --- DISPLAY ---
Adafruit_ST7789 tft = Adafruit_ST7789(TFT_CS, TFT_DC, TFT_RST);
GFXcanvas16 canvas(240, 135);

// --- PIN DEFINITIONS ---
#define MIC_BCLK  5
#define MIC_LRCLK 6
#define MIC_DOUT  9

#define DAC_BCK   10
#define DAC_LCK   11
#define DAC_DIN   12

#define BUTTON_PIN   13
#define LED_PIN      A0

// --- AUDIO CONFIG ---
#define SAMPLE_RATE     16000
#define BITS_PER_SAMPLE I2S_BITS_PER_SAMPLE_16BIT
#define RECORD_MAX_SEC  10
#define MAX_SAMPLES     (SAMPLE_RATE * RECORD_MAX_SEC)
#define DMA_BUF_COUNT   8
#define DMA_BUF_LEN     256

#define I2S_MIC_PORT    I2S_NUM_0
#define I2S_DAC_PORT    I2S_NUM_1

// --- ESP-NOW PROTOCOL ---
#define PKT_AUDIO       0x00
#define PKT_DISCOVERY   0x01
#define PKT_MANIFEST    0x02
#define PKT_NACK        0x03
#define PKT_ACK_DONE    0x04

#define ESPNOW_MAX_SIZE   250
#define HEADER_SIZE       6
#define CHUNK_PAYLOAD     (ESPNOW_MAX_SIZE - HEADER_SIZE)
#define SAMPLES_PER_CHUNK (CHUNK_PAYLOAD / sizeof(int16_t))

#define MANIFEST_SIZE     8
#define NACK_HEADER       4
#define MAX_NACK_INDICES  ((ESPNOW_MAX_SIZE - NACK_HEADER) / 2)

// Timing & retries
#define INTER_CHUNK_US     1500
#define SEND_TIMEOUT_MS    100
#define MAX_RETRIES        3
#define MAX_REPAIR_ROUNDS  3
#define MAX_FULL_RETRIES   3
#define NACK_WAIT_MS       800
#define POST_NACK_SETTLE   50
#define RX_SETTLE_MS       200
#define FULL_RETRY_DELAY   500

// --- DISPLAY COLORS ---
#define COL_BG        0x0000   // black
#define COL_TITLE     0x07FF   // cyan
#define COL_OK        0x07E0   // green
#define COL_WARN      0xFD20   // orange
#define COL_ERR       0xF800   // red
#define COL_INFO      0xFFFF   // white
#define COL_DIM       0x7BEF   // grey
#define COL_ACCENT    0xF81F   // magenta
#define COL_RECORDING 0xF800   // red
#define COL_PLAYING   0x07E0   // green
#define COL_SENDING   0xFFE0   // yellow

// --- DISPLAY STATE ---
enum DeviceState {
  STATE_BOOTING,
  STATE_DISCOVERING,
  STATE_IDLE,
  STATE_RECORDING,
  STATE_SENDING,
  STATE_PLAYING
};

DeviceState deviceState = STATE_BOOTING;
char statusLine1[64] = "";
char statusLine2[64] = "";
char peerMacStr[20] = "";
int lastRSSI = 0;
volatile int latestRSSI = 0;   // updated in rx callback
unsigned long lastDisplayUpdate = 0;
#define DISPLAY_UPDATE_MS 100

// --- GLOBALS ---
int16_t* txBuffer = nullptr;
int16_t* rxBuffer = nullptr;
size_t   txSampleCount = 0;

// Receive state
volatile bool     rxComplete = false;
volatile size_t   rxSampleCount = 0;
uint8_t           rxMsgId = 255;
uint16_t          rxTotalChunks = 0;
volatile uint16_t rxChunksReceived = 0;
uint32_t          rxExpectedSamples = 0;
volatile bool     rxGotManifest = false;
volatile unsigned long rxManifestTime = 0;
bool*             rxChunkMap = nullptr;

// Transmit state
uint8_t txMsgId = 0;
volatile bool sendBusy = false;
volatile bool lastSendOk = false;

// Sender: response from receiver
volatile bool     nackReceived = false;
volatile bool     ackDoneReceived = false;
volatile uint16_t nackCount = 0;
uint16_t nackIndices[MAX_NACK_INDICES];

// Peer tracking
bool     peerPaired = false;
uint8_t  peerAddr[6];
uint8_t  broadcastAddr[] = {0xFF,0xFF,0xFF,0xFF,0xFF,0xFF};
esp_now_peer_info_t peerInfo;

// =============================================
// DISPLAY FUNCTIONS
// =============================================

void updateDisplay() {
  canvas.fillScreen(COL_BG);

  // ---- Row 1: Title bar ----
  canvas.setFont(&FreeSansBold12pt7b);
  canvas.setCursor(4, 20);

  switch (deviceState) {
    case STATE_BOOTING:
      canvas.setTextColor(COL_DIM);
      canvas.print("WALKIE TALKIE");
      break;
    case STATE_DISCOVERING:
      canvas.setTextColor(COL_WARN);
      canvas.print("SCANNING...");
      break;
    case STATE_IDLE:
      canvas.setTextColor(COL_TITLE);
      canvas.print("WALKIE TALKIE");
      break;
    case STATE_RECORDING:
      canvas.setTextColor(COL_RECORDING);
      canvas.print("RECORDING");
      break;
    case STATE_SENDING:
      canvas.setTextColor(COL_SENDING);
      canvas.print("SENDING");
      break;
    case STATE_PLAYING:
      canvas.setTextColor(COL_PLAYING);
      canvas.print("PLAYING");
      break;
  }

  // ---- Row 2: Connection info ----
  canvas.setFont(&FreeSans9pt7b);
  canvas.setCursor(4, 48);

  if (peerPaired) {
    canvas.setTextColor(COL_OK);
    canvas.print("Peer: ");
    canvas.setTextColor(COL_INFO);
    canvas.print(peerMacStr);
  } else {
    canvas.setTextColor(COL_DIM);
    canvas.print("No peer connected");
  }

  // ---- Row 3: RSSI / signal ----
  if (peerPaired && lastRSSI != 0) {
    canvas.setCursor(4, 70);
    canvas.setTextColor(COL_DIM);
    canvas.print("Signal: ");

    // Classify signal strength
    if (lastRSSI > -50) {
      canvas.setTextColor(COL_OK);
      canvas.print("Excellent");
    } else if (lastRSSI > -65) {
      canvas.setTextColor(COL_OK);
      canvas.print("Good");
    } else if (lastRSSI > -80) {
      canvas.setTextColor(COL_WARN);
      canvas.print("Fair");
    } else {
      canvas.setTextColor(COL_ERR);
      canvas.print("Weak");
    }

    canvas.setTextColor(COL_DIM);
    canvas.printf(" (%d dBm)", lastRSSI);
  }

  // ---- Row 4: Status line 1 ----
  if (statusLine1[0]) {
    canvas.setCursor(4, 96);
    canvas.setTextColor(COL_INFO);
    canvas.print(statusLine1);
  }

  // ---- Row 5: Status line 2 ----
  if (statusLine2[0]) {
    canvas.setCursor(4, 118);
    canvas.setTextColor(COL_DIM);
    canvas.print(statusLine2);
  }

  // Push to screen
  tft.drawRGBBitmap(0, 0, canvas.getBuffer(), 240, 135);
}

// Helper: set status lines and refresh display immediately
void setStatus(const char* line1, const char* line2 = nullptr) {
  if (line1) strncpy(statusLine1, line1, sizeof(statusLine1) - 1);
  if (line2) strncpy(statusLine2, line2, sizeof(statusLine2) - 1);
  else statusLine2[0] = '\0';
  updateDisplay();
}

// Periodic refresh (call from loop for RSSI updates etc)
void tickDisplay() {
  if (millis() - lastDisplayUpdate >= DISPLAY_UPDATE_MS) {
    lastDisplayUpdate = millis();
    lastRSSI = latestRSSI;
    updateDisplay();
  }
}

// =============================================
// I2S SETUP
// =============================================

void setupMicI2S() {
  i2s_config_t cfg = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = BITS_PER_SAMPLE,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = DMA_BUF_COUNT,
    .dma_buf_len = DMA_BUF_LEN,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };
  i2s_pin_config_t pins = {
    .bck_io_num   = MIC_BCLK,
    .ws_io_num    = MIC_LRCLK,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num  = MIC_DOUT
  };
  i2s_driver_install(I2S_MIC_PORT, &cfg, 0, NULL);
  i2s_set_pin(I2S_MIC_PORT, &pins);
  i2s_zero_dma_buffer(I2S_MIC_PORT);
}

void setupDacI2S() {
  i2s_config_t cfg = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = BITS_PER_SAMPLE,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = DMA_BUF_COUNT,
    .dma_buf_len = DMA_BUF_LEN,
    .use_apll = false,
    .tx_desc_auto_clear = true,
    .fixed_mclk = 0
  };
  i2s_pin_config_t pins = {
    .bck_io_num   = DAC_BCK,
    .ws_io_num    = DAC_LCK,
    .data_out_num = DAC_DIN,
    .data_in_num  = I2S_PIN_NO_CHANGE
  };
  i2s_driver_install(I2S_DAC_PORT, &cfg, 0, NULL);
  i2s_set_pin(I2S_DAC_PORT, &pins);
  i2s_zero_dma_buffer(I2S_DAC_PORT);
}

// =============================================
// ESP-NOW CALLBACKS
// =============================================

void onDataSent(const wifi_tx_info_t* info, esp_now_send_status_t status) {
  lastSendOk = (status == ESP_NOW_SEND_SUCCESS);
  sendBusy = false;
}

void onDataRecv(const esp_now_recv_info_t* recvInfo, const uint8_t* data, int len) {
  if (len < 1) return;

  // Capture RSSI from every packet
  if (recvInfo->rx_ctrl) {
    latestRSSI = recvInfo->rx_ctrl->rssi;
  }

  uint8_t pktType = data[0];

  // ---- Discovery ----
  if (pktType == PKT_DISCOVERY) {
    if (!peerPaired) {
      memcpy(peerAddr, recvInfo->src_addr, 6);
      peerPaired = true;
      snprintf(peerMacStr, sizeof(peerMacStr), "%02X:%02X:%02X:%02X:%02X:%02X",
               peerAddr[0],peerAddr[1],peerAddr[2],
               peerAddr[3],peerAddr[4],peerAddr[5]);
      Serial.printf("Discovered peer: %s\n", peerMacStr);
    }
    return;
  }

  // ---- ACK_DONE ----
  if (pktType == PKT_ACK_DONE) {
    ackDoneReceived = true;
    return;
  }

  // ---- NACK ----
  if (pktType == PKT_NACK && len >= NACK_HEADER) {
    uint16_t count = data[2] | (data[3] << 8);
    count = min(count, (uint16_t)MAX_NACK_INDICES);
    if ((size_t)len < NACK_HEADER + count * 2) return;
    nackCount = count;
    for (uint16_t i = 0; i < count; i++) {
      size_t pos = NACK_HEADER + i * 2;
      nackIndices[i] = data[pos] | (data[pos + 1] << 8);
    }
    nackReceived = true;
    return;
  }

  // ---- Manifest ----
  if (pktType == PKT_MANIFEST && len >= MANIFEST_SIZE) {
    uint8_t  msgId   = data[1];
    uint16_t total   = data[2] | (data[3] << 8);
    uint32_t samples = data[4] | (data[5] << 8) | (data[6] << 16) | (data[7] << 24);
    if (msgId != rxMsgId) {
      rxMsgId          = msgId;
      rxTotalChunks    = total;
      rxChunksReceived = 0;
      rxSampleCount    = 0;
      rxComplete       = false;
      rxGotManifest    = false;
      memset(rxChunkMap, 0, total);
    }
    if (rxComplete) return;
    rxTotalChunks     = total;
    rxExpectedSamples = samples;
    rxGotManifest     = true;
    rxManifestTime    = millis();
    return;
  }

  // ---- Audio chunk ----
  if (pktType != PKT_AUDIO || len < HEADER_SIZE) return;
  uint8_t  msgId = data[1];
  uint16_t seq   = data[2] | (data[3] << 8);
  uint16_t total = data[4] | (data[5] << 8);
  const int16_t* samples = (const int16_t*)(data + HEADER_SIZE);
  size_t numSamples = (len - HEADER_SIZE) / sizeof(int16_t);

  if (msgId != rxMsgId) {
    rxMsgId          = msgId;
    rxTotalChunks    = total;
    rxChunksReceived = 0;
    rxSampleCount    = 0;
    rxComplete       = false;
    rxGotManifest    = false;
    rxExpectedSamples = 0;
    memset(rxChunkMap, 0, total);
  }
  if (rxComplete) return;
  if (seq < rxTotalChunks && !rxChunkMap[seq]) {
    size_t offset = (size_t)seq * SAMPLES_PER_CHUNK;
    size_t toCopy = min(numSamples, (size_t)(MAX_SAMPLES - offset));
    memcpy(&rxBuffer[offset], samples, toCopy * sizeof(int16_t));
    rxChunkMap[seq] = true;
    rxChunksReceived++;
  }
}

// =============================================
// DISCOVERY
// =============================================

void sendDiscoveryBeacon() {
  uint8_t pkt[1] = { PKT_DISCOVERY };
  esp_now_send(broadcastAddr, pkt, sizeof(pkt));
}

void waitForPeer() {
  deviceState = STATE_DISCOVERING;
  setStatus("Searching for peer...");
  Serial.println("Sending discovery beacons — waiting for peer...");

  memcpy(peerInfo.peer_addr, broadcastAddr, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;
  esp_now_add_peer(&peerInfo);

  bool ledState = false;
  while (!peerPaired) {
    sendDiscoveryBeacon();
    ledState = !ledState;
    digitalWrite(LED_PIN, ledState ? HIGH : LOW);
    for (int i = 0; i < 50 && !peerPaired; i++) {
      delay(10);
    }
    tickDisplay();
  }

  setStatus("Peer found!", "Completing handshake...");
  Serial.println("Paired! Sending beacons for grace period...");
  for (int i = 0; i < 30; i++) {
    sendDiscoveryBeacon();
    delay(100);
  }
  digitalWrite(LED_PIN, LOW);

  if (esp_now_is_peer_exist(broadcastAddr)) {
    esp_now_del_peer(broadcastAddr);
  }
  if (!esp_now_is_peer_exist(peerAddr)) {
    memcpy(peerInfo.peer_addr, peerAddr, 6);
    peerInfo.channel = 0;
    peerInfo.encrypt = false;
    esp_now_add_peer(&peerInfo);
  }

  deviceState = STATE_IDLE;
  setStatus("Ready. Hold button to talk.");
  Serial.println("Peer paired! Ready to talk.");
}

// =============================================
// RECORD
// =============================================

size_t recordAudio() {
  deviceState = STATE_RECORDING;
  setStatus("Recording...");
  Serial.println("Recording...");

  int16_t flushBuf[256];
  size_t bytesRead;
  for (int i = 0; i < DMA_BUF_COUNT; i++) {
    i2s_read(I2S_MIC_PORT, flushBuf, sizeof(flushBuf), &bytesRead, portMAX_DELAY);
  }

  size_t sampleCount = 0;
  int16_t readBuf[DMA_BUF_LEN];
  digitalWrite(LED_PIN, HIGH);

  unsigned long recStart = millis();
  while (digitalRead(BUTTON_PIN) == LOW && sampleCount < MAX_SAMPLES) {
    i2s_read(I2S_MIC_PORT, readBuf, sizeof(readBuf), &bytesRead, portMAX_DELAY);
    size_t samplesRead = bytesRead / sizeof(int16_t);
    size_t toCopy = min(samplesRead, (size_t)(MAX_SAMPLES - sampleCount));
    memcpy(&txBuffer[sampleCount], readBuf, toCopy * sizeof(int16_t));
    sampleCount += toCopy;

    // Update display with recording duration periodically
    if (millis() - lastDisplayUpdate >= 200) {
      char buf[32];
      float elapsed = (float)(millis() - recStart) / 1000.0f;
      snprintf(buf, sizeof(buf), "%.1fs / %ds", elapsed, RECORD_MAX_SEC);
      setStatus("Recording...", buf);
      lastDisplayUpdate = millis();
    }
  }

  float dur = (float)sampleCount / SAMPLE_RATE;
  Serial.printf("Recorded %d samples (%.1fs)\n", sampleCount, dur);

  int fade = min((size_t)200, sampleCount / 4);
  for (int i = 0; i < fade; i++) {
    txBuffer[i] = (int32_t)txBuffer[i] * i / fade;
    txBuffer[sampleCount - 1 - i] = (int32_t)txBuffer[sampleCount - 1 - i] * i / fade;
  }

  digitalWrite(LED_PIN, LOW);
  return sampleCount;
}

// =============================================
// LOW-LEVEL SEND
// =============================================

bool sendPacketWithRetry(uint8_t* packet, size_t packetLen) {
  for (int attempt = 0; attempt < MAX_RETRIES; attempt++) {
    sendBusy  = true;
    lastSendOk = false;
    esp_err_t result = esp_now_send(peerAddr, packet, packetLen);
    if (result != ESP_OK) {
      sendBusy = false;
      delay(5);
      continue;
    }
    unsigned long t0 = millis();
    while (sendBusy && (millis() - t0 < SEND_TIMEOUT_MS)) {
      delayMicroseconds(200);
    }
    if (lastSendOk) return true;
    delay(5);
  }
  return false;
}

void sendManifest(uint8_t msgId, uint16_t totalChunks, uint32_t totalSamples) {
  uint8_t pkt[MANIFEST_SIZE];
  pkt[0] = PKT_MANIFEST;
  pkt[1] = msgId;
  pkt[2] = totalChunks & 0xFF;
  pkt[3] = (totalChunks >> 8) & 0xFF;
  pkt[4] = totalSamples & 0xFF;
  pkt[5] = (totalSamples >> 8) & 0xFF;
  pkt[6] = (totalSamples >> 16) & 0xFF;
  pkt[7] = (totalSamples >> 24) & 0xFF;
  sendPacketWithRetry(pkt, MANIFEST_SIZE);
}

bool sendChunk(uint8_t msgId, uint16_t seq, uint16_t totalChunks, size_t sampleCount) {
  uint8_t packet[ESPNOW_MAX_SIZE];
  size_t offset       = (size_t)seq * SAMPLES_PER_CHUNK;
  size_t remaining    = sampleCount - offset;
  size_t chunkSamples = min((size_t)SAMPLES_PER_CHUNK, remaining);
  size_t payloadBytes = chunkSamples * sizeof(int16_t);

  packet[0] = PKT_AUDIO;
  packet[1] = msgId;
  packet[2] = seq & 0xFF;
  packet[3] = (seq >> 8) & 0xFF;
  packet[4] = totalChunks & 0xFF;
  packet[5] = (totalChunks >> 8) & 0xFF;
  memcpy(&packet[HEADER_SIZE], &txBuffer[offset], payloadBytes);

  return sendPacketWithRetry(packet, HEADER_SIZE + payloadBytes);
}

// =============================================
// SEND AUDIO WITH REPAIR + FULL RETRY
// =============================================

bool sendAudioAttempt(size_t sampleCount, uint16_t totalChunks) {
  // Send all chunks
  uint16_t hwFail = 0;
  for (uint16_t seq = 0; seq < totalChunks; seq++) {
    if (!sendChunk(txMsgId, seq, totalChunks, sampleCount)) {
      hwFail++;
    }
    delayMicroseconds(INTER_CHUNK_US);

    // Update display progress every ~50 chunks
    if (seq % 50 == 0) {
      char buf[48];
      snprintf(buf, sizeof(buf), "Chunk %d / %d", seq, totalChunks);
      setStatus("Sending...", buf);
    }
  }
  Serial.printf("  Chunks sent (%d HW failures)\n", hwFail);

  // Repair rounds
  for (int round = 0; round < MAX_REPAIR_ROUNDS; round++) {
    nackReceived    = false;
    ackDoneReceived = false;
    nackCount       = 0;

    sendManifest(txMsgId, totalChunks, (uint32_t)sampleCount);
    Serial.printf("  Manifest sent (round %d) — waiting...\n", round + 1);

    char buf[48];
    snprintf(buf, sizeof(buf), "Verifying (round %d)...", round + 1);
    setStatus("Sending...", buf);

    unsigned long t0 = millis();
    while (!nackReceived && !ackDoneReceived && (millis() - t0 < NACK_WAIT_MS)) {
      delay(1);
    }

    if (ackDoneReceived) {
      Serial.println("  ACK received — transfer complete!");
      return true;
    }
    if (!nackReceived) {
      Serial.println("  No response — assuming complete.");
      return true;
    }
    if (nackCount == 0) {
      Serial.println("  NACK with 0 missing — transfer complete!");
      return true;
    }

    Serial.printf("  NACK: %d missing — retransmitting...\n", nackCount);
    snprintf(buf, sizeof(buf), "Repairing %d chunks...", nackCount);
    setStatus("Sending...", buf);

    delay(POST_NACK_SETTLE);
    for (uint16_t i = 0; i < nackCount; i++) {
      uint16_t seq = nackIndices[i];
      if (seq < totalChunks) {
        sendChunk(txMsgId, seq, totalChunks, sampleCount);
        delayMicroseconds(INTER_CHUNK_US);
      }
    }
  }

  // Final manifest
  nackReceived    = false;
  ackDoneReceived = false;
  sendManifest(txMsgId, totalChunks, (uint32_t)sampleCount);
  unsigned long t0 = millis();
  while (!nackReceived && !ackDoneReceived && (millis() - t0 < NACK_WAIT_MS)) {
    delay(1);
  }
  if (ackDoneReceived) {
    Serial.println("  ACK after final manifest — complete!");
    return true;
  }
  return false;
}

void sendAudio(size_t sampleCount) {
  uint16_t totalChunks = (sampleCount + SAMPLES_PER_CHUNK - 1) / SAMPLES_PER_CHUNK;
  float dur = (float)sampleCount / SAMPLE_RATE;
  deviceState = STATE_SENDING;

  for (int fullAttempt = 0; fullAttempt < MAX_FULL_RETRIES; fullAttempt++) {
    txMsgId++;

    Serial.printf("Sending %d samples in %d chunks (msg %d, attempt %d/%d)...\n",
                  sampleCount, totalChunks, txMsgId,
                  fullAttempt + 1, MAX_FULL_RETRIES);

    char buf[48];
    snprintf(buf, sizeof(buf), "%.1fs — attempt %d/%d",
             dur, fullAttempt + 1, MAX_FULL_RETRIES);
    setStatus("Sending...", buf);

    if (sendAudioAttempt(sampleCount, totalChunks)) {
      deviceState = STATE_IDLE;
      setStatus("Sent!", "Ready. Hold button to talk.");
      delay(1000);
      setStatus("Ready. Hold button to talk.");
      return;
    }

    Serial.printf("  Attempt %d failed.\n", fullAttempt + 1);

    if (fullAttempt < MAX_FULL_RETRIES - 1) {
      char buf2[48];
      snprintf(buf2, sizeof(buf2), "Retry in %dms...", FULL_RETRY_DELAY);
      setStatus("Send failed", buf2);
      Serial.printf("  Waiting %dms before full retry...\n", FULL_RETRY_DELAY);
      delay(FULL_RETRY_DELAY);
    }
  }

  Serial.println("  ALL ATTEMPTS FAILED — giving up.");
  deviceState = STATE_IDLE;
  setStatus("Send failed!", "Ready. Hold button to talk.");
  delay(2000);
  setStatus("Ready. Hold button to talk.");
}

// =============================================
// RECEIVER RESPONSES
// =============================================

void sendNack(uint8_t msgId) {
  uint16_t missing[MAX_NACK_INDICES];
  uint16_t count = 0;
  for (uint16_t i = 0; i < rxTotalChunks && count < MAX_NACK_INDICES; i++) {
    if (!rxChunkMap[i]) missing[count++] = i;
  }

  uint8_t pkt[ESPNOW_MAX_SIZE];
  pkt[0] = PKT_NACK;
  pkt[1] = msgId;
  pkt[2] = count & 0xFF;
  pkt[3] = (count >> 8) & 0xFF;
  for (uint16_t i = 0; i < count; i++) {
    size_t pos = NACK_HEADER + i * 2;
    pkt[pos]     = missing[i] & 0xFF;
    pkt[pos + 1] = (missing[i] >> 8) & 0xFF;
  }
  sendPacketWithRetry(pkt, NACK_HEADER + count * 2);

  Serial.printf("  Sent NACK: %d missing of %d total (%d received)\n",
                count, rxTotalChunks, rxChunksReceived);

  char buf[48];
  snprintf(buf, sizeof(buf), "Receiving... %d/%d chunks", rxChunksReceived, rxTotalChunks);
  setStatus("Incoming message", buf);
}

void sendAckDone(uint8_t msgId) {
  uint8_t pkt[2] = { PKT_ACK_DONE, msgId };
  sendPacketWithRetry(pkt, sizeof(pkt));
  Serial.println("  Sent ACK_DONE");
}

// =============================================
// PLAYBACK
// =============================================

void playAudio(int16_t* buffer, size_t sampleCount) {
  float dur = (float)sampleCount / SAMPLE_RATE;
  deviceState = STATE_PLAYING;

  char buf[32];
  snprintf(buf, sizeof(buf), "%.1f seconds", dur);
  setStatus("Playing...", buf);

  Serial.printf("Playing %d samples (%.1fs)...\n", sampleCount, dur);
  digitalWrite(LED_PIN, HIGH);

  size_t bytesWritten;
  size_t offset = 0;
  while (offset < sampleCount) {
    size_t toWrite = min((size_t)DMA_BUF_LEN, sampleCount - offset);
    i2s_write(I2S_DAC_PORT, &buffer[offset], toWrite * sizeof(int16_t),
              &bytesWritten, portMAX_DELAY);
    offset += bytesWritten / sizeof(int16_t);
  }

  int16_t silence[DMA_BUF_LEN] = {0};
  for (int i = 0; i < DMA_BUF_COUNT; i++) {
    i2s_write(I2S_DAC_PORT, silence, sizeof(silence), &bytesWritten, portMAX_DELAY);
  }

  Serial.println("Playback done!");
  digitalWrite(LED_PIN, LOW);

  deviceState = STATE_IDLE;
  setStatus("Ready. Hold button to talk.");
}

// =============================================
// SETUP
// =============================================

void setup() {
  Serial.begin(115200);

  tft.init(135, 240);
  tft.setRotation(3);
  pinMode(TFT_BACKLITE, OUTPUT);
  digitalWrite(TFT_BACKLITE, HIGH);

  deviceState = STATE_BOOTING;
  setStatus("Booting...");

  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);

  // Allocate buffers
  txBuffer = (int16_t*)ps_malloc(MAX_SAMPLES * sizeof(int16_t));
  rxBuffer = (int16_t*)ps_malloc(MAX_SAMPLES * sizeof(int16_t));
  if (!txBuffer) txBuffer = (int16_t*)malloc(MAX_SAMPLES * sizeof(int16_t));
  if (!rxBuffer) rxBuffer = (int16_t*)malloc(MAX_SAMPLES * sizeof(int16_t));

  size_t maxChunks = (MAX_SAMPLES + SAMPLES_PER_CHUNK - 1) / SAMPLES_PER_CHUNK;
  rxChunkMap = (bool*)calloc(maxChunks, sizeof(bool));

  if (!txBuffer || !rxBuffer || !rxChunkMap) {
    Serial.println("ERROR: Memory allocation failed!");
    setStatus("MEMORY ERROR!", "Cannot allocate buffers");
    while (1) { delay(100); }
  }
  memset(rxBuffer, 0, MAX_SAMPLES * sizeof(int16_t));

  setStatus("Booting...", "Initializing audio...");
  setupMicI2S();
  setupDacI2S();

  // WiFi + ESP-NOW
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  if (esp_now_init() != ESP_OK) {
    Serial.println("ERROR: ESP-NOW init failed!");
    setStatus("ESP-NOW ERROR!", "Init failed");
    while (1) { delay(100); }
  }
  esp_now_register_send_cb(onDataSent);
  esp_now_register_recv_cb(onDataRecv);

  Serial.printf("MAC: %s\n", WiFi.macAddress().c_str());
  Serial.println("========================================");
  Serial.println("ESP-NOW Walkie Talkie");
  Serial.printf("  Sample rate: %d Hz | Max: %ds\n", SAMPLE_RATE, RECORD_MAX_SEC);
  Serial.println("========================================");

  char macBuf[48];
  snprintf(macBuf, sizeof(macBuf), "MAC: %s", WiFi.macAddress().c_str());
  setStatus("Booting...", macBuf);
  delay(500);

  waitForPeer();

  Serial.println("Hold button to record, release to send.");
  Serial.println("Incoming audio plays automatically.");
}

// =============================================
// MAIN LOOP
// =============================================

void loop() {
  // Button press -> record and send
  if (digitalRead(BUTTON_PIN) == LOW) {
    delay(50);
    if (digitalRead(BUTTON_PIN) == HIGH) return;

    txSampleCount = recordAudio();

    if (txSampleCount > SAMPLE_RATE / 5) {
      sendAudio(txSampleCount);
    } else {
      Serial.println("Too short, not sending.");
      deviceState = STATE_IDLE;
      setStatus("Too short!", "Hold longer to record.");
      delay(1000);
      setStatus("Ready. Hold button to talk.");
    }

    while (digitalRead(BUTTON_PIN) == LOW) { delay(10); }
    delay(300);
  }

  // Got manifest but missing chunks? Wait settle time, then respond.
  if (rxGotManifest && !rxComplete) {
    if (millis() - rxManifestTime >= RX_SETTLE_MS) {
      rxGotManifest = false;
      if (rxChunksReceived >= rxTotalChunks) {
        rxSampleCount = rxExpectedSamples;
        rxComplete = true;
        sendAckDone(rxMsgId);
      } else {
        sendNack(rxMsgId);
      }
    }
  }

  // Complete message -> play it
  if (rxComplete) {
    Serial.printf("Received message %d (%d/%d chunks, %d samples)\n",
                  rxMsgId, rxChunksReceived, rxTotalChunks, rxSampleCount);
    playAudio(rxBuffer, rxSampleCount);
    rxComplete = false;
    rxGotManifest = false;
  }

  // Periodic display refresh (updates RSSI etc while idle)
  tickDisplay();

  delay(1);
}
