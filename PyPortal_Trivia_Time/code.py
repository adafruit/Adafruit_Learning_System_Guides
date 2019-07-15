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
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
import adafruit_imageload
import displayio

# initialize harware
led = DigitalInOut(board.L) # For debugging
led.direction = Direction.OUTPUT
button1 = DigitalInOut(board.D4)
button2 = DigitalInOut(board.D3)
button1.direction = Direction.INPUT
button2.direction = Direction.INPUT
button1.pull = Pull.UP
button2.pull = Pull.UP
display = board.DISPLAY

# Set up where we'll be fetching data from
DATA_SOURCE = "https://opentdb.com/api.php?amount=1&type=multiple"
Q_LOCATION = ['results', 0, 'question']
WA_LOCATION1 = ['results', 0, 'incorrect_answers', 0]
WA_LOCATION2 = ['results', 0, 'incorrect_answers', 1]
WA_LOCATION3 = ['results', 0, 'incorrect_answers', 2]
CA_LOCATION = ['results', 0, 'correct_answer']
CAPTION = 'opentdb.com'
answerChoices = ("A","B","C","D")
qf_text = ''
a1f_text = ''
a2f_text = ''
a3f_text = ''
a4f_text = ''
trivia_font = bitmap_font.load_font("/fonts/Arial-ItalicMT-17.bdf")
# 320 x 240
loading_position = tapagain_position = (100,120)
player_position = timesup_position = answerReveal_position = (120, 75)
answerReveal_position = (25, 75)
q_position = (25, 70)
a1_position = (25, 135)
a2_position = (25, 155)
a3_position = (25, 175)
a4_position = (25, 195)
loading_color = 0x8080FF
q_color = 0x8080FF
a_color = 0xFFFFFF
player1_text = "Player 1!"
player2_text = "Player 2!"
timesup_text = "TIME'S UP!"
loading_text = "loading question..."
tapagain_text = "Tap again for \n next question."





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
            # pyportal.set_text("PLAYER 1!")
            pyportal.splash.pop() # Pop 5 - quesiton - to make room for player that wins
            player1_text_area = label.Label(trivia_font, text=player1_text, color=loading_color)
            player1_text_area.x = player_position[0]
            player1_text_area.y = player_position[1]
            pyportal.splash.append(player1_text_area) # push 5
            led.value = True # For debugging
            break
        if button2.value:
            led.value = False # For debugging
        else: # If button 2 pressed, print player 1 on screen and exit function
            # pyportal.set_text("PLAYER 2!")
            led.value = True # For debugging
            pyportal.splash.pop() # Pop 5 - quesiton - to make room for player that wins
            player2_text_area = label.Label(trivia_font, text=player2_text, color=loading_color)
            player2_text_area.x = player_position[0]
            player2_text_area.y = player_position[1]
            pyportal.splash.append(player2_text_area) # push 5
            break
        if time.monotonic() - timerStart > (timerLength - 0.5): # Timer runs out
            # pyportal.set_text("TIME'S UP!")
            pyportal.splash.pop() # Pop 5 - quesiton - to make room for player that wins
            timesup_text_area = label.Label(trivia_font, text=timesup_text, color=loading_color)
            timesup_text_area.x = timesup_position[0]
            timesup_text_area.y = timesup_position[1]
            pyportal.splash.append(timesup_text_area) # push 5
    print(time.monotonic() - timerStart)
    time.sleep(0.05)  # debounce delay

#convert html codes to normal text
def unescape(s):
    s = s.replace("&quot;", "''")
    s = s.replace("&#039;", "'")
    s = s.replace("&amp;", "&")
    return s

def unescapeList(l):
    for i in range(len(l)):
        l[i] = l[i].replace("&quot;", "\"")
        l[i] = l[i].replace("&#039;", "\'")
        l[i] = l[i].replace("&amp;", "&")
    return l

# Clear screen of all elements but background
def clear_splash():
    for _ in range(len(pyportal.splash) - 1):
        pyportal.splash.pop()

pyportal = PyPortal(url=DATA_SOURCE,
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/trivia_title.bmp")
                    # caption_font=cwd+"/fonts/Arial-ItalicMT-17.bdf") # no caption?


print("loading...") # print to repl while waiting for font to load
pyportal.preload_font() # speed things up by preloading font



while True:
    # Load new question when screen is touched
    if pyportal.touchscreen.touch_point:
        clear_splash() # clear all besides background screen
        pyportal.set_background(cwd+"/trivia.bmp")
        #pyportal.set_text("Loading question...")
        loading_text_area = label.Label(trivia_font, text=loading_text, color=loading_color)
        loading_text_area.x = loading_position[0]
        loading_text_area.y = loading_position[1]
        pyportal.splash.append(loading_text_area) # push 1

        # pyportal.set_caption(CAPTION,(200, 218), 0x808080) # set caption location and color
        answerList = [WA_LOCATION1, WA_LOCATION2, WA_LOCATION3, CA_LOCATION]
        # For catching potential index error when shuffling question
        try:
            shuffle(answerList) # Shuffle answers
        except IndexError:
            print("Index Error")
            #pyportal.set_text("Tap again for next question.")
            pyportal.splash.pop() # take off loading... pop 1
            tapagain_text_area = label.Label(trivia_font, text=tapagain_text, color=loading_color)
            tapagain_text_area.x = tapagain_position[0]
            tapagain_text_area.y = tapagain_position[1]
            pyportal.splash.append(tapagain_text_area) # push 1
            continue
        try:
            # set the JSON path here, now that answers are shuffled
            # pylint: disable=protected-access
            pyportal._json_path=(Q_LOCATION,
                                 answerList[0],
                                 answerList[1],
                                 answerList[2],
                                 answerList[3],)
            value = pyportal.fetch()
            print("Response is", value)

            #pyportal.set_text("Loading question...")
            pyportal.splash.pop() # take off loading... pop 1
            loading_text_area = label.Label(trivia_font, text=loading_text, color=loading_color)
            loading_text_area.x = loading_position[0]
            loading_text_area.y = loading_position[1]
            pyportal.splash.append(loading_text_area) # push 1

            # "clean" results
            valueClean = unescapeList(value)
            print("Response is", valueClean)

            # Formatting with displayio
            q_text = unescape(value[0])
            q_text_formatted = pyportal.wrap_nicely(q_text, 35)
            qf_text = ''
            for i in range (len(q_text_formatted)):
                qf_text = qf_text + q_text_formatted[i] +"\n"
            q_text = qf_text
            q_text_area = label.Label(trivia_font, text=q_text, color=q_color, line_spacing = 1)
            q_text_area.x = q_position[0]
            q_text_area.y = q_position[1]
            a1_text = unescape(value[1])
            a1_text_area = label.Label(trivia_font, text="A. "+a1_text, color=a_color, line_spacing = 1.5)
            a1_text_area.x = a1_position[0]
            a1_text_area.y = a1_position[1]
            a2_text = unescape(value[2])
            a2_text_area = label.Label(trivia_font, text="B. "+a2_text, color=a_color, line_spacing = 1.5)
            a2_text_area.x = a2_position[0]
            a2_text_area.y = a2_position[1]
            a3_text = unescape(value[3])
            a3_text_area = label.Label(trivia_font, text="C. "+a3_text, color=a_color, line_spacing = 1.5)
            a3_text_area.x = a3_position[0]
            a3_text_area.y = a3_position[1]
            a4_text = unescape(value[4])
            a4_text_area = label.Label(trivia_font, text="D. "+a4_text, color=a_color, line_spacing = 1.5)
            a4_text_area.x = a4_position[0]
            a4_text_area.y = a4_position[1]

            pyportal.splash.pop() # take off loading... pop 1
            pyportal.splash.append(a1_text_area) # push 1
            pyportal.splash.append(a2_text_area) # push 2
            pyportal.splash.append(a3_text_area) # push 3
            pyportal.splash.append(a4_text_area) # push 4
            pyportal.splash.append(q_text_area) # push 5 push question last so it can be removed more easily later

            #display.show(q_text_area)

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
        answerReveal_text="Correct Answer: "+str(correctAnswerChoice)+"\n(Tap for next question.)"
        pyportal.splash.pop() # Pop 5
        answerReveal_text_area = label.Label(trivia_font, text=answerReveal_text, color=loading_color)
        answerReveal_text_area.x = answerReveal_position[0]
        answerReveal_text_area.y = answerReveal_position[1]
        pyportal.splash.append(answerReveal_text_area) # push 5

        #pyportal.set_text(answerRevealText)
