/*
  Rdm_Defines.h - DMX library for Arduino with RDM (Remote Device Management) support
  Copyright (c) 2013 W.A. van der Meeren <danny@illogic.nl>.  All right reserved.

  This library is free software; you can redistribute it and/or
  modify it under the terms of the GNU Lesser General Public
  License as published by the Free Software Foundation; either
  version 3 of the License, or (at your option) any later version.

  This library is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
  Lesser General Public License for more details.

  You should have received a copy of the GNU Lesser General Public
  License along with this library; if not, write to the Free Software
  Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
*/


#ifndef RDM_DEFINES_H_
#define RDM_DEFINES_H_

#include "Rdm_Uid.h"

#define RDM_MAX_DEVICELABEL_LENGTH 32

namespace rdm
{
    enum RdmCommandClass
    {
        DiscoveryCommand            = 0x10,
        DiscoveryCommandResponse,
        GetCommand                  = 0x20,
        GetCommandResponse,
        SetCommand                  = 0x30,
        SetCommandResponse,
    };

    enum RdmResponseTypes
    {
        ResponseTypeAck              = 0x00,
        ResponseTypeAckTimer,
        ResponseTypeNackReason,
        ResponseTypeAckOverflow,             // Additional response data available (see spec) 
    };

    enum RdmParameters
    {
        // Category - Network Management
        DiscUniqueBranch                = 0x0001,   // Required
        DiscMute                        = 0x0002,   // Required
        DiscUnMute                      = 0x0003,   // Required

        CommsStatus                     = 0x0015,   // Get,Set

        // Category - Status Collection
        QueuedMessage                   = 0x0020,   // Get      [enum RdmStatusTypes]
        StatusMessages                  = 0x0030,   // Get      [enum RdmStatusTypes]
        StatusIdDescription             = 0x0031,   // Get
        ClearStatusId                   = 0x0032,   // Set
        SubDeviceStatusReportThreshold  = 0x0033,   // Get, Set [enum RdmStatusTypes]

        // Category - RDM Information
        // ** Only required if supporting parameters 
        //    beyond the minimum required set
        SupportedParameters             = 0x0005,   // Get, **Required
        ParameterDescription            = 0x0051,   // Get, **Required
    
        // Category = Product Information
        DeviceInfo                      = 0x0060,   // Get, Required
        ProductDetailIdList             = 0x0070,   // Get
        DeviceModelDescription          = 0x0080,   // Get
        ManufacturerLabel               = 0x0081,   // Get
        DeviceLabel                     = 0x0082,   // Get, Set
        FactoryDefaults                 = 0x0009,   // Get, Set **
        SoftwareVersionLabel            = 0x000c,   // Get
      
        // Category - DMX512 Setup
        DmxPersonality                  = 0x00e0,   // Get, Set
        DmxPersonalityDescription       = 0x00e1,   // Get
        DmxStartAddress                 = 0x00f0,   // Get, Set ** Required if DMX device
        SlotInfo                        = 0x0120,   // Get
        SlotDescription                 = 0x0121,   // Get
        DefaultSlotValue                = 0x0122,   // Get

        // Category - Sensors
        // Category - Dimmer Settings
        // Category - Power/Lamp Settings
        // Category - Display Settings
        // Category - Configuration

        // Category - Control
        IdentifyDevice                  = 0x1000,   // Get, Set, Required
        ResetDevice                     = 0x1001,   // Set
        PowerState                      = 0x1010,   // Get, Set
        PerformSelftest                 = 0x1020,   // Get, Set
        SelfTestDescription             = 0x1021,   // Get
    };


    enum RdmStatusTypes
    {
        StatusNone              = 0x00,
        StatusGetLastMessage,
        StatusAdvisory,
        StatusWarning,
        StatusError,
        StatusAdvisoryCleared   = 0x12,
        StatusWarningCleared,
        StatusErrorCleared,
    };
   
    enum RdmProductCategory
    {
        CategoryNotDeclared          = 0x0000,

        // Fixtures - intended as source for illumination
        CategoryFixture                     = 0x0100,
        CategoryFixtureFixed                = 0x0101,
        CategoryFixtureMovingYoke           = 0x0102,
        CategoryFixtureMovingMirror         = 0x0103,
        CategoryFixtureOther                = 0x01ff,
        
        // Fixture Accessories - add-ons to fixtures or projectors
        CategoryFixtureAccessory            = 0x0200,
        CategoryFixtureAccessoryColor       = 0x0201,
        CategoryFixtureAccessoryYoke        = 0x0202,
        CategoryFixtureAccessoryMirror      = 0x0203,
        CategoryFixtureAccessoryEffect      = 0x0204,
        CategoryFixtureAccessoryBeam        = 0x0205,
        CategoryFixtureAccessoryOther       = 0x02ff,

        // Projectors - Light source capable of producing
        // realistic images from another media
        CategoryProjector                   = 0x0300,
        CategoryProjectorFixed              = 0x0301,
        CategoryProjectorMovingYoke         = 0x0302,
        CategoryProjectorMovingMirror       = 0x0303,
        CategoryProjectorOther              = 0x03ff,

        // Atmospheric Effect - earth/wind/fire
        CategoryAtmospheric                 = 0x0400,
        CategoryAtmosphericEffect           = 0x0401, // Fogger, Hazer, Flame
        CategoryAtmosphericPyro             = 0x0402,
        CategoryAtmosphericOther            = 0x04ff,

        // Insensity Control (Specifically dimming equipment)
        CategoryDimmer                      = 0x0500,
        CategoryDimmer_AC_Incandescent      = 0x0501,
        CategoryDimmer_AC_Fluorescent       = 0x0502,
        CategoryDimmer_AC_Coldcathode       = 0x0503,
        CategoryDimmer_AC_Nondim            = 0x0504,
        CategoryDimmer_AC_Elv               = 0x0505,
        CategoryDimmer_AC_Other             = 0x0506,
        CategoryDimmer_DC_Level             = 0x0507,
        CategoryDimmer_DC_PWM               = 0x0508,
        CategoryDimmer_CS_LED               = 0x0509,
        CategoryDimmer_Other                = 0x05ff,

        // Power control (Other than dimming equipment)
        CategoryPower                       = 0x0600,
        CategoryPowerControl                = 0x0601,
        CategoryPowerSource                 = 0x0602,
        CategoryPowerOther                  = 0x06ff,

        // Scenic Drive - Including motorized effects 
        // unrelated to light source
        CategoryScenic                      = 0x0700,
        CategoryScenicDrive                 = 0x0701,
        CategoryScenicOther                 = 0x07ff,

        // DMX Infrastructure, conversion and interfaces
        CategoryData                        = 0x0800,
        CategoryDataDistribution            = 0x0801,
        CategoryDataConversion              = 0x0802,
        CategoryDataOther                   = 0x08ff,

        // Audio visual equipment
        Category_AV                         = 0x0900,
        Category_AV_Audio                   = 0x0901,
        Category_AV_Video                   = 0x0902,
        Category_AV_Other                   = 0x09ff,

        // Parameter monitoring equipment
        CategoryMonitor                     = 0x0a00,
        CategoryMonitorACLinePower          = 0x0a01,
        CategoryMonitorDCPower              = 0x0a02,
        CategoryMonitorEnvironmental        = 0x0a03,
        CategoryMonitorOther                = 0x0aff,

        // Controllers, backup devices
        CategoryControl                     = 0x7000,
        CategoryControlController           = 0x7001,
        CategoryControlBackupdevice         = 0x7002,
        CategoryControlOther                = 0x70ff,

        // Test equipment
        CategoryTest                        = 0x7100,
        CategoryTestEquipment               = 0x7101,
        CategoryTestEquipmentOther          = 0x71ff,

        // Miscellaneous
        CategoryOther                       = 0x7fff,
    };

    // 
    // Product details not yet supported in
    // this library
    //
    enum RdmProductDetail
    {
        ProductDetailNotDeclared        = 0x0000,
    };

    // Only LSB
    enum RdmNackReasons
    {
        UnknownPid                      = 0x00,
        FormatError,
        HardwareFault,
        ProxyReject,
        WriteProtect,
        UnsupportedCmdClass,
        DataOutOfRange,
        BufferFull,
        PacketSizeUnsupported,
        SubDeviceOutOfRange,
        ProxyBufferFull
    };

};


#define RDM_HDR_LEN             24      // RDM Message header length ** fixed
#define RDM_PD_MAXLEN           32      // RDM Maximum parameter data length 1 - 231


union RDM_Message
{
    uint8_t         d[ RDM_HDR_LEN + RDM_PD_MAXLEN ];
    struct
    {
        uint8_t     startCode;        // 0        SC_RDM
        uint8_t     subStartCode;     // 1        SC_SUB_MESSAGE
        uint8_t     msgLength;        // 2        Range 24 - 255
        RDM_Uid     dstUid;         // 3-8      Destination UID
        RDM_Uid     srcUid;         // 9-14     Source UID (sender)
        uint8_t     TN;               // 15       Transaction number
        uint8_t     portId;           // 16       Port ID / Response type
        uint8_t     msgCount;         // 17
        uint16_t    subDevice;        // 18,19    0=root, 0xffff=all
        uint8_t     CC;               // 20       GET_COMMAND
        uint16_t    PID;              // 21,22    Parameter ID
        uint8_t     PDL;              // 23       Parameter Data length 1-231 

        uint8_t     PD[RDM_PD_MAXLEN];    // Parameter Data ... variable length 
    };
};

union RDM_Checksum
{
    uint16_t checksum;
    struct
    {
        uint8_t csl;
        uint8_t csh;
    };
};

struct RDM_DiscUniqueBranchPD
{
    RDM_Uid lbound;
    RDM_Uid hbound;
};

struct RDM_DiscMuteUnMutePD
{
    uint16_t    ctrlField;

// Only for multiple ports
//    RDM_Uid     bindingUid;
};

struct RDM__DeviceInfoPD
{
    uint8_t     protocolVersionMajor;
    uint8_t     protocolVersionMinor;
    uint16_t    deviceModelId;
    uint16_t    ProductCategory;        // enum RdmProductCategory
    uint8_t     SoftwareVersionId[4]; 
    uint16_t    DMX512FootPrint;
    uint8_t     DMX512CurrentPersonality;
    uint8_t     DMX512NumberPersonalities;
    uint16_t    DMX512StartAddress;
    uint16_t    SubDeviceCount;
    uint8_t     SensorCount;
};

struct RDM_DeviceGetPersonality_PD
{
    uint8_t     DMX512CurrentPersonality;
    uint8_t     DMX512NumberPersonalities;
};

struct RDM_DeviceSetPersonality_PD
{
    uint8_t     DMX512Personality;
};


#endif /* RDM_DEFINES_H_ */
