// SPDX-FileCopyrightText: 2024 john park for Adafruit Industries
//
// SPDX-License-Identifier: MIT
/**
 * For USB MIDI Host Feather RP2040 with mini OLED FeatherWing and MIDI FeatherWing
 * Modified 12 Jun 2024 - @todbot -- added USB MIDI forwarding
 * Modified by @johnedgarpark -- added UART MIDI forwarding and display/message filtering
 * originally from: https://github.com/rppicomidi/EZ_USB_MIDI_HOST/blob/main/examples/arduino/EZ_USB_MIDI_HOST_PIO_example/EZ_USB_MIDI_HOST_PIO_example.ino
 */
 
 /* 
 * The MIT License (MIT)
 *
 * Copyright (c) 2023 rppicomidi
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 *
 */

/**
 * This demo program is designed to test the USB MIDI Host driver for a single USB
 * MIDI device connected to the USB Host port. It also
 * forwards MIDI received from the USB MIDI device to USB and UART MIDI devices.
 *
 * This program works with a single USB MIDI device connected via a USB hub, but it
 * does not handle multiple USB MIDI devices connected at the same time.
 * 
 *  Libraries (all available via library manager): 
 *  - MIDI -- https://github.com/FortySevenEffects/arduino_midi_library

 */
// Be sure to set the CPU clock to 120MHz or 240MHz before uploading to board
// USB Stack is TinyUSB
// Press A to change output MIDI channel
// Press B to change Program Change banks in groups of 8
// Press C for MIDI panic


#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

//#define WIRE Wire1  //only if display needs it.
#define SCREEN_WIDTH 128 // OLED display width, in pixels
#define SCREEN_HEIGHT 32 // OLED display height, in pixels
#define OLED_RESET     -1 // Reset pin # (or -1 if sharing Arduino reset pin)
#define SCREEN_ADDRESS 0x3C ///< See datasheet for Address; 0x3D for 128x64, 0x3C for OLED FeatherWing 128x32
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

//Screen buttons
const int buttonAPin = 9;
const int buttonBPin = 6;
const int buttonCPin = 5;
int buttonAState;
int buttonBState;
int buttonCState;
int lastButtonAState;
int lastButtonBState;
int lastButtonCState;
unsigned long lastDebounceATime = 0;
unsigned long lastDebounceBTime = 0;
unsigned long lastDebounceCTime = 0;
unsigned long debounceDelay = 50;

int userChannel = 1;  //1-16
int userProgOffset = 0;
   
#include <MIDI.h>  

#if defined(USE_TINYUSB_HOST) || !defined(USE_TINYUSB)
#error "Please use the Menu to select Tools->USB Stack: Adafruit TinyUSB"
#endif
#include "pio_usb.h"
#define HOST_PIN_DP   16   // Pin used as D+ for host, D- = D+ + 1
#include "EZ_USB_MIDI_HOST.h"

// USB Host object
Adafruit_USBH_Host USBHost;

USING_NAMESPACE_MIDI
USING_NAMESPACE_EZ_USB_MIDI_HOST

RPPICOMIDI_EZ_USB_MIDI_HOST_INSTANCE(usbhMIDI, MidiHostSettingsDefault)

Adafruit_USBD_MIDI usb_midi;                                  // USB MIDI object
MIDI_CREATE_INSTANCE(Adafruit_USBD_MIDI, usb_midi, MIDIusb);  // USB MIDI
MIDI_CREATE_INSTANCE(HardwareSerial, Serial1, MIDIuart);      // Serial MIDI over MIDI FeatherWing

static uint8_t midiDevAddr = 0;

static bool core0_booting = true;
static bool core1_booting = true;

/* MIDI IN MESSAGE REPORTING */
static void onMidiError(int8_t errCode)
{
    Serial.printf("MIDI Errors: %s %s %s\r\n", (errCode & (1UL << ErrorParse)) ? "Parse":"",
        (errCode & (1UL << ErrorActiveSensingTimeout)) ? "Active Sensing Timeout" : "",
        (errCode & (1UL << WarningSplitSysEx)) ? "Split SysEx":"");
}
int last_cc_cntrl = 1;

static void midiPanic()
{
    for (int i=0; i<128; i++)
    {
      MIDIusb.sendNoteOff(i, 0, userChannel);
      MIDIuart.sendNoteOff(i, 0, userChannel);
      Serial.printf("note %u off\r\n", i);
      last_cc_cntrl = 0;  // dirty this
    }
}

static void onNoteOff(Channel channel, byte note, byte velocity)
{
    MIDIusb.sendNoteOff(note, velocity, userChannel);
    MIDIuart.sendNoteOff(note, velocity, userChannel);
    Serial.printf("ch%u: Note off#%u v=%u\r\n", userChannel, note, velocity);

    display.setCursor(0,12);
    display.setTextColor(SSD1306_WHITE, SSD1306_BLACK);
    display.setTextWrap(false);
    display.printf("Ch %u > %u  Note %u     \r\n", channel, userChannel, note);
    display.display();
    last_cc_cntrl = 0; 
}

static void onNoteOn(Channel channel, byte note, byte velocity)
{
    MIDIusb.sendNoteOn(note, velocity, userChannel);
    MIDIuart.sendNoteOn(note, velocity, userChannel);
    Serial.printf("ch%u: Note on#%u v=%u\r\n", userChannel, note, velocity);

    display.setCursor(0,12);
    display.setTextColor(SSD1306_WHITE, SSD1306_BLACK);
    display.setTextWrap(false);
    display.printf("Ch %u > %u  Note %u o\r\n", channel, userChannel, note);
    display.display();
    last_cc_cntrl = 0; 
    
}

static void onPolyphonicAftertouch(Channel channel, byte note, byte amount)
{
    Serial.printf("ch%u: PAT#%u=%u\r\n", userChannel, note, amount);
    MIDIusb.sendAfterTouch(note, amount, userChannel);
    MIDIuart.sendAfterTouch(note, amount, userChannel);
}


static void onControlChange(Channel channel, byte controller, byte value)
{
    MIDIusb.sendControlChange(controller, value, userChannel);
    MIDIuart.sendControlChange(controller, value, userChannel);
    Serial.printf("Ch %u CC#%u=%u\r\n", userChannel, controller, value);
    if (last_cc_cntrl != controller){
      display.setTextColor(SSD1306_WHITE, SSD1306_BLACK);
      display.setTextWrap(false);
      display.setCursor(0,12);
      display.printf("CC# %u                \r\n", controller);
      display.display();
      last_cc_cntrl = controller;
    }
    
}

static void onProgramChange(Channel channel, byte program)
{
    Serial.printf("ch%u: Prog=%u\r\n", userChannel, program);
    MIDIusb.sendProgramChange(program + userProgOffset, userChannel);
    MIDIuart.sendProgramChange(program + userProgOffset, userChannel);
    display.setTextColor(SSD1306_WHITE, SSD1306_BLACK);
    display.setCursor(0,24);
    display.printf("Progs %u-%u   [%u]   \r\n", userProgOffset, (userProgOffset + 7), (program + userProgOffset));
    display.display();
    last_cc_cntrl = 0;  // dirty this
    
}

static void onAftertouch(Channel channel, byte value)
{
    Serial.printf("ch%u: AT=%u\r\n", userChannel, value);
    MIDIusb.sendAfterTouch(value, userChannel);
    MIDIuart.sendAfterTouch(value, userChannel);
}

static void onPitchBend(Channel channel, int value)
{
    Serial.printf("ch%u: PB=%d\r\n", userChannel, value);
    MIDIusb.sendPitchBend(value, userChannel);
    MIDIuart.sendPitchBend(value, userChannel);
}

static void onSysEx(byte * array, unsigned size)
{
    Serial.printf("SysEx:\r\n");
    unsigned multipleOf8 = size/8;
    unsigned remOf8 = size % 8;
    for (unsigned idx=0; idx < multipleOf8; idx++) {
        for (unsigned jdx = 0; jdx < 8; jdx++) {
            Serial.printf("%02x ", *array++);
        }
        Serial.printf("\r\n");
    }
    for (unsigned idx = 0; idx < remOf8; idx++) {
        Serial.printf("%02x ", *array++);
    }
    Serial.printf("\r\n");
}

static void onSMPTEqf(byte data)
{
    uint8_t type = (data >> 4) & 0xF;
    data &= 0xF;    
    static const char* fps[4] = {"24", "25", "30DF", "30ND"};
    switch (type) {
        case 0: Serial.printf("SMPTE FRM LS %u \r\n", data); break;
        case 1: Serial.printf("SMPTE FRM MS %u \r\n", data); break;
        case 2: Serial.printf("SMPTE SEC LS %u \r\n", data); break;
        case 3: Serial.printf("SMPTE SEC MS %u \r\n", data); break;
        case 4: Serial.printf("SMPTE MIN LS %u \r\n", data); break;
        case 5: Serial.printf("SMPTE MIN MS %u \r\n", data); break;
        case 6: Serial.printf("SMPTE HR LS %u \r\n", data); break;
        case 7:
            Serial.printf("SMPTE HR MS %u FPS:%s\r\n", data & 0x1, fps[(data >> 1) & 3]);
            break;
        default:
          Serial.printf("invalid SMPTE data byte %u\r\n", data);
          break;
    }
}

static void onSongPosition(unsigned beats)
{
    Serial.printf("SongP=%u\r\n", beats);
    MIDIusb.sendSongPosition(beats);
    MIDIuart.sendSongPosition(beats);
}

static void onSongSelect(byte songnumber)
{
    Serial.printf("SongS#%u\r\n", songnumber);
    MIDIusb.sendSongSelect(songnumber);
    MIDIuart.sendSongSelect(songnumber);
}

static void onTuneRequest()
{
    Serial.printf("Tune\r\n");
    MIDIusb.sendTuneRequest();
    MIDIuart.sendTuneRequest();
}

static void onMidiClock()
{
    Serial.printf("Clock\r\n");
    MIDIusb.sendClock();
    MIDIuart.sendClock();
}

static void onMidiStart()
{
    Serial.printf("Start\r\n");
    MIDIusb.sendStart();
    MIDIuart.sendStart();
}

static void onMidiContinue()
{
    Serial.printf("Cont\r\n");
    MIDIusb.sendContinue();
    MIDIuart.sendContinue();
}

static void onMidiStop()
{
    Serial.printf("Stop\r\n");
    MIDIusb.sendStop();
    MIDIuart.sendStop();
}

static void onActiveSense()
{
    Serial.printf("ASen\r\n");
}

static void onSystemReset()
{
    Serial.printf("SysRst\r\n");
}

static void onMidiTick()
{
    Serial.printf("Tick\r\n");
}

static void onMidiInWriteFail(uint8_t devAddr, uint8_t cable, bool fifoOverflow)
{
    if (fifoOverflow)
        Serial.printf("Dev %u cable %u: MIDI IN FIFO overflow\r\n", devAddr, cable);
    else
        Serial.printf("Dev %u cable %u: MIDI IN FIFO error\r\n", devAddr, cable);
}

static void registerMidiInCallbacks()
{
    auto intf = usbhMIDI.getInterfaceFromDeviceAndCable(midiDevAddr, 0);
    if (intf == nullptr)
        return;
    intf->setHandleNoteOff(onNoteOff);                      // 0x80
    intf->setHandleNoteOn(onNoteOn);                        // 0x90
    intf->setHandleAfterTouchPoly(onPolyphonicAftertouch);  // 0xA0
    intf->setHandleControlChange(onControlChange);          // 0xB0
    intf->setHandleProgramChange(onProgramChange);          // 0xC0
    intf->setHandleAfterTouchChannel(onAftertouch);         // 0xD0
    intf->setHandlePitchBend(onPitchBend);                  // 0xE0
    intf->setHandleSystemExclusive(onSysEx);                // 0xF0, 0xF7
    intf->setHandleTimeCodeQuarterFrame(onSMPTEqf);         // 0xF1
    intf->setHandleSongPosition(onSongPosition);            // 0xF2
    intf->setHandleSongSelect(onSongSelect);                // 0xF3
    intf->setHandleTuneRequest(onTuneRequest);              // 0xF6
    intf->setHandleClock(onMidiClock);                      // 0xF8
    // 0xF9 as 10ms Tick is not MIDI 1.0 standard but implemented in the Arduino MIDI Library
    intf->setHandleTick(onMidiTick);                        // 0xF9
    intf->setHandleStart(onMidiStart);                      // 0xFA
    intf->setHandleContinue(onMidiContinue);                // 0xFB
    intf->setHandleStop(onMidiStop);                        // 0xFC
    intf->setHandleActiveSensing(onActiveSense);            // 0xFE
    intf->setHandleSystemReset(onSystemReset);              // 0xFF
    intf->setHandleError(onMidiError);

    auto dev = usbhMIDI.getDevFromDevAddr(midiDevAddr);
    if (dev == nullptr)
        return;
    dev->setOnMidiInWriteFail(onMidiInWriteFail);
}

/* CONNECTION MANAGEMENT */
static void onMIDIconnect(uint8_t devAddr, uint8_t nInCables, uint8_t nOutCables)
{
    Serial.printf("MIDI device at address %u has %u IN cables and %u OUT cables\r\n", devAddr, nInCables, nOutCables);
    midiDevAddr = devAddr;
    registerMidiInCallbacks();
}

static void onMIDIdisconnect(uint8_t devAddr)
{
    Serial.printf("MIDI device at address %u unplugged\r\n", devAddr);
    midiDevAddr = 0;
}


/* MAIN LOOP FUNCTIONS */

static void blinkLED(void)
{
    const uint32_t intervalMs = 1000;
    static uint32_t startMs = 0;

    static bool ledState = false;
    if ( millis() - startMs < intervalMs)
        return;
    startMs += intervalMs;

    ledState = !ledState;
    digitalWrite(LED_BUILTIN, ledState ? HIGH:LOW); 
}



// core1's setup
void setup1() {
    #if ARDUINO_ADAFRUIT_FEATHER_RP2040_USB_HOST 
        pinMode(18, OUTPUT);  // Sets pin USB_HOST_5V_POWER to HIGH to enable USB power
        digitalWrite(18, HIGH);
    #endif
  
    //while(!Serial);   // wait for native usb
    Serial.println("Core1 setup to run TinyUSB host with pio-usb\r\n");

    // Check for CPU frequency, must be multiple of 120Mhz for bit-banging USB
    uint32_t cpu_hz = clock_get_hz(clk_sys);
    if ( cpu_hz != 120000000UL && cpu_hz != 240000000UL ) {
        delay(2000);   // wait for native usb
        Serial.printf("Error: CPU Clock = %lu, PIO USB require CPU clock must be multiple of 120 Mhz\r\n", cpu_hz);
        Serial.printf("Change your CPU Clock to either 120 or 240 Mhz in Menu->CPU Speed \r\n");
        while(1) delay(1);
    }

    pio_usb_configuration_t pio_cfg = PIO_USB_DEFAULT_CONFIG;
    pio_cfg.pin_dp = HOST_PIN_DP;

 
    USBHost.configure_pio_usb(1, &pio_cfg);
    // run host stack on controller (rhport) 1
    // Note: For rp2040 pico-pio-usb, calling USBHost.begin() on core1 will have most of the
    // host bit-banging processing work done in core1 to free up core0 for other work
    usbhMIDI.begin(&USBHost, 1, onMIDIconnect, onMIDIdisconnect);
    core1_booting = false;
    while(core0_booting) ;
}

// core1's loop
void loop1()
{
    USBHost.task();
}

void setup()
{
    TinyUSBDevice.setManufacturerDescriptor("LarsCo");
    TinyUSBDevice.setProductDescriptor("MIDI Masseuse");
    Serial.begin(115200);
    if(!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    Serial.println(F("SSD1306 allocation failed"));
    for(;;); // Don't proceed, loop forever
  }

  // Show initial display buffer contents on the screen --
  // the library initializes this with an Adafruit splash screen.
  display.display();
  delay(2000); // Pause for 2 seconds
  // Clear the buffer
  display.clearDisplay();
  display.display();

  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE, SSD1306_BLACK);
  display.setCursor(0,0);
  display.print("USB MIDI Messenger");
  display.setCursor(0,12);
  display.print("Ch x > 1  Note_ CC#_\r\n");
  display.setCursor(0,24);
  display.printf("Progs %u-%u     \r\n", userProgOffset, (userProgOffset + 7));
  display.display();

  pinMode(buttonAPin, INPUT_PULLUP);
  pinMode(buttonBPin, INPUT);  // OLED button B as a 100k pullup on it on 128x32 FW
  pinMode(buttonCPin, INPUT_PULLUP);
  
    
    MIDIusb.begin();
    MIDIusb.turnThruOff();   // turn off echo
    
    MIDIuart.begin(MIDI_CHANNEL_OMNI); // don't forget OMNI
    
//     while(!Serial);   // wait for serial port
    pinMode(LED_BUILTIN, OUTPUT);
    Serial.println("USB Host to MIDI Messenger\r\n");
    core0_booting = false;
    while(core1_booting) ;
}

void loop() {    
    // Handle any incoming data; triggers MIDI IN callbacks
    usbhMIDI.readAll();
    // Do other processing that might generate pending MIDI OUT data
    
    // Tell the USB Host to send as much pending MIDI OUT data as possible
    usbhMIDI.writeFlushAll();

    // Do other non-USB host processing
    blinkLED();

    int readingA = digitalRead(buttonAPin);
    int readingB = digitalRead(buttonBPin);
    int readingC = digitalRead(buttonCPin);
    
    if (readingA != lastButtonAState) {
      lastDebounceATime = millis();
    }
    if (readingB != lastButtonBState) {
      lastDebounceBTime = millis();
    }
    if (readingC != lastButtonCState) {
      lastDebounceCTime = millis();
    }

    if ((millis() - lastDebounceATime) > debounceDelay) {
      if (readingA != buttonAState) {
        buttonAState = readingA;
        if (buttonAState == LOW) {
          userChannel = (userChannel % 16) + 1 ; // increment from 1-16
          Serial.printf("Ch%u\r\n", userChannel);
          display.setTextColor(SSD1306_WHITE, SSD1306_BLACK);
          display.setCursor(0,12);
          display.printf("Ch out %u          \r\n", userChannel);
          display.display();
          
        }
      }
    }


    if ((millis() - lastDebounceBTime) > debounceDelay) {
      if (readingB != buttonBState) {
        buttonBState = readingB;
        if (buttonBState == LOW) {
          userProgOffset = (userProgOffset + 8) % 128 ; 
          Serial.printf("Prog Progs %u   through %u\r\n", userProgOffset, (userProgOffset + 7));
          display.setTextColor(SSD1306_WHITE, SSD1306_BLACK);
          display.setCursor(0,24);
          display.printf("Progs %u-%u \r\n", userProgOffset, (userProgOffset + 7));
          display.display();
        }
      }
    }


    if ((millis() - lastDebounceCTime) > debounceDelay) {
      if (readingC != buttonCState) {
        buttonCState = readingC;
        if (buttonCState == LOW) {
          midiPanic();
        }
      }
    }
    
    lastButtonAState = readingA;
    lastButtonBState = readingB;
    lastButtonCState = readingC;

    
}
