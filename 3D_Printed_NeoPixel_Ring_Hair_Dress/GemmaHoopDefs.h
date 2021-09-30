# SPDX-FileCopyrightText: 2017 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: GNU
/******************************************************************************
 *
 * this file is part of the gemma hoop animator example sketch
 *
 * it is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation, either version 3 of
 * the License, or (at your option) any later version.
 *
 * it is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  see the
 * GNU Lesser General Public License for more details.
 *
 * you should have received a copy of the GNU Lesser General Public
 * License along with NeoPixel.  If not, see
 * <http://www.gnu.org/licenses/>.
 *
 * ----------------------------------------------------------------------------
 *
 * these are the general definitions and declarations for the 
 * gemma hoop animator - unless you don't like the preset animations or
 * find a major bug, you don't need to change anything here
 *
 ******************************************************************************/

#ifndef _GEMMA_HOOP_DEFS_H_
#define _GEMMA_HOOP_DEFS_H_

/******************************************************************************
 *
 * available actions
 *
 ******************************************************************************/

#define ACT_NOP               0b00000000     // all leds off, do nothing
#define ACT_SIMPLE_RING       0b00000001     // all leds on
#define ACT_CYCLING_RING_ACLK 0b00000010     // anti clockwise cycling colors 
#define ACT_CYCLING_RING_CLKW 0b00000100     // clockwise cycling colors 
#define ACT_WHEEL_ACLK        0b00001000     // anti clockwise spinning wheel 
#define ACT_WHEEL_CLKW        0b00010000     // clockwise spinning wheel 
#define ACT_SPARKLING_RING    0b00100000     // sparkling effect 

/******************************************************************************
 *
 * available color generation methods
 *
 ******************************************************************************/

#define COL_RANDOM            0b01000000     // colors will be generated randomly
#define COL_SPECTRUM          0b10000000     // colors will be set as cyclic spectral wipe
                                             // R -> G -> B -> R -> ...

/******************************************************************************
 *
 * specifiyng the action list 
 *
 ******************************************************************************/
 
typedef struct
{
  uint16_t action_duration;       // the action's overall duration in milliseconds (be careful not 
                                  // to use values > 2^16-1 - roughly one minute :-)
  uint8_t action_and_color_gen;   // the color generation method
  uint16_t action_step_duration;  // the duration of each action step rsp. the delay of the main 
                                  // loop in milliseconds - thus, controls the action speed (be 
                                  // careful not to use values > 2^16-1 - roughly one minute :-)
  uint8_t color_granularity;      // controls the increment of the R, G, and B portions of the 
                                  // rsp. color. 1 means the increment is 0,1,2,3,..., 10 means 
                                  // the increment is 0,10,20,... don't use values > 255, and note
                                  // that even values > 127 wouldn't make much sense...
  uint16_t color_interval;        // controls the speed of color changing independently from action
                                  // speed (be careful not to use values > 2^16-1 - roughly one minute :-)
} actiondesc;

typedef actiondesc actionlist[];  // a simple array of actions that will be continously cycled through
                                  // by the sketch's main loop. the number of elemnts is limitted by
                                  // the size of RAM available on the rsp. µC
#endif

