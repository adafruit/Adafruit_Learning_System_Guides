import board
import time
import math
import random
from adafruit_pyportal import PyPortal
from digitalio import DigitalInOut, Direction, Pull

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi settings are kept in settings.py, please add them there!")
    raise


led = DigitalInOut(board.L)
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
PLAYER1 = 'PLAYER 1!'
PLAYER2 = 'PLAYER 2!'
#DEFINITION_EXAMPLE_ARR = [DEF_LOCATION, EXAMPLE_LOCATION]
#defintion and example array variable initialized at 0
definition_example = 0

# determine the current working directory
# needed so we know where to find files
cwd = ("/"+__file__).rsplit('/', 1)[0]

data_file = cwd+"data_file"

# Initialize the pyportal object and let us know what data to fetch and where
# to display it
pyportal = PyPortal(url=DATA_SOURCE,
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/wordoftheday_background.bmp",
                    text_font=cwd+"/fonts/Arial-ItalicMT-17.bdf",
                    text_position=((50, 70),  # question location
                                   (50, 130), # wrong answer location 1
                                   (50, 150), # wrong answer location 2
                                   (50, 170), # wrong answer location 3
                                   (50, 190)), # correct answer location
                    text_color=(0x8080FF,
                                0xFFFFFF,
                                0xFFFFFF,
                                0xFFFFFF,
                                0xFFFFFF),
                    text_wrap=(28, # characters to wrap for text
                               28,
                               28,
                               28,
                               28),
                    text_maxlen=(180, 30, 115, 120, 120), # max text size for word, part of speech and def
                    caption_text=CAPTION,
                    caption_font=cwd+"/fonts/Arial-ItalicMT-17.bdf",
                    caption_position=(50, 218),
                    caption_color=0x808080)

print("loading...") # print to repl while waiting for font to load
pyportal.preload_font() # speed things up by preloading font
pyportal.set_text("\nTrivia Time!\n(Tap to Begin!)") # show title



def shuffle(aList):
    for i in range(len(aList)-1, 0, -1):

        # Pick a random index from 0 to i
        j = random.randint(0, i + 1)

        # Swap arr[i] with the element at random index
        aList[i], aList[j] = aList[j], aList[i]

        return aList






while True:
    if pyportal.touchscreen.touch_point:
        try:

            answerList = [WA_LOCATION1, WA_LOCATION2, WA_LOCATION3, CA_LOCATION]

            shuffle(answerList)

            tupleAnswerList = tuple(answerList)

            print(tupleAnswerList)


            #set the JSON path here to be able to change between definition and example
            pyportal._json_path=(Q_LOCATION,
                                 tupleAnswerList[0],
                                 tupleAnswerList[1],
                                 tupleAnswerList[2],
                                 tupleAnswerList[3],)


            pyportal._text_color=(0x8080FF,
                                0xFFFFFF,
                                0xFFFFFF,
                                0xFFFFFF,
                                0xFFFFFF)
            value = pyportal.fetch()
            print("Response is", value)
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)
        except IndexError:
            print("Index Error")
            continue

        # 30 seconds to see question

        timerStart = time.monotonic()

        print(time.monotonic() - timerStart)

        while time.monotonic() - timerStart < 30:

            if button1.value:
                led.value = False
            else:
                led.value = True

                pyportal.set_text("PLAYER 1!")

                break

            if button2.value:
                led.value = False
            else:
                led.value = True

                pyportal.set_text("PLAYER 2!")

                break

            if time.monotonic() - timerStart > 29.5:

                pyportal.set_text("TIME'S UP!")

        print(time.monotonic() - timerStart)

        time.sleep(0.05)  # debounce delay

        # 10 seconds to answer

        timerStart = time.monotonic()

        print(time.monotonic() - timerStart)

        while time.monotonic() - timerStart < 10:

            if button1.value:
                led.value = False
            else:
                led.value = True

                pyportal.set_text("PLAYER 1!")

                break

            if button2.value:
                led.value = False
            else:
                led.value = True

                pyportal.set_text("PLAYER 2!")

                break

            if time.monotonic() - timerStart > 9.5:

                pyportal.set_text("TIME'S UP!")

        print(time.monotonic() - timerStart)

        time.sleep(0.05)  # debounce delay


        # Show the correct answer

        answerChoices = ("A","B","C","D")

        for i in range(len(tupleAnswerList)):
            if tupleAnswerList[i] is CA_LOCATION:
                print(answerChoices[i])
                correctAnswerChoice = answerChoices[i]
                break

        answerRevealText = "Correct Answer: " + str(correctAnswerChoice) + "\n(Tap for next question.)"

        pyportal.set_text(answerRevealText)


