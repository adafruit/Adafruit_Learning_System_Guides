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

# determine the current working directory
# needed so we know where to find files
cwd = ("/"+__file__).rsplit('/', 1)[0]

# Set up where we'll be fetching data from
DATA_SOURCE = "https://opentdb.com/api.php?amount=1&type=multiple"
Q_LOCATION = ['results', 0, 'question']
WA_LOCATION1 = ['results', 0, 'incorrect_answers', 0]
WA_LOCATION2 = ['results', 0, 'incorrect_answers', 1]
WA_LOCATION3 = ['results', 0, 'incorrect_answers', 2]
CA_LOCATION = ['results', 0, 'correct_answer']

# Text info
trivia_font = bitmap_font.load_font("/fonts/Arial-ItalicMT-17.bdf")

loading_color = 0x8080FF
loading_position = (100,120)
loading_text_area = label.Label(trivia_font, max_glyphs=30, color=loading_color,
                                x=loading_position[0], y=loading_position[1])

q_color = 0x8080FF
q_position = (25, 70)
q_text_area = label.Label(trivia_font, max_glyphs=120,
                          x=q_position[0], y=q_position[1],
                          color=q_color, line_spacing = 1)

answer_choices = ("A","B","C","D")
a_positions = ((25, 135), (25, 155), (25, 175), (25, 195))
a_color = 0xFFFFFF
ans_text_areas = []
for answernum in range(4):
    ans_text_areas.append(label.Label(trivia_font, max_glyphs=80,
                                      color=a_color, line_spacing = 1.5,
                                      x=a_positions[answernum][0],
                                      y=a_positions[answernum][1]))

reveal_position = (25, 75)
reveal_text_area = label.Label(trivia_font, max_glyphs=120, color=loading_color,
                               x=reveal_position[0], y=reveal_position[1])

timer_position = (25, 215)
timer_color = 0xFF00FF
timer_text_area = label.Label(trivia_font, max_glyphs=20, color=timer_color,
                              x=timer_position[0], y=timer_position[1])

# A function to shuffle trivia questions
def shuffle(aList):
    for i in range(len(aList)):
        j = random.randint(0, len(aList)-1)
        # Swap arr[i] with the element at random index
        aList[i], aList[j] = aList[j], aList[i]
    return aList

# convert html codes to normal text
def unescape(s):
    s = s.replace("&quot;", "''")
    s = s.replace("&#039;", "'")
    s = s.replace("&amp;", "&")
    return s

# A function to handle the timer and determine which player answers first
def faceOff(timerLength):
    timer_text = str(timerLength) + " seconds!"
    timer_text_area.text = ''
    timer_text_area.text = str(timer_text)
    timerStart = time.monotonic()
    while time.monotonic() - timerStart < timerLength:
        if button1.value:
            led.value = False # For debugging
        else: # If button 1 pressed, print player 1 on screen and exit function
            led.value = True # For debugging
            q_text_area.text = ''
            reveal_text_area.text = "Player 1!"
            break
        if button2.value:
            led.value = False # For debugging
        else: # If button 2 pressed, print player 2 on screen and exit function
            led.value = True # For debugging
            q_text_area.text = ''
            reveal_text_area.text = "Player 2!"
            break
        time.sleep(0.05)  # debounce delay
    else: # Timer runs out
        q_text_area.text = ''
        reveal_text_area.text = "Times up!"

# PyPortal constructor
pyportal = PyPortal(url=DATA_SOURCE,
                    json_path=(Q_LOCATION, CA_LOCATION, WA_LOCATION1, WA_LOCATION2, WA_LOCATION3),
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/trivia_title.bmp")

pyportal.preload_font() # speed things up by preloading font

pyportal.splash.append(loading_text_area) #loading...
pyportal.splash.append(q_text_area)
pyportal.splash.append(reveal_text_area)
pyportal.splash.append(timer_text_area)
for textarea in ans_text_areas:
    pyportal.splash.append(textarea)

while True:
    # Load new question when screen is touched
    while not pyportal.touchscreen.touch_point:
        pass

    reveal_text_area.text = ''
    q_text_area.text = ''
    for textarea in ans_text_areas:
        textarea.text = ''
    timer_text_area.text = ''

    pyportal.set_background(cwd+"/trivia.bmp")
    loading_text_area.text ="Loading question..."

    while True:
        try:
            value = pyportal.fetch()
            break
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)
            continue
    print("Response is", value)
    question = value[0]
    correct_answer = value[1]
    answers = shuffle(value[1:5])
    loading_text_area.text = ''

    # Format text and wrap with display text library
    try: # sometimes gives a runtime error: Group full
        q_text_area.text = '\n'.join(pyportal.wrap_nicely(unescape(question), 35))
    except RuntimeError as e:
        print("Group full", e)
        continue
    for k, answer in enumerate(answers):
        ans_text_areas[k].text = answer_choices[k]+") "+unescape(answer)

    faceOff(10) # 10 seconds with question
    time.sleep(2) # pause for 2 seconds to show which player tapped first
    faceOff(5) # 5 seconds to answer
    timer_text_area.text = ''
    # Show the correct answer
    k = answers.index(correct_answer)
    reveal_text = ("Correct Answer:\n"+answer_choices[k]+") "
                   +unescape(answers[k])+"\n(Tap for next question.)")
    print(reveal_text)
    reveal_text_area.text = reveal_text
