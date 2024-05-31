// SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// adapted from the LampArray example from the Microsoft_HidForWindows library

#include <Microsoft_HidForWindows.h>
#include <Adafruit_NeoPixel.h>

#define NEO_PIXEL_PIN PIN_DATA

// NeoPixel-Shield has 40 neopixels
#define NEO_PIXEL_LAMP_COUNT 64

#define NEO_PIXEL_TYPE (NEO_GRB + NEO_KHZ800) // use "NEO_GRBW" for RGBW neopixels

Adafruit_NeoPixel neoPixelShield = Adafruit_NeoPixel(NEO_PIXEL_LAMP_COUNT, NEO_PIXEL_PIN, NEO_PIXEL_TYPE);

// UpdateLatency for all Lamps set to 4msec as it just seems reasonable.
#define NEO_PIXEL_LAMP_UPDATE_LATENCY (0x04)

// The Host needs to know the location of every Lamp in the LampArray (X/Y/Z position) and other metadata.
// See "26.7 LampArray Attributes and Interrogation" https://usb.org/sites/default/files/hut1_4.pdf#page=336
static LampAttributes neoPixelShieldLampAttributes[] PROGMEM = 
{
    // All positions in millimeters from upper-left corner of device.
    // All times in milliseconds.
    // Id  X     Y     Z     Latency                        Purposes           RED   GRN   BLUE  GAIN  PROGRAMMABLE?        KEY
    {0x00, 0x03, 0x08, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x01, 0x0C, 0x08, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x02, 0x15, 0x08, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x03, 0x1E, 0x08, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x04, 0x27, 0x08, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x05, 0x30, 0x08, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x06, 0x39, 0x08, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x07, 0x42, 0x08, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x08, 0x03, 0x13, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x09, 0x0C, 0x13, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x0A, 0x15, 0x13, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x0B, 0x1E, 0x13, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x0C, 0x27, 0x13, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x0D, 0x30, 0x13, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x0E, 0x39, 0x13, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x0F, 0x42, 0x13, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x10, 0x03, 0x1E, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x11, 0x0C, 0x1E, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x12, 0x15, 0x1E, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x13, 0x1E, 0x1E, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x14, 0x27, 0x1E, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x15, 0x30, 0x1E, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x16, 0x39, 0x1E, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x17, 0x42, 0x1E, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x18, 0x03, 0x29, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x19, 0x0C, 0x29, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x1A, 0x15, 0x29, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x1B, 0x1E, 0x29, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x1C, 0x27, 0x29, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x1D, 0x30, 0x29, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x1E, 0x39, 0x29, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x1F, 0x42, 0x29, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x20, 0x03, 0x34, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x21, 0x0C, 0x34, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x22, 0x15, 0x34, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x23, 0x1E, 0x34, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x24, 0x27, 0x34, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x25, 0x30, 0x34, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x26, 0x39, 0x34, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x27, 0x42, 0x34, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x28, 0x03, 0x3F, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x29, 0x0C, 0x3F, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x2A, 0x15, 0x3F, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x2B, 0x1E, 0x3F, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x2C, 0x27, 0x3F, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x2D, 0x30, 0x3F, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x2E, 0x39, 0x3F, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x2F, 0x42, 0x3F, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x30, 0x03, 0x4A, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x31, 0x0C, 0x4A, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x32, 0x15, 0x4A, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x33, 0x1E, 0x4A, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x34, 0x27, 0x4A, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x35, 0x30, 0x4A, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x36, 0x39, 0x4A, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x37, 0x42, 0x4A, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x38, 0x03, 0x55, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x39, 0x0C, 0x55, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x3A, 0x15, 0x55, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x3B, 0x1E, 0x55, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x3C, 0x27, 0x55, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x3D, 0x30, 0x55, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x3E, 0x39, 0x55, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00},
    {0x3F, 0x42, 0x55, 0x00, NEO_PIXEL_LAMP_UPDATE_LATENCY, LampPurposeAccent, 0xFF, 0xFF, 0xFF, 0x01, LAMP_IS_PROGRAMMABLE, 0x00}
};
static_assert(((sizeof(neoPixelShieldLampAttributes) / sizeof(LampAttributes)) == NEO_PIXEL_LAMP_COUNT), "neoPixelShieldLampAttributes must have NEO_PIXEL_LAMP_COUNT items.");

// All lengths in millimeters.
// All times in milliseconds.
Microsoft_HidLampArray lampArray = Microsoft_HidLampArray(NEO_PIXEL_LAMP_COUNT, 70, 55, 1, LampArrayKindPeripheral, 33, neoPixelShieldLampAttributes);

// When the LampArray is in Autonomous-Mode, displays solid blue.
uint32_t lampArrayAutonomousColor = neoPixelShield.Color(0, 0, 1);

void setup()
{
    // Initialize the NeoPixel library.
    neoPixelShield.begin();
    neoPixelShield.clear();

    // Always initially in Autonomous-Mode.
    neoPixelShield.fill(lampArrayAutonomousColor, 0, NEO_PIXEL_LAMP_COUNT - 1);
    neoPixelShield.show();
}

void loop()
{
    LampArrayColor currentLampArrayState[NEO_PIXEL_LAMP_COUNT];
    bool isAutonomousMode = lampArray.getCurrentState(currentLampArrayState);

    bool update = false;

    for (uint16_t i = 0; i < NEO_PIXEL_LAMP_COUNT; i++)
    {
        // Autonomous-Mode is the Host's mechanism to indicate to the device, that the device should decide what to render.
        // The Host may do this when no application is using the LampArray, so it has nothing to render.
        // In this case, this LampArray will revert to it's default/background effect, rendering 'blue'.
        uint32_t newColor = isAutonomousMode ? lampArrayAutonomousColor : lampArrayColorToNeoPixelColor(currentLampArrayState[i]);
        if (newColor != neoPixelShield.getPixelColor(i))
        {
            neoPixelShield.setPixelColor(i, newColor);
            update = true;
        }
    }

    // Only call update on the NeoPixels when something has changed, show() takes a long time to execute.
    if (update)
    {
        // Send the updated pixel color to hardware.
        neoPixelShield.show();
    }
}

uint32_t lampArrayColorToNeoPixelColor(LampArrayColor lampArrayColor)
{
    return neoPixelShield.Color(lampArrayColor.RedChannel, lampArrayColor.GreenChannel, lampArrayColor.BlueChannel);
}
