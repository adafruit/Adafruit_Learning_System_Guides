#!/usr/bin/python
import os
import time
import math
import logging
import pygame, sys
from pygame.locals import *
import RPi.GPIO as GPIO
from twitter import *
from flowmeter import *
from adabot import *
from seekrits import *

t = Twitter( auth=OAuth(OAUTH_TOKEN, OAUTH_SECRET, CONSUMER_KEY, CONSUMER_SECRET) )
#boardRevision = GPIO.RPI_REVISION
GPIO.setmode(GPIO.BCM) # use real GPIO numbering
GPIO.setup(23,GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(24,GPIO.IN, pull_up_down=GPIO.PUD_UP)

# set up pygame
pygame.init()

# set up the window
VIEW_WIDTH = 1024
VIEW_HEIGHT = 576
pygame.display.set_caption('KEGBOT')
lastTweet = 0
view_mode = 'normal'

# hide the mouse
pygame.mouse.set_visible(False)

# set up the flow meters
fm = FlowMeter('metric', ["beer"])
fm2 = FlowMeter('metric', ["root beer"])
tweet = ''
# set up the colors
BLACK = (0,0,0)
WHITE = (255,255,255)

# set up the window surface
windowSurface = pygame.display.set_mode((VIEW_WIDTH,VIEW_HEIGHT), FULLSCREEN, 32) 
windowInfo = pygame.display.Info()
FONTSIZE = 48
LINEHEIGHT = 28
basicFont = pygame.font.SysFont(None, FONTSIZE)

# set up the backgrounds
bg = pygame.image.load('beer-bg.png')
tweet_bg = pygame.image.load('tweet-bg.png')

# set up the adabots
back_bot = adabot(361, 151, 361, 725)
middle_bot = adabot(310, 339, 310, 825)
front_bot = adabot(220, 527, 220, 888)

# draw some text into an area of a surface
# automatically wraps words
# returns any text that didn't get blitted
def drawText(surface, text, color, rect, font, aa=False, bkg=None):
    rect = Rect(rect)
    y = rect.top
    lineSpacing = -2
 
    # get the height of the font
    fontHeight = font.size("Tg")[1]
 
    while text:
        i = 1
 
        # determine if the row of text will be outside our area
        if y + fontHeight > rect.bottom:
            break
 
        # determine maximum width of line
        while font.size(text[:i])[0] < rect.width and i < len(text):
            i += 1
 
        # if we've wrapped the text, then adjust the wrap to the last word      
        if i < len(text): 
            i = text.rfind(" ", 0, i) + 1
 
        # render the line and blit it to the surface
        if bkg:
            image = font.render(text[:i], 1, color, bkg)
            image.set_colorkey(bkg)
        else:
            image = font.render(text[:i], aa, color)
 
        surface.blit(image, (rect.left, y))
        y += fontHeight + lineSpacing
 
        # remove the text we just blitted
        text = text[i:]
 
    return text

def renderThings(flowMeter, flowMeter2, tweet, windowSurface, basicFont):
  # Clear the screen
  windowSurface.blit(bg,(0,0))
  
  # draw the adabots
  back_bot.update()
  windowSurface.blit(back_bot.image,(back_bot.x, back_bot.y))
  middle_bot.update()
  windowSurface.blit(middle_bot.image,(middle_bot.x, middle_bot.y))
  front_bot.update()
  windowSurface.blit(front_bot.image,(front_bot.x, front_bot.y))

  # Draw Ammt Poured
  text = basicFont.render("CURRENT", True, WHITE, BLACK)
  textRect = text.get_rect()
  windowSurface.blit(text, (40,20))
  if fm.enabled:
    text = basicFont.render(fm.getFormattedThisPour(), True, WHITE, BLACK)
    textRect = text.get_rect()
    windowSurface.blit(text, (40,30+LINEHEIGHT))
  if fm2.enabled:
    text = basicFont.render(fm2.getFormattedThisPour(), True, WHITE, BLACK)
    textRect = text.get_rect()
    windowSurface.blit(text, (40, 30+(2*(LINEHEIGHT+5))))

  # Draw Ammt Poured Total
  text = basicFont.render("TOTAL", True, WHITE, BLACK)
  textRect = text.get_rect()
  windowSurface.blit(text, (windowInfo.current_w - textRect.width - 40, 20))
  if fm.enabled:
    text = basicFont.render(fm.getFormattedTotalPour(), True, WHITE, BLACK)
    textRect = text.get_rect()
    windowSurface.blit(text, (windowInfo.current_w - textRect.width - 40, 30 + LINEHEIGHT))
  if fm2.enabled:
    text = basicFont.render(fm2.getFormattedTotalPour(), True, WHITE, BLACK)
    textRect = text.get_rect()
    windowSurface.blit(text, (windowInfo.current_w - textRect.width - 40, 30 + (2 * (LINEHEIGHT+5))))
  
  if view_mode == 'tweet':
    windowSurface.blit(tweet_bg,(0,0))
    textRect = Rect(545,265,500,225)
    drawText(windowSurface, tweet, BLACK, textRect, basicFont, True, None)

  # Display everything
  pygame.display.flip()

# Beer, on Pin 23.
def doAClick(channel):
  currentTime = int(time.time() * FlowMeter.MS_IN_A_SECOND)
  if fm.enabled == True:
    fm.update(currentTime)

# Root Beer, on Pin 24.
def doAClick2(channel):
  currentTime = int(time.time() * FlowMeter.MS_IN_A_SECOND)
  if fm2.enabled == True:
    fm2.update(currentTime)

def tweetPour(theTweet):
  try:
    t.statuses.update(status=theTweet)
  except:
    logging.warning('Error tweeting: ' + theTweet + "\n")

GPIO.add_event_detect(23, GPIO.RISING, callback=doAClick, bouncetime=20) # Beer, on Pin 23
GPIO.add_event_detect(24, GPIO.RISING, callback=doAClick2, bouncetime=20) # Root Beer, on Pin 24

# main loop
while True:
  # Handle keyboard events
  for event in pygame.event.get():
    if event.type == QUIT or (event.type == KEYUP and event.key == K_ESCAPE):
      GPIO.cleanup()
      pygame.quit()
      sys.exit()
    elif event.type == KEYUP and event.key == K_1:
      fm.enabled = not(fm.enabled)
    elif event.type == KEYUP and event.key == K_2:
      fm2.enabled = not(fm2.enabled)
    elif event.type == KEYUP and event.key == K_9:
      fm.clear()
    elif event.type == KEYUP and event.key == K_0:
      fm2.clear()
  
  currentTime = int(time.time() * FlowMeter.MS_IN_A_SECOND)
 
  if currentTime - lastTweet < 5000: # Pause for 5 seconds after tweeting to show the tweet
    view_mode = 'tweet'
  else:
    view_mode = 'normal'

  if (fm.thisPour > 0.23 and currentTime - fm.lastClick > 10000): # 10 seconds of inactivity causes a tweet
    tweet = "Someone just poured " + fm.getFormattedThisPour() + " of " + fm.getBeverage() + " from the Adafruit kegomatic!" 
    lastTweet = int(time.time() * FlowMeter.MS_IN_A_SECOND)
    fm.thisPour = 0.0
    tweetPour(tweet)
 
  if (fm2.thisPour > 0.23 and currentTime - fm2.lastClick > 10000): # 10 seconds of inactivity causes a tweet
    tweet = "Someone just poured " + fm2.getFormattedThisPour() + " of " + fm2.getBeverage() + " from the Adafruit kegomatic!"
    lastTweet = int(time.time() * FlowMeter.MS_IN_A_SECOND)
    fm2.thisPour = 0.0
    tweetPour(tweet)
    
  # reset flow meter after each pour (2 secs of inactivity)
  if (fm.thisPour <= 0.23 and currentTime - fm.lastClick > 2000):
    fm.thisPour = 0.0
    
  if (fm2.thisPour <= 0.23 and currentTime - fm2.lastClick > 2000):
    fm2.thisPour = 0.0

  # Update the screen
  renderThings(fm, fm2, tweet, windowSurface, basicFont)
