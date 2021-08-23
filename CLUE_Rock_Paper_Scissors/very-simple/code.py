# clue-verysimple-rpsgame v1.0
# CircuitPython rock paper scissors game simple text game
# based on https://www.youtube.com/watch?v=dhaaZQyBP2g

# Tested with CLUE and Circuit Playground Bluefruit (Alpha)
# and CircuitPython and 5.3.0

# copy this file to CLUE/CPB board as code.py

# MIT License

# Copyright (c) 2015 Chris Bradfield, KidsCanCode LLC

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import random

moves = ["r", "p", "s"]
player_wins = ["pr", "sp", "rs"]

print("Rock, paper scissors game: enter first letter for move or q for quit")
while True:
    player_move = input("Your move: ")
    if player_move == "q":
        break

    computer_move = random.choice(moves)
    print("You:", player_move)
    print("Me:", computer_move)
    if player_move == computer_move:
        print("Tie")
    elif player_move + computer_move in player_wins:
        print("You win!")
    else:
        print("You lose!")
