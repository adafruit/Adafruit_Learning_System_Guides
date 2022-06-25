#!/usr/bin/env python3
import boardFunc.gameLogic as gm
import boardFunc.funcTest as Func
from time import monotonic
from random import randrange


class boardState():
    # include the lower level abstraction modules we made and imported
    # define static tuples for colors
    # this class is a logical representation of the board,
    # it takes the initial gamestate as an arg
    def __init__(self, gridSize):
        self.onColor = (200, 18, 20)
        self.offColor = (0, 0, 0)
        self.winColor = (0, 25, 0)
        self.simColor = (10, 93, 30)
        self.N = gridSize//4  # changed from sqrt because,
        # importing math adds to the the total size of the the script
        # and the the size of the stack.
        # the init method takes one argument, the grid size
        self.theBoard = [[self.offColor]*self.N for _ in range(self.N)]
        self.timePressed = monotonic()
        self.eventButt = None
        self.previousButtonPressed = 0
        self.mode = None
        self.condition = None

    def debounce(self):
        # filters button inputs, input will only be
        # accepted every 0.2 seconds as measured from last press
        if monotonic() - self.timePressed > 0.2:
            return True
        else:
            return False

# hard to know what to do here.
    def animation(self):
        # this function runs the game in a way where each button press is random
        # and the color is as well, and it uses the real game anb board logic to produce an animation.
        self.onColor = (randrange(0, 254), randrange(
            27, 254), randrange(0, 254))
        simPress = randrange(0, 16)
        if simPress == self.previousButtonPressed:
            if simPress >= 15:
                simPress -= 1
            else:
                simPress += 1
        self.boardLogic(simPress)
    # TODO: move to module

    def choseMode(self):
        self.theBoard[0][0] = self.onColor
        self.theBoard[0][1] = self.simColor
        self.theBoard[0][2] = (123, 30, 170)
        if self.eventButt == 0:
            self.mode = 'run'
            self.clearBoard()
        elif self.eventButt == 1:
            self.mode = 'sim'
            self.clearBoard()
        elif self.eventButt == 2:
            self.mode = 'draw'
            self.clearBoard()

    # random pattern game init
    def randomStart(self):
        for i in range(0, 15):
            self.previousButtonPressed = randrange(i, 16)
            self.theBoard = gm.GameLogic(
                self.theBoard, self.previousButtonPressed, self.onColor, self.offColor)
    # TODO: move to module.

    def clearBoard(self):
        self.previousButtonPressed = None
        self.theBoard = [[self.offColor]*self.N for _ in range(self.N)]
        self.randomStart()

    def boardLogic(self, event):
        # print(self.mode)
        # the sim mode flag needs to use an interget value while button presses are key events
        # so if we chose sim mode, leave the event as 
        # a int value if not use the event.number data type.
        if self.mode != 'sim':
            self.eventButt = event.number
            if self.mode == None:
                # self.eventButt = event.number
                self.choseMode()
        else:
            self.eventButt = event
        # takes theboard and "event" or pressed button as an argument and updates the board state
        if self.debounce():
            # check if the player is pressing the same button they did last turn
            if not self.eventButt == self.previousButtonPressed:
                print(self.eventButt)
                # if not then do the main game logic
                self.previousButtonPressed = self.eventButt
                # run the game
                self.theBoard = gm.GameLogic(
                    self.theBoard, self.eventButt, self.onColor, self.offColor)
                if self.mode == 'run':
                    # if the mode flag isnt set to draw check the win condition
                    self.condition = gm.checkWin(self.theBoard)
                    if self.condition:
                        self.theBoard = [[self.winColor] *
                                         self.N for _ in range(self.N)]
            else:
                print('debounce failed')
            # update the last pressed time for debouncing purposes
            self.timePressed = monotonic()

    def getColor(self, i):
        y, x = Func.arrayMap(i, self.N)
        return self.theBoard[y][x]
