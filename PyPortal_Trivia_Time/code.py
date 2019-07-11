"""
This example uses the Open Trivia Database API to display multiple choice trivia questions.
Tap the screen to start, then a question will appear and a 30 second timer will start.
The first player to hit their button will get 10 seconds to answer.
Hit button again to reveal answer. Tap screen to move to next question.
This program assumes two buttons are attached to D3 and D4 on the Adafruit PyPortal.
"""

import time
import random
import board
from adafruit_pyportal import PyPortal
from digitalio import DigitalInOut, Direction, Pull

# initialize harware
led = DigitalInOut(board.L) # For debugging
led.direction = Direction.OUTPUT
button1 = DigitalInOut(board.D4)
button2 = DigitalInOut(board.D3)
button1.direction = Direction.INPUT
button2.direction = Direction.INPUT
button1.pull = Pull.UP
button2.pull = Pull.UP

# Set up where we'll be fetching data from
DATA_SOURCE = "https://opentdb.com/api.php?amount=1&type=multiple"
Q_LOCATION = ['results', 0, 'question']
WA_LOCATION1 = ['results', 0, 'incorrect_answers', 0]
WA_LOCATION2 = ['results', 0, 'incorrect_answers', 1]
WA_LOCATION3 = ['results', 0, 'incorrect_answers', 2]
CA_LOCATION = ['results', 0, 'correct_answer']
CAPTION = 'opentdb.com'
answerChoices = ("A","B","C","D")

# determine the current working directory
# needed so we know where to find files
cwd = ("/"+__file__).rsplit('/', 1)[0]

# A function to shuffle trivia questions
def shuffle(aList):
    for i in range(len(aList)-1, 0, -1):
        # Pick a random index from 0 to i
        j = random.randint(0, i + 1)
        # Swap arr[i] with the element at random index
        aList[i], aList[j] = aList[j], aList[i]
        return aList

# A function to handle the timer and determine which player answers first
def faceOff(timerLength):
    timerStart = time.monotonic()
    print(time.monotonic() - timerStart)
    while time.monotonic() - timerStart < timerLength:
        if button1.value:
            led.value = False # For debugging
        else: # If button 1 pressed, print player 1 on screen and exit function
            pyportal.set_text("PLAYER 1!")
            led.value = True # For debugging
            break
        if button2.value:
            led.value = False # For debugging
        else: # If button 2 pressed, print player 1 on screen and exit function
            pyportal.set_text("PLAYER 2!")
            led.value = True # For debugging
            break
        if time.monotonic() - timerStart > (timerLength - 0.5): # Timer runs out
            pyportal.set_text("TIME'S UP!")
    print(time.monotonic() - timerStart)
    time.sleep(0.05)  # debounce delay

#convert html codes to normal text
def unescape(s):
    s = s.replace("&quot;", "''")
    s = s.replace("&#039;", "'")
    s = s.replace("&amp;", "&")
    return s

# Initialize the pyportal object and let us know what data to fetch and where
# to display it
pyportal = PyPortal(url=DATA_SOURCE,
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/trivia_title.bmp",
                    text_font=cwd+"/fonts/Arial-ItalicMT-17.bdf",
                    text_position=((25, 70),  # question location
                                   (40, 135), # answer location 1
                                   (40, 155), # answer location 2
                                   (40, 175), # answer location 3
                                   (40, 195)), # answer location 4
                    text_color=(0x8080FF,
                                0xFFFFFF,
                                0xFFFFFF,
                                0xFFFFFF,
                                0xFFFFFF),
                    text_wrap=(35, # characters to wrap for text
                               30,
                               30,
                               30,
                               30),
                    text_maxlen=(140, 27, 27, 27, 27), # max text size
                    caption_font=cwd+"/fonts/Arial-ItalicMT-17.bdf")
print("loading...") # print to repl while waiting for font to load
pyportal.preload_font() # speed things up by preloading font

while True:
    # Load new question when screen is touched
    if pyportal.touchscreen.touch_point:
        pyportal.set_background(cwd+"/trivia.bmp")
        pyportal.set_text("Loading question...")
        pyportal.set_caption(CAPTION,(200, 218), 0x808080)
        answerList = [WA_LOCATION1, WA_LOCATION2, WA_LOCATION3, CA_LOCATION]
        # For catching potential index error when shuffling question
        try:
            shuffle(answerList)
        except IndexError:
            print("Index Error")
            pyportal.set_text("Tap again for next question.")
            continue
        try:
            # set the JSON path here
            # pylint: disable=protected-access
            pyportal._json_path=(unescape(Q_LOCATION),
                                 unescape(answerList[0]),
                                 unescape(answerList[1]),
                                 unescape(answerList[2]),
                                 unescape(answerList[3]),)
            value = pyportal.fetch()
            print("Response is", value)
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)
        # 30 seconds with question
        faceOff(30)
        time.sleep(2) # pause for 2 seconds to show which player tapped first
        # 10 seconds to answer
        faceOff(10)
        # Show the correct answer
        for k in range(len(answerList)):
            if answerList[k] is CA_LOCATION:
                print(answerChoices[k])
                correctAnswerChoice = answerChoices[k]
                break
        answerRevealText="Correct Answer: "+str(correctAnswerChoice)+"\n(Tap for next question.)"
        pyportal.set_text(answerRevealText)
