// SPDX-FileCopyrightText: 2014 HerrRausB https://github.com/HerrRausB
//
// SPDX-License-Identifier: LGPL-3.0-or-later
//
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
 * use this file to set up your individual animation actions and
 * general settings and then simply recompile the sketch
 *
 * the number of actions possible is limited by the RAM of the used µC. shall
 * the list be too long, the µC will crash and nothing will go on.
 *
 * ----------------------------------------------------------------------------
 *
 * AND NOW HAVE FUN! :-)
 *
 ******************************************************************************/

#ifndef _GEMMA_HOOP_ACTIONLIST_H_
#define _GEMMA_HOOP_ACTIONLIST_H_

#include "GemmaHoopDefs.h"

/******************************************************************************
 *
 * general settings
 *
 ******************************************************************************/

#define PIXEL_OUTPUT 0           // output pin the NeoPixels are connected to
#define ANALOG_INPUT 0           // needed to seed the random generator
#define NUM_PIXELS 16            // total number of NeoPixels
#define BRIGHTNESS 30            // overall brightness of NeoPixels

/******************************************************************************
 *
 * defining the animation actions by simply initializing the array of actions
 * this array variable must be called theActionList !!!
 *
 * valid actions are:
 *    ACT_NOP                     simply do nothing and switch everything off
 *    ACT_SIMPLE_RING             all leds on
 *    ACT_CYCLING_RING_ACLK       anti clockwise cycling colors 
 *    ACT_CYCLING_RING_CLKW       clockwise cycling colors acording 
 *    ACT_WHEEL_ACLK              anti clockwise spinning wheel 
 *    ACT_WHEEL_CLKW              clockwise spinning wheel 
 *    ACT_SPARKLING_RING          sparkling effect 
 *
 * valid color options are:
 *    COL_RANDOM                  colors will be selected randomly, which might  
 *                                be not very sufficient due to well known 
 *                                limitations of the random generation algorithm
 *    COL_SPECTRUM                colors will be set as cyclic spectral wipe 
 *                                R -> G -> B -> R -> G -> B -> R -> ...
 *
 ******************************************************************************/

actionlist theActionList =
{
//  action    action name &                          action step    color        color change
//  duration  color generation method                duration       granularity  interval
  { 5000,     ACT_SPARKLING_RING | COL_RANDOM,       10,            25,          1000 },
  { 2000,     ACT_CYCLING_RING_CLKW | COL_RANDOM,    20,            1,           5 },
  { 5000,     ACT_SPARKLING_RING | COL_RANDOM,       10,            25,          1000 },
  { 2000,     ACT_CYCLING_RING_ACLK | COL_RANDOM,    20,            1,           5 },
  { 5000,     ACT_SPARKLING_RING | COL_RANDOM,       10,            25,          1000 },
  { 2500,     ACT_CYCLING_RING_CLKW | COL_SPECTRUM,  25,            20,          20 },
  { 1000,     ACT_CYCLING_RING_CLKW | COL_SPECTRUM,  50,            1,           20 },
  { 750,      ACT_CYCLING_RING_CLKW | COL_SPECTRUM,  75,            1,           20 },
  { 500,      ACT_CYCLING_RING_CLKW | COL_SPECTRUM,  100,           1,           20 },
  { 500,      ACT_CYCLING_RING_CLKW | COL_SPECTRUM,  125,           1,           20 },
  { 500,      ACT_CYCLING_RING_CLKW | COL_SPECTRUM,  150,           1,           50 },
  { 500,      ACT_CYCLING_RING_CLKW | COL_SPECTRUM,  175,           1,           100 },
  { 500,      ACT_CYCLING_RING_CLKW | COL_SPECTRUM,  200,           1,           200 },
  { 750,      ACT_CYCLING_RING_CLKW | COL_SPECTRUM,  225,           1,           250 },
  { 1000,     ACT_CYCLING_RING_CLKW | COL_SPECTRUM,  250,           1,           350 },
  { 30000,    ACT_SIMPLE_RING | COL_SPECTRUM,        50,            1,           10 },
  { 2500,     ACT_WHEEL_ACLK | COL_SPECTRUM,         10,            1,           10 },
  { 2500,     ACT_WHEEL_ACLK | COL_SPECTRUM,         15,            1,           20 },
  { 2000,     ACT_WHEEL_ACLK | COL_SPECTRUM,         25,            1,           30 },
  { 1000,     ACT_WHEEL_ACLK | COL_SPECTRUM,         50,            1,           40 },
  { 1000,     ACT_WHEEL_ACLK | COL_SPECTRUM,         75,            1,           40 },
  { 1000,     ACT_WHEEL_ACLK | COL_SPECTRUM,         100,           1,           50 },
  { 500,      ACT_WHEEL_ACLK | COL_SPECTRUM,         125,           1,           60 },
  { 500,      ACT_WHEEL_CLKW | COL_SPECTRUM,         125,           5,           50 },
  { 1000,     ACT_WHEEL_CLKW | COL_SPECTRUM,         100,           10,          40 },
  { 1500,     ACT_WHEEL_CLKW | COL_SPECTRUM,         75,            15,          30 },
  { 2000,     ACT_WHEEL_CLKW | COL_SPECTRUM,         50,            20,          20 },
  { 2500,     ACT_WHEEL_CLKW | COL_SPECTRUM,         25,            25,          10 },
  { 3000,     ACT_WHEEL_CLKW | COL_SPECTRUM,         10,            30,          5 },
  { 5000,     ACT_SPARKLING_RING | COL_RANDOM,       10,            25,          1000 },
  { 5000,     ACT_NOP,                               0,             0,           0 }
};

#endif
