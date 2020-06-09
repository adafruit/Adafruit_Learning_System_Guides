import time
from adafruit_button import Button
from adafruit_pyportal import PyPortal

pyportal = PyPortal(default_bg="/stock-pyportal.bmp")

lowE = "/sounds/lowE.wav"
A = "/sounds/A.wav"
D = "/sounds/D.wav"
G = "/sounds/G.wav"
B = "/sounds/B.wav"
highE = "/sounds/highE.wav"

notes = [lowE, A, D, G, B, highE]

pegs = [
    {'label': "lowE", 'pos': (53, 0), 'size': (65, 90)},
    {'label': "A", 'pos': (124, 0), 'size': (65, 90)},
    {'label': "D", 'pos': (194, 0), 'size': (65, 90)},
    {'label': "G", 'pos': (194, 150), 'size': (65, 90)},
    {'label': "B", 'pos': (124, 150), 'size': (65, 90)},
    {'label': "highE", 'pos': (53, 150), 'size': (65, 90)}
    ]

buttons = []
for peg in pegs:
    button = Button(x=peg['pos'][0], y=peg['pos'][1],
                    width=peg['size'][0], height=peg['size'][1],
                    style=Button.RECT,
                    fill_color=None, outline_color=0x5C3C15,
                    name=peg['label'])
    pyportal.splash.append(button.group)
    buttons.append(button)

note_select = None

while True:
    touch = pyportal.touchscreen.touch_point
    if not touch and note_select:
        note_select = False
    if touch:
        for i in range(6):
            tuning = notes[i]
            button = buttons[i]
            if button.contains(touch) and not note_select:
                print("Touched", button.name)
                note_select = True
                for z in range(3):
                    pyportal.play_file(tuning)
    time.sleep(0.1)
