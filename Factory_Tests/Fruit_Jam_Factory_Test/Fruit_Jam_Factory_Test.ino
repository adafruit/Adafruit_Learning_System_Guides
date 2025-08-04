// SPDX-FileCopyrightText: 2025 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include "hardware/pio.h"
#include "pio_usb.h"
#include "Adafruit_TinyUSB.h"
#include <Adafruit_dvhstx.h>
#include "Adafruit_TestBed.h"
#include "Adafruit_NeoPixel.h" 
#include <SdFat_Adafruit_Fork.h>
#include <SPI.h>
#include <WiFiNINA.h>
#include <I2S.h>
#include <Adafruit_TLV320DAC3100.h>

// NeoPixel - Note we can't write to these all the time or DVI gets sad from the blocking
extern Adafruit_TestBed TB;
Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUM_NEOPIXEL, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

// DVI display using HSTX peripheral
DVHSTX16 display(DVHSTX_PINOUT_DEFAULT, DVHSTX_RESOLUTION_320x240);
volatile bool display_inited = false;
volatile bool usbhost_inited = false;

// SD setup
SdFat SD;
SdFile file;
SdSpiConfig config(PIN_SD_DAT3_CS, DEDICATED_SPI, SD_SCK_MHZ(16), &SPI);
bool sd_initialized = false;
bool last_sd_detect_state = true;  // Active low, so true means not detected

// I2S
Adafruit_TLV320DAC3100 codec;  // Create codec object
I2S i2s(OUTPUT, PIN_I2S_BITCLK, PIN_I2S_DATAOUT); // Create the I2S port using a PIO state machine

int32_t headphone_gain = 60;  // starting gain == -30dB see Table 6-24
int32_t speaker_gain = 40;  // starting gain == -20dB see Table 6-24
// Octave of notes to play
uint32_t notes[] = {523, 587, 659, 698, 784, 880, 988, 1047};
uint8_t note_idx = 0;
uint32_t amplitude = 10000;    // amplitude of sine wave
uint32_t sampleRate = 44100;   // sample rate in Hz
float phase_increment = 0;
float phase = 0.0;
uint32_t note_timer = 0;


void setup() {
  Serial.begin(115200);
  while ( !Serial ) delay(10);   // wait for native usb
  delay(100);
  
  Serial.println("TinyUSB Hardware demo + DVI demo");

  Serial.println("initialize onboard NeoPixels");
  strip.begin();           
  strip.setBrightness(10); 
  strip.show();            
  strip.fill(0xFF00FF);
  
  Serial.println("init hstx display");
  if (!display.begin()) { // Blink LED if insufficient RAM
    pinMode(LED_BUILTIN, OUTPUT);
    for (;;)
      digitalWrite(LED_BUILTIN, (millis() / 500) & 1);
  }
  Serial.println("display initialized");
  display_inited = true;

  // wait for USB host to be done initializing
  while (! usbhost_inited) {
    delay(1);
  }
  
  Serial.println("Initialize testbed");
  TB.ledPin = LED_BUILTIN;
  TB.begin();

  Serial.println("Initialize onboard LED & buttons");
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(PIN_BUTTON1, INPUT_PULLUP);
  pinMode(PIN_BUTTON2, INPUT_PULLUP);
  pinMode(PIN_BUTTON3, INPUT_PULLUP);  
  // Setup SD detect pin
  pinMode(PIN_SD_DETECT, INPUT_PULLUP);
  last_sd_detect_state = digitalRead(PIN_SD_DETECT);

  // Set up the wifi coproc
  WiFi.setPins(SPIWIFI_SS, SPIWIFI_ACK, ESP32_RESETN, ESP32_GPIO0, &SPIWIFI);
  // check for the WiFi module:
  if (WiFi.status() == WL_NO_MODULE) {
    Serial.println("Communication with WiFi module failed!");
  } else {
    String fv = WiFi.firmwareVersion();  
    Serial.print("Firmware OK: ");  
    Serial.println(fv);
  }

  // Set up the I2S
  configI2S();
  note_timer = millis();
  phase_increment = 2.0 * PI * notes[note_idx] / sampleRate;

  
  uint32_t sys_clock = clock_get_hz(clk_sys);
  uint32_t peri_clock = clock_get_hz(clk_peri);
  Serial.printf("System clock: %u Hz (%u MHz)\n", sys_clock, sys_clock/1000000);
  Serial.printf("Peripheral clock: %u Hz (%u MHz)\n", peri_clock, peri_clock/1000000);
  check_pio_status();
}

uint8_t j = 0;
uint32_t last_wifi_scan = 0;

void loop() {
  j++;
  delay(10);

  // always add a line to the display!
  display.drawLine(random(display.width()), random(display.height()),
                 random(display.width()), random(display.height()),
                 random(65536));

  check_buttons();
  check_and_init_sd();

  // every 300 ms toggle the onboard red LED
  if ((j % 64) == 31) {
    digitalWrite(LED_BUILTIN, HIGH);
  }
  if ((j % 64) == 0) {
    digitalWrite(LED_BUILTIN, LOW);
  }

  // every .6 sec print analog pin info
  if ((j % 64) == 0) {
    Serial.print("A0 = "); Serial.print(TB.readAnalogVoltage(A0)); Serial.print("\t");
    Serial.print("A1 = "); Serial.print(TB.readAnalogVoltage(A1)); Serial.print("\t");
    Serial.print("A2 = "); Serial.print(TB.readAnalogVoltage(A2)); Serial.print("\t");
    Serial.print("A3 = "); Serial.print(TB.readAnalogVoltage(A3)); Serial.print("\t");
    Serial.print("A4 = "); Serial.print(TB.readAnalogVoltage(A4)); Serial.print("\t");
    Serial.print("A5 = "); Serial.print(TB.readAnalogVoltage(A5)); Serial.print("\n\r");
  }

  // every 1.2 sec print I2C bus info
  if (j == 127) {
    TB.printI2CBusScan();
  }

  if ((millis() - last_wifi_scan) > 10000) {
    // every 10 sec, scan wifi
    Serial.println("** Scan Networks **");
    int numSsid = WiFi.scanNetworks();
    if (numSsid == -1) {
      Serial.println("Couldn't get a wifi connection");
      return;
    }
    Serial.printf("Number of available networks: %d\n\r", numSsid);
  
    // print the network number and name for each network found:
    for (int thisNet = 0; thisNet < numSsid; thisNet++) {
      Serial.printf("%d) %s\tSignal: %d dBm\n\r", thisNet, WiFi.SSID(thisNet), WiFi.RSSI(thisNet));
    }
    last_wifi_scan = millis();
  }
}


void check_pio_status() {
  PIO pios[] = {pio0, pio1, pio2};
  
  for (uint pio_idx = 0; pio_idx < 3; pio_idx++) {
    PIO pio = pios[pio_idx];
    
    Serial.printf("PIO%d:\n", pio_idx);
    
    // Check state machine status
    for (uint sm = 0; sm < 4; sm++) {
      Serial.printf("  SM%d: %s\n", sm, 
             pio_sm_is_claimed(pio, sm) ? "CLAIMED" : "FREE");
    }
    Serial.printf("\n");
  }
}

void check_buttons() {
  if (!digitalRead(PIN_BUTTON1)) {
    Serial.println("Button 1 pressed!");
    strip.fill(0xFF0000);  // Red when button pressed
    strip.show();
    delay(50);  // Simple debounce
  }
  
  if (!digitalRead(PIN_BUTTON2)) {
    Serial.println("Button 2 pressed!");
    strip.fill(0x00FF00);  // Green when button1 pressed
    strip.show();
    delay(50);
  }
  
  if (!digitalRead(PIN_BUTTON3)) {
    Serial.println("Button 3 pressed!");
    strip.fill(0x0000FF);  // Blue when button2 pressed
    strip.show();
    delay(50);
  }
}


void check_and_init_sd() {
  bool current_sd_detect = digitalRead(PIN_SD_DETECT);
  
  // Check for SD card insertion (detect pin going high)
  if (current_sd_detect && (last_sd_detect_state == false)) {
    Serial.println("SD card inserted!");
    delay(100);  // Give the card time to stabilize
    
    if (!SD.begin(config)) {
      Serial.println("SD card initialization failed!");
      return;
    }
    
    Serial.println("SD card initialized successfully.");
    
    // Print the SD card details
    uint32_t size = SD.card()->sectorCount();
    if (size == 0) {
      Serial.println("Can't determine the card size.");
      return;
    }
    
    uint32_t sizeMB = 0.000512 * size + 0.5;
    Serial.printf("Card size: %lu MB (MB = 1,000,000 bytes)\n", sizeMB);
    Serial.printf("Volume is FAT%d, Cluster size (bytes): %lu\n\n", 
                 int(SD.vol()->fatType()), 
                 SD.vol()->bytesPerCluster());
    
    // List all files
    Serial.println("Files on card:");
    SD.ls(LS_R | LS_DATE | LS_SIZE);
    
    sd_initialized = true;
  }
  
  // Update last state
  last_sd_detect_state = current_sd_detect;
}



//------------- Core1 USB Host management -------------//

Adafruit_USBH_Host USBHost;
#define LANGUAGE_ID 0x0409

typedef struct {
  tusb_desc_device_t desc_device;
  uint16_t manufacturer[32];
  uint16_t product[48];
  uint16_t serial[16];
  bool mounted;
} dev_info_t;

// CFG_TUH_DEVICE_MAX is defined by tusb_config header
dev_info_t dev_info[CFG_TUH_DEVICE_MAX] = { 0 };


void setup1() {
  pinMode(PIN_5V_EN, OUTPUT);
  digitalWrite(PIN_5V_EN, PIN_5V_EN_STATE);
  
  while (! display_inited) {
    delay(1);
    yield();
  }

  Serial.println(clock_get_hz(clk_sys));
  
  Serial.println("Core1 setup to run TinyUSB host with pio-usb");

  pio_usb_configuration_t pio_cfg = PIO_USB_DEFAULT_CONFIG;
  pio_cfg.pin_dp = PIN_USB_HOST_DP;
  pio_cfg.tx_ch = dma_claim_unused_channel(true);
  dma_channel_unclaim(pio_cfg.tx_ch);
  USBHost.configure_pio_usb(1, &pio_cfg);
  
  USBHost.begin(1);
  usbhost_inited = true;
}

void loop1() {
  USBHost.task();
  Serial.flush();

  // Generate sine wave sample
  int16_t sample = amplitude * sin(phase);
  
  // write the same sample twice, once for left and once for the right channel
  i2s.write(sample);
  i2s.write((int16_t)-sample);
  
  // Update phase for next sample
  phase += phase_increment;
  if (phase >= 2.0 * PI) {
    phase -= 2.0 * PI;
  }
  // every 250ms change notes
  if ((millis() - note_timer) > 250) {
    note_idx = (note_idx + 1) % (sizeof(notes) / sizeof(notes[0]));
    //Serial.println(notes[note_idx]);
    phase_increment = 2.0 * PI * notes[note_idx] / sampleRate;
    note_timer = millis();

    static tlv320_headset_status_t last_status = TLV320_HEADSET_NONE;
  
    tlv320_headset_status_t status = codec.getHeadsetStatus();
  
    if (last_status != status) {
      switch (status) {
      case TLV320_HEADSET_NONE:
        Serial.println("Headset removed");
        // unmute speaker
        codec.configureSPK_PGA(TLV320_SPK_GAIN_6DB, true);
        // mute headphone
        codec.configureHPL_PGA(0, false);
        codec.configureHPR_PGA(0, false); 
        break;
      case TLV320_HEADSET_WITH_MIC:
        Serial.println("Headset with mic detected");
      case TLV320_HEADSET_WITHOUT_MIC:
        Serial.println("Headphones detected");
        // mute speaker
        codec.configureSPK_PGA(TLV320_SPK_GAIN_6DB, false);
        // unmute headphone
        codec.configureHPL_PGA(0, true);
        codec.configureHPR_PGA(0, true); 
        break;
      }
      last_status = status;
    }
  }
}

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
  if (!tuh_hid_receive_report(dev_addr, instance)) {
    Serial.printf("Error: cannot request to receive report\r\n");
  }
}

// Invoked when device with hid interface is un-mounted
void tuh_hid_umount_cb(uint8_t dev_addr, uint8_t instance) {
  Serial.printf("HID device address = %d, instance = %d is unmounted\r\n", dev_addr, instance);
}

// Invoked when received report from device via interrupt endpoint
void tuh_hid_report_received_cb(uint8_t dev_addr, uint8_t instance, uint8_t const *report, uint16_t len) {
  Serial.printf("HIDreport : ");
  for (uint16_t i = 0; i < len; i++) {
    Serial.printf("0x%02X ", report[i]);
  }
  Serial.println();
  // continue to request to receive report
  if (!tuh_hid_receive_report(dev_addr, instance)) {
    Serial.printf("Error: cannot request to receive report\r\n");
  }
}

} // extern C


void configI2S() {
  // reset
  pinMode(PIN_PERIPHERAL_RESET, OUTPUT);
  digitalWrite(PIN_PERIPHERAL_RESET, LOW);
  delay(10);
  digitalWrite(PIN_PERIPHERAL_RESET, HIGH);
  
  delay(100);

  Serial.println("Init TLV DAC");
  if (!codec.begin()) {
    Serial.println("Failed to initialize codec!");
    return;
  }
  delay(10);

  // Interface Control
  if (!codec.setCodecInterface(TLV320DAC3100_FORMAT_I2S,    // Format: I2S
                              TLV320DAC3100_DATA_LEN_16)) { // Length: 16 bits
    Serial.println("Failed to configure codec interface!");
    return;
  }

  // Clock MUX and PLL settings
  if (!codec.setCodecClockInput(TLV320DAC3100_CODEC_CLKIN_PLL) ||
      !codec.setPLLClockInput(TLV320DAC3100_PLL_CLKIN_BCLK)) {
    Serial.println("Failed to configure codec clocks!");
    return;
  }
    
  if (!codec.setPLLValues(1, 2, 32, 0)) {  // P=2, R=2, J=32, D=0
    Serial.println("Failed to configure PLL values!");
    return;
  }

  // DAC/ADC Config
  if (!codec.setNDAC(true, 8) ||    // Enable NDAC with value 8
      !codec.setMDAC(true, 2)) {    // Enable MDAC with value 2
    Serial.println("Failed to configure DAC dividers!");
    return;
  }
  
  if (!codec.powerPLL(true)) {  // Power up the PLL
    Serial.println("Failed to power up PLL!");
    return;
  }
  
  // DAC Setup
  if (!codec.setDACDataPath(true, true,                     // Power up both DACs
                           TLV320_DAC_PATH_NORMAL,          // Normal left path
                           TLV320_DAC_PATH_NORMAL,          // Normal right path
                           TLV320_VOLUME_STEP_1SAMPLE)) {   // Step: 1 per sample
    Serial.println("Failed to configure DAC data path!");
    return;
  }
  
  if (!codec.configureAnalogInputs(TLV320_DAC_ROUTE_MIXER,   // Left DAC to mixer
                                  TLV320_DAC_ROUTE_MIXER,    // Right DAC to mixer
                                  false, false, false,        // No AIN routing
                                  false)) {                   // No HPL->HPR
    Serial.println("Failed to configure DAC routing!");
    return;
  }

  // DAC Volume Control
  if (!codec.setDACVolumeControl(false, false, TLV320_VOL_INDEPENDENT) ||  // Unmute both channels
     !codec.setChannelVolume(false, 18) ||                                // Left DAC +0dB 
     !codec.setChannelVolume(true, 18)) {                                 // Right DAC +0dB
    Serial.println("Failed to configure DAC volumes!");
    return;
  }

  // Headphone and Speaker Setup
  if (!codec.configureHeadphoneDriver(true, true,            // Power up both drivers
                                     TLV320_HP_COMMON_1_35V,  // Default common mode
                                     false) ||                // Don't power down on SCD
      !codec.configureHPL_PGA(0, false) ||                    // Set HPL gain, mute
      !codec.configureHPR_PGA(0, false) ||                    // Set HPR gain, mute
      !codec.setHPLVolume(true, headphone_gain) ||           // Enable and set HPL volume
      !codec.setHPRVolume(true, headphone_gain)) {           // Enable and set HPR volume
    Serial.println("Failed to configure headphone outputs!");
    return;
  }

  if (!codec.enableSpeaker(true) ||                        // Dis/Enable speaker amp
      !codec.configureSPK_PGA(TLV320_SPK_GAIN_6DB,         // Set gain to 6dB
                             true) ||                      // Un-mute
      !codec.setSPKVolume(true, speaker_gain)) {           // Enable and set volume
    Serial.println("Failed to configure speaker output!");
    return;
  }

  

  if (!codec.configMicBias(false, true, TLV320_MICBIAS_AVDD) ||
      !codec.setHeadsetDetect(true) ||
      !codec.setInt1Source(true, true, false, false, false,
                           false) || // GPIO1 is detect headset or button press
      !codec.setGPIO1Mode(TLV320_GPIO1_INT1)) {
    Serial.println("Failed to configure headset detect");
    return;
  }
  
  Serial.println("TLV config done!");

  i2s.setBitsPerSample(16);
  // start I2S at the sample rate with 16-bits per sample
  if (!i2s.begin(sampleRate)) {
    Serial.println("Failed to initialize I2S!");
    while (1); // do nothing
  }
}
