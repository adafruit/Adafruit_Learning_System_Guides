from . import funcTest

def GameLogic(theBoard, event, onColor, offColor):
    #
    # get the 1d event button mapping for grid
    row, col = funcTest.arrayMap(event,4)
    #
    # algorithm corresponding 8 neighbor cell calc
    neighbors = funcTest.neighbors(theBoard, row,col)
    #
    #  unpack the column and row values calc from neighbors y,x orientation to match how board is drawn.
    for y, x in neighbors:
        # first check if the neighbor in the list is off on the game board
        if theBoard[y][x] == offColor:
            # if its not turned on turn y=the light on
            theBoard[y][x] = onColor
        # elif the neighbor cell is not eqaul to the off color thens its turned on
        elif theBoard[y][x] != offColor:
            # so we turn it off it the prevouis isnt true
            theBoard[y][x] = offColor
    # turn off the pressed key
    theBoard[row][col] = offColor
    # return the new board
    return theBoard

def NewGameLogic(theBoard:list, event:tuple, onColor:tuple, offColor:tuple):
    numOff = 0
    numOn = 0
    # get the 1d event button mapping for grid
    row, col = funcTest.arrayMap(event,4)
    # algorithm corresponding 8 neighbor cell calc
    neighbors = funcTest.neighbors(theBoard, row,col)
    #  unpack the column and row values calc from neighbors y,x orientation to match how board is drawn.
    for x ,y in neighbors:
        # first check if the neighbor in the list is off on the game board
        if theBoard[x][y] == offColor:
            # if its not turned on turn y=the light on
            numOff +=1
        # elif the neighbor cell is not eqaul to the off color thens its turned on
        elif theBoard[x][y] != offColor:
            # so we turn it off it the prevouis isnt true
            numOn += 1
    # turn off the pressed key using modified Conway's rule
    # cant use the above loop as the comparison to
    # on&off would change each iteration. 
    for x ,y in neighbors:
        if numOn < 3:
            theBoard[x][y] = onColor
        elif numOff < 5:
            theBoard[x][y] = offColor
    return theBoard

def checkWin(theBoard, offcolor):
    # board is NxN so get the len of first row to size the loop range
    boardRange = len(theBoard[0])
    for x in range(boardRange):
        for y in range(boardRange):
            # check logical board against win condition, in this case if the board is empty
            if theBoard[x][y] == offcolor:
                return False
    else:
        return True