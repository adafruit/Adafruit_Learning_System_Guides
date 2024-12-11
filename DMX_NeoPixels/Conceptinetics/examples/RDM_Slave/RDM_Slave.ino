/*
  RDM_Responder.ino - Example code for using the Conceptinetics DMX library
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


#include <Conceptinetics.h>

//
// CTC-DRA-13-1 ISOLATED DMX-RDM SHIELD JUMPER INSTRUCTIONS
//
// RXEN JUMPER: DE 2  " This allows the software to control reads and writes
//
// The !EN Jumper should be either placed in the G (GROUND) 
// position to enable the shield circuitry 
//   OR
// if one of the pins is selected the selected pin should be
// set to OUTPUT mode and set to LOGIC LOW in order for the 
// shield to work
//

// CTC-DRA-10-1 NON ISOLATED DMX-RDM SHIELD JUMPER INSTRUCTIONS
// JUMPER 1: EN        " Shield is enabled
// JUMPER 2: DE        " Read Write control via Digital 2
// JUMPER 3: TX-uart   " Use UART for transmitting data
// JUMPER 4: RX-uart   " Use UART for receiving data

//
// DMX512FootPrint (Number of slave channels)
//
#define DMX_SLAVE_CHANNELS   10 


//
// Pin number to change read or write mode on the shield
// Uncomment the following line if you choose to control 
// read and write via a pin
//
// On the CTC-DRA-13-1 and CTC-DRA-10-1 shields this will always be pin 2,
// if you are using other shields you should look it up 
// yourself
//
#define RXEN_PIN                2


// Configure a DMX slave controller
DMX_Slave       dmx_slave ( DMX_SLAVE_CHANNELS, RXEN_PIN );

// Setup RDM Responder with out manufacturer id and
// unique device id
//
// Manufacturer ID: 0x0707
// Device ID:       0x01 0x02 0x03 0x04
//
RDM_Responder rdm_responder ( 0x0707, 0x1, 0x2, 0x3, 0x4, dmx_slave );

// Led pin used for identification of this responder via RDM
const int ledPin = 13;

// the setup routine runs once when you press reset:
void setup() {             
  
  // Set initial start address, this can be changed remotely via RDM
  dmx_slave.setStartAddress (1);
  
  // Setup device info to propagate
  rdm_responder.setDeviceInfo
    (
    0x1,                           // Device model ID (manufacturers unique model identifier
    rdm::CategoryScenicDrive,      // We pretend to be a scenic drive controller
    2,                             // Available personlities
    1                              // Current personality
    );
 
  // Set vendor software version id
  rdm_responder.setSoftwareVersionId ( 0x00, 0x01, 0x00, 0x01 );
  
  // Register deveice identification event handler
  rdm_responder.onIdentifyDevice ( OnIdentifyDevice );
  
  // Enable DMX slave interface and start recording (without RDM won't work)
  dmx_slave.enable ();  
  
  // Enable RMD responder (without an active DMX_Slave the RDM responder will not work sinde
  // it is integrated into the DMX_Slave object)
  rdm_responder.enable ();
  
  
  // Set led pin as output pin
  pinMode ( ledPin, OUTPUT );
}

// the loop routine runs over and over again forever:
void loop() 
{
  // Do stuff here
}


// Turn led on if identification is turned on, else turn the 
// led off
void OnIdentifyDevice (bool identify)
{
    digitalWrite ( ledPin, identify ? HIGH : LOW );
}
