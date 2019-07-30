import pygame, sys
from pygame.locals import *

class adabot():
  image = ''
  x = 0
  y = 0
  ll = 0 # left limit
  rl = 0 # right limit
  direction = 'right'

  def __init__(self, x, y, ll, rl):
    self.image = pygame.image.load('adabot.png')
    self.image = self.image.convert_alpha()
    self.x = x
    self.y = y
    self.ll = ll
    self.rl = rl

  def update(self):
    if (self.direction == 'right'):
      self.x += 5
    else:
      self.x -= 5

    if (self.x > self.rl or self.x < self.ll):
      self.direction = 'right' if self.direction == 'left' else 'left'
