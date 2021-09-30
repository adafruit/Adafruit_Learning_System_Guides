# SPDX-FileCopyrightText: 2017 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: GNU
#
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
 * this is the general implementation of the gemma hoop animator - unless you 
 * don't like the preset animations or find a major bug, you don't need to 
 * change anything here
 *
 * ----------------------------------------------------------------------------
 *
 * this sketch simply cycles through the action list defined in
 * GemmaHoopActiuonList.h. it should run on any arduino compatible µC
 * and with all available NeoPixel products - you just have to adjust
 * the general settings in GemmaHoopActionList.h.
 *
 * it hereby loads the individually defined actions one after the other
 * and continously steps through these actions according to the action
 * speed specified for the respective action.
 *
 * independently from stepping through the current action, it also changes 
 * the current color according to the color change interval and the 
 * respective color selection method (random or spectrum)
 * definied for the current action. 
 *
 * each action will continue according to the current action duration 
 * as defined in the action list. then the next action will be loaded. when
 * the last action in the list is reached, it will continue with the first 
 * action.
 *
 * ----------------------------------------------------------------------------
 *
 * the number of actions possible is limited by the RAM of the used µC. shall
 * the list be too long, the µC will crash and nothing will go on.
 *
 * i'd rather like to put the action definitions on a SD card or any external
 * storage to get more space for as well more different action implementations
 * as an unlimited number of actions per animation including more control
 * parameters as for example:
 *
 * - brightnes control per action
 * - speed wipes per action, which would reduce the number
 *   of actions to be defined for seamless speed changes
 *
 * as i designed this for the gemma hoops as suggested on adafruit's web page
 * there seems to be no suitable way of connecting an external storage device
 * 
 ******************************************************************************/

#include <Adafruit_NeoPixel.h>

/******************************************************************************
 *
 * where the action list is to be declared and all animation actions 
 * are to be defined:
 *
 ******************************************************************************/

#include "GemmaHoopActionList.h"
 
/******************************************************************************
 *
 * general global variables
 *
 ******************************************************************************/

uint32_t color = 0, 
         color_timer = 0, 
         action_timer = 0, 
         action_step_timer = 0;
uint16_t color_idx = 0, 
         curr_color_interval = 0, 
         curr_action_step_duration = 0, 
         curr_action_duration = 0;
uint8_t  spectrum_part = 0, 
         curr_action = 0, 
         curr_color_gen = COL_RANDOM, 
         idx = 0, 
         offset = 0, 
         number_of_actions = 0, 
         curr_action_idx = 0, 
         curr_color_granularity = 1;

/******************************************************************************
 *
 * general global variables
 *
 ******************************************************************************/

Adafruit_NeoPixel pixels = Adafruit_NeoPixel(NUM_PIXELS, PIXEL_OUTPUT);

/******************************************************************************
 *
 * initializing - note that the action list is declared and initialized
 * in GemmaHoopActionList.h!
 *
 ******************************************************************************/

void setup() 
{
  // fingers corssed, the seeding makes sense to really get random colors...
  randomSeed(analogRead(ANALOG_INPUT));  
  
  // we need to know, how many actions are defined - shall the there be too
  // many actions defined, the RAM will overflow and he µC won't do anything
  // --> rather easy diagnosis ;-)
  number_of_actions = sizeof (theActionList) / sizeof (actiondesc);
  
  // let's go!
  pixels.begin();
  pixels.setBrightness(BRIGHTNESS);
  nextColor();
  pixels.show();
}

/******************************************************************************
 *
 * where all the magic happens - note that the action list is declared and 
 * initialized in GemmaHoopActionList.h!
 *
 ******************************************************************************/

void loop() 
{
  // do we need to load the next action?
  if ((millis() - action_timer) > curr_action_duration)
  {
    curr_action_duration = theActionList[curr_action_idx].action_duration;
    curr_action = theActionList[curr_action_idx].action_and_color_gen & 0b00111111;
    curr_action_step_duration = theActionList[curr_action_idx].action_step_duration;
    curr_color_gen = theActionList[curr_action_idx].action_and_color_gen & 0b11000000;
    curr_color_granularity = theActionList[curr_action_idx].color_granularity;
    curr_color_interval = theActionList[curr_action_idx].color_interval;
    
    curr_action_idx++;
    // take care to rotate the action list!
    curr_action_idx %= number_of_actions; 

    action_timer = millis();
  }
  
  // do we need to change to the next color?
  if ((millis() - color_timer) > curr_color_interval)
  {
    nextColor();
    color_timer = millis();
  }
  
  // do we need to step up the current action?
  if ((millis() - action_step_timer) > curr_action_step_duration)
  {
    switch (curr_action)
    {
      case ACT_NOP :
      {
        // rather trivial even tho this will be repeated as long as the
        // NOP continues - i could have prevented it from repeating
        // unnecessarily, but that would mean more code and less
        // space for more actions within the animation
        for (int i = 0; i < NUM_PIXELS; i++) pixels.setPixelColor(i,0);
        break;
      }
      case ACT_SIMPLE_RING :
      {
        // even more trivial - just set the new color, if there is one
        for (int i = 0; i < NUM_PIXELS; i++) pixels.setPixelColor(i,color);
        break;
      }
      case ACT_CYCLING_RING_ACLK :
      case ACT_CYCLING_RING_CLKW :
      {
        // spin the ring clockwise or anti clockwise
        (curr_action == ACT_CYCLING_RING_ACLK) ? idx++ : idx--;
        // prevent overflows or underflows
        idx %= NUM_PIXELS;
        // set the new color, if there is one
        pixels.setPixelColor(idx,color);
        break;
      }
      case ACT_WHEEL_ACLK :
      case ACT_WHEEL_CLKW :
      {
        // switch on / off the appropriate pixels according to
        // the current offset
        for(idx=0; idx < NUM_PIXELS; idx++) 
        {
          pixels.setPixelColor(idx, ((offset + idx) & 7) < 2 ? color : 0);
        }
        // advance the offset and thus, spin the wheel
        // clockwise or anti clockwise
        (curr_action == ACT_WHEEL_CLKW) ? offset++ : offset--;
        // prevent overflows or underflows
        offset %= NUM_PIXELS;
        break;
      }
      case ACT_SPARKLING_RING :
      {
        // switch current pixel off
        pixels.setPixelColor(idx,0);
        // pick a new pixel
        idx = random (NUM_PIXELS);
        // set new pixel to the current color
        pixels.setPixelColor(idx,color);
        break;
      }
/*    for the sake of free RAM we disobey the rules
      of consistent coding and leave the following
      
      default :
      {
      }
*/      
    }
    pixels.show();
    action_step_timer = millis();
  }    
}

void nextColor ()
{
/*
 * detailed color generation method selection is obsolete
 * as long as there are just two methods
 
  switch (curr_color_gen)
  {
    case COL_RANDOM :
    {
      nextRandomColor();
      break;
    }
    case COL_SPECTRUM :
    {
      nextSpectrumColor();
      break;
    }
    default :
    {
    }
  }

 */
 
 // save some RAM for more animation actions
 (curr_color_gen & COL_RANDOM) ? nextRandomColor() : nextSpectrumColor();
}

void nextSpectrumColor ()
{
  switch (spectrum_part)
  {
    case 0 :  // spectral wipe from red to blue
    {
      color = Adafruit_NeoPixel::Color(255-color_idx,color_idx,0);
      color_idx += curr_color_granularity;
      if (color_idx > 255) 
      {
          spectrum_part = 1;
          color_idx = 0;
      }
      break;
    }
    case 1 :  // spectral wipe from blue to green
    {
      color = Adafruit_NeoPixel::Color(0,255-color_idx,color_idx);
      color_idx += curr_color_granularity;
      if (color_idx > 255) 
      {
          spectrum_part = 2;
          color_idx = 0;
      }
      break;
    }
    case 2 :  // spectral wipe from green to red
    {
      color = Adafruit_NeoPixel::Color(color_idx,0,255-color_idx);
      color_idx += curr_color_granularity;
      if (color_idx > 255) 
      {
          spectrum_part = 0;
          color_idx = 0;
      }
      break;
    }
/*  for the sake of free RAM we disobey the rules
    of consistent coding and leave the following
    
    default :
    {
    }
*/      
  }
}

void nextRandomColor ()
{
  color = Adafruit_NeoPixel::Color(random(256/curr_color_granularity) * curr_color_granularity,
                                   // granularity = 1 --> [0 .. 255] * 1 --> 0,1,2,3 ... 255
                                   random(256/curr_color_granularity) * curr_color_granularity,
                                   // granularity = 10 --> [0 .. 25] * 10 --> 0,10,20,30 ... 250
                                   random(256/curr_color_granularity) * curr_color_granularity);
                                   // granularity = 100 --> [0 .. 2] * 100 --> 0,100, 200 (boaring...)
}

