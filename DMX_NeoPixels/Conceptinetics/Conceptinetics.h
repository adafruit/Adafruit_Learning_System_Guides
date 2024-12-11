/*
  Conceptinetics.h - DMX library for Arduino
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

/*
  This code has been tested using the following hardware:

  - Arduino / Genuino UNO R3 using a CTC-DRA-13-1 ISOLATED DMX-RDM SHIELD 
  - Arduino / Genuino MEGA2560 R3 using a CTC-DRA-13-1 ISOLATED DMX-RDM SHIELD 
  - Arduino / Genuino Leonardo using a CTC-DRA-13-R2 ISOLATED DMX-RDM SHIELD 

  - CTC-DRA-10-1 and CTC-DRA-10-R2 is the Non-isolated costs effective DMX-RDM shield 
*/


#ifndef CONCEPTINETICS_H_
#define CONCEPTINETICS_H_

#include <Arduino.h>
#include <inttypes.h>

#include "Rdm_Uid.h"
#include "Rdm_Defines.h"

#define DMX_MAX_FRAMESIZE       513     // Startbyte + 512 Slots
#define DMX_MIN_FRAMESIZE       2       // Startbyte + 1 Slot

#define DMX_MAX_FRAMECHANNELS   512     // Maxmim number of channer per frame

#define DMX_STARTCODE_SIZE      1       // Size of startcode in bytes

#define DMX_START_CODE          0x0     // Start code for a DMX frame
#define RDM_START_CODE          0xcc    // Start code for a RDM frame

// Uncomment to enable Inter slot delay ) (avg < 76uSec) ... 
// mimum is zero according to specification
// #define DMX_IBG				    10      // Inter slot time

// Speed your Arduino is running on in Hz.
#define F_OSC 				    16000000UL

// DMX Baudrate, this should be 250000
#define DMX_BAUD_RATE 		    250000

// The baudrate used to automaticly generate a break within
// your ISR.. make it lower to generate longer breaks
//#define DMX_BREAK_RATE 	 	    99900       

// 2017, Feb 28: Set to appox 176us
#define DMX_BREAK_RATE          49950       

// Tabel 3-2 ANSI_E1-20-2010 
// Minimum time to allow the datalink to 'turn arround'
#define MIN_RESPONDER_PACKET_SPACING_USEC   176 /*176*/

// Define which serial port to use as DMX port, only one can be 
// selected at the time by uncommenting one of the following
// lines
#define USE_DMX_SERIAL_0
//#define USE_DMX_SERIAL_1
//#define USE_DMX_SERIAL_2
//#define USE_DMX_SERIAL_3

namespace dmx 
{
    enum dmxState 
	{
        dmxUnknown,
        dmxStartByte,
        dmxWaitStartAddress,
        dmxData,
        dmxFrameReady,
	};
};

namespace rdm
{
    enum rdmState
    {
        rdmUnknown,
        rdmStartByte,
        rdmSubStartCode,
        rdmMessageLength,
        rdmData,
        rdmChecksumHigh,
        rdmChecksumLow,
        rdmFrameReady,
    };
};

struct IFrameBuffer
{
    virtual uint16_t    getBufferSize   ( void ) = 0;        

    virtual uint8_t     getSlotValue    ( uint16_t index ) = 0;
    virtual void        setSlotValue    ( uint16_t index, uint8_t value ) = 0;
};

class DMX_FrameBuffer : IFrameBuffer
{
    public:
        //
        // Constructor buffersize = 1-513
        //
        DMX_FrameBuffer     ( uint16_t buffer_size );
        DMX_FrameBuffer     ( DMX_FrameBuffer &buffer );
        ~DMX_FrameBuffer    ( void );

        uint16_t getBufferSize ( void );        

        uint8_t getSlotValue ( uint16_t index );
        void    setSlotValue ( uint16_t index, uint8_t value );
        void    setSlotRange ( uint16_t start, uint16_t end, uint8_t value );
        void    clear ( void );        

        uint8_t &operator[] ( uint16_t index );

    private:

        uint8_t     *m_refcount;
        uint16_t    m_bufferSize;
        uint8_t     *m_buffer;      
};


//
// DMX Master controller
//
class DMX_Master
{
    public:
        // Run the DMX master from a pre allocated frame buffer which
        // you have fully under your own control
        DMX_Master ( DMX_FrameBuffer &buffer, int readEnablePin  );
        
        // Run the DMX master by giving a predefined maximum number of
        // channels to support
        DMX_Master ( uint16_t maxChannel, int readEnablePin );

        ~DMX_Master ( void );
    
        void enable  ( void );              // Start transmitting
        void disable ( void );              // Stop transmitting

        // Get reference to the internal framebuffer
        DMX_FrameBuffer &getBuffer ( void );

        // Update channel values
        void setChannelValue ( uint16_t channel, uint8_t value );
        void setChannelRange ( uint16_t start, uint16_t end, uint8_t value );

    public:
        //
        // Manual control over the break period
        //
        void setAutoBreakMode ( void );     // Generated from ISR
        void setManualBreakMode ( void );   // Generate manually

        uint8_t autoBreakEnabled ( void );

        // We are waiting for a manual break to be generated 
        uint8_t waitingBreak ( void );
        
        // Generate break and start transmission of frame
        void breakAndContinue ( uint8_t breakLength_us = 100 );


    protected:
        void setStartCode ( uint8_t value ); 


    private:
        DMX_FrameBuffer m_frameBuffer;
        uint8_t         m_autoBreak;
};


//
// DMX Slave controller
//
class DMX_Slave : public DMX_FrameBuffer
{
    public:
        DMX_Slave ( DMX_FrameBuffer &buffer, int readEnablePin = -1 );

        // nrChannels is the consecutive DMX512 slots required
        // to operate this slave device
        DMX_Slave ( uint16_t nrChannels, int readEnablePin = -1 );

        ~DMX_Slave ( void );

        void enable     ( void );           // Enable receiver
        void disable    ( void );           // Disable receiver

 
        // Get reference to the internal framebuffer
        DMX_FrameBuffer &getBuffer ( void );

        uint8_t  getChannelValue ( uint16_t channel );

        uint16_t getStartAddress ( void );
        void     setStartAddress ( uint16_t );


        // Process incoming byte from USART
        bool processIncoming   ( uint8_t val, bool first = false );

        // Register on receive complete callback in case
        // of time critical applications
        void onReceiveComplete ( void (*func)(unsigned short) );

    protected:


    private:
        uint16_t        m_startAddress;     // Slave start address
        dmx::dmxState   m_state;

        static void (*event_onFrameReceived)(unsigned short channelsReceived);
};


class RDM_FrameBuffer : public IFrameBuffer
{
    public:
        //
        // Constructor
        //
        RDM_FrameBuffer     ( void ) {};
        ~RDM_FrameBuffer    ( void ) {};

        uint16_t getBufferSize ( void );        

        uint8_t getSlotValue ( uint16_t index );
        void    setSlotValue ( uint16_t index, uint8_t value );
        void    clear ( void );        

        uint8_t &operator[] ( uint16_t index );

    public: // functions to provide access from USART       
        // Process incoming byte from USART, 
        // returns false when no more data is accepted
        bool processIncoming ( uint8_t val, bool first = false );

        // Process outgoing byte to USART
        // returns false when no more data is available
        bool fetchOutgoing ( volatile uint8_t *udr, bool first = false );

    protected:
        // Process received frame
        virtual void processFrame ( void ) = 0;

    //private:
    protected:
        rdm::rdmState   m_state;       // State for pushing the message in
        RDM_Message     m_msg;
        RDM_Checksum    m_csRecv;      // Checksum received in rdm message
};

//
// RDM_Responder 
//
class RDM_Responder : public RDM_FrameBuffer
{
    public:
        //
        // m        = manufacturer id (16bits)
        // d1-d4    = device id (32bits)
        //
        RDM_Responder   ( uint16_t m, uint8_t d1, uint8_t d2, uint8_t d3, uint8_t d4, DMX_Slave &slave);
        ~RDM_Responder  ( void );

        void    setDeviceInfo 
                ( 
                    uint16_t deviceModelId, 
                    rdm::RdmProductCategory productCategory,
                    uint8_t personalities = 1,
                    uint8_t personality = 1
                )
        {
            m_DeviceModelId         = deviceModelId;
            m_ProductCategory       = productCategory;
            m_Personalities         = personalities;
            m_Personality           = personality;
        };

        //
        // Set vendor software version id
        //
        // v1 = MOST SIGNIFICANT
        // v2... 
        // v3...
        // v4 = LEAST SIGNIFICANT
        //
        void    setSoftwareVersionId ( uint8_t v1, uint8_t v2, uint8_t v3, uint8_t v4 )
        {
            m_SoftwareVersionId[0] = v1;
            m_SoftwareVersionId[1] = v2;
            m_SoftwareVersionId[2] = v3;
            m_SoftwareVersionId[3] = v4;
        }

        // Currently no sensors and subdevices supported
        // void    AddSensor ( void );
        // void    AddSubDevice ( void );

        uint8_t getPersonality ( void ) { return m_Personality; };
        void    setPersonality ( uint8_t personality ) { m_Personality = personality; };
   
        // Register on identify device event handler
        void    onIdentifyDevice ( void (*func)(bool) );
        void    onDeviceLabelChanged ( void (*func) (const char*, uint8_t) );
        void    onDMXStartAddressChanged ( void (*func) (uint16_t) );
        void    onDMXPersonalityChanged ( void (*func) (uint8_t) );


        // Set the device label
        void    setDeviceLabel ( const char *label, size_t len );

        // Enable, Disable rdm responder
        void enable ( void )    { m_rdmStatus.enabled = true; m_rdmStatus.mute = false; };
        void disable ( void )   { m_rdmStatus.enabled = false; };

        union
        {
            uint8_t  raw;
            struct
            {
                uint8_t mute:1; 
                uint8_t ident:1;
                uint8_t enabled:1;  // Rdm responder enable/disable
            };
        } m_rdmStatus;


    protected:  
        virtual void processFrame ( void );

        // Discovery to unque brach packets only requires
        // the data part of the packet to be transmitted
        // without breaks or header
        void repondDiscUniqueBranch ( void );

        // Helpers for generating response packets which 
        // have larger datafields
        void populateDeviceInfo ( void );

    private:
        RDM_Uid                     m_devid;            // Holds our unique device ID
        uint8_t                     m_Personalities;    // The total number of supported personalities
        uint8_t                     m_Personality;      // The currently active personality
        uint16_t                    m_DeviceModelId;
        uint8_t                     m_SoftwareVersionId[4]; // 32 bit Software version
        rdm::RdmProductCategory     m_ProductCategory;
 
        char                        m_deviceLabel[32];  // Device label

        static void (*event_onIdentifyDevice)(bool);
        static void (*event_onDeviceLabelChanged)(const char*, uint8_t);
        static void (*event_onDMXStartAddressChanged)(uint16_t);
        static void (*event_onDMXPersonalityChanged)(uint8_t);
};


#endif /* CONCEPTINETICS_H_ */
