/*
  DMX_Master.ino - Example code for using the Conceptinetics DMX library
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
// When configuring a DMX_Master it will normally automaticly
// generate breaks and continues sending the next frame.
// However, if you would like to have more control over the 
// break period and when it to happen then this example is meant for you


//
// CTC-DRA-13-1 ISOLATED DMX-RDM SHIELD JUMPER INSTRUCTIONS
//
// If you are using the above mentioned shield you should 
// place the RXEN jumper towards pin number 2, this allows the
// master controller to put to iso shield into transmit 
// (DMX Master) mode 
//
//
// The !EN Jumper should be either placed in the G (GROUND) 
// position to enable the shield circuitry 
//   OR
// if one of the pins is selected the selected pin should be
// set to OUTPUT mode and set to LOGIC LOW in order for the 
// shield to work
//


//
// The master will control 100 Channels (1-100)
// 
// depending on the ammount of memory you have free you can choose
// to enlarge or schrink the ammount of channels (minimum is 1)
//
#define DMX_MASTER_CHANNELS   100 

//
// Pin number to change read or write mode on the shield
//
#define RXEN_PIN                2


// Configure a DMX master controller, the master controller
// will use the RXEN_PIN to control its write operation 
// on the bus
DMX_Master        dmx_master ( DMX_MASTER_CHANNELS, RXEN_PIN );

const int break_usec = 200;

// the setup routine runs once when you press reset:
void setup() {             
  
  // Enable DMX master interface and start transmitting
  dmx_master.enable ();  
  
  // This will turn the DMX Master into manual break mode
  // After doing this you have to check wheter a break is 
  // expected and then invoke a Break to continue the next 
  // frame to be sent.
  dmx_master.setManualBreakMode ();
  
  // Set channel 1 - 50 @ 50%
  dmx_master.setChannelRange ( 2, 25, 127 );

  pinMode (13, OUTPUT);
}

// the loop routine runs over and over again forever:
void loop() 
{
  // Check if the DMX master is waiting for a break
  // to happen
  if ( dmx_master.waitingBreak () )
  {      
    // We rate limit the number of frames by creating
    // a 50msec gap between frames, this is merely done
    // as an example to demonstrate the breakAndContinue()
    delay ( 50 );
    
    // Invoke the breakAndContinue to start generating 
    // the break and then automaticly continue sending the
    // next frame.
    // Your application will block for a period 
    // length of a break and mark after break
    dmx_master.breakAndContinue ( break_usec );
  }  
  
  // TODO: Do your other operations part of your
  // program here...
  
 
}
