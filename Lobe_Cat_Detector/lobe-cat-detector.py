import time
from enum import Enum, auto
import board
from digitalio import DigitalInOut, Direction, Pull
import picamera
import io
from PIL import Image
from lobe import ImageModel
import os
import adafruit_dotstar
from datetime import datetime
import pwmio
from adafruit_motor import servo

LABEL_CAT = "Cat"
LABEL_MULTI_CAT = "Multiple Cats"
LABEL_NOTHING = "No Cats"
SERVO_PIN = board.D12
WARNING_COUNT = 3

pwm = pwmio.PWMOut(SERVO_PIN, duty_cycle=0, frequency=50)
servo = servo.Servo(pwm, min_pulse=400, max_pulse=2400)

# Boiler Plate code for buttons and joystick on the braincraft
BUTTON_PIN = board.D17
JOYDOWN_PIN = board.D27
JOYLEFT_PIN = board.D22
JOYUP_PIN = board.D23
JOYRIGHT_PIN = board.D24
JOYSELECT_PIN = board.D16

buttons = [BUTTON_PIN, JOYUP_PIN, JOYDOWN_PIN,
           JOYLEFT_PIN, JOYRIGHT_PIN, JOYSELECT_PIN]

for i, pin in enumerate(buttons):
    buttons[i] = DigitalInOut(pin)
    buttons[i].direction = Direction.INPUT
    buttons[i].pull = Pull.UP
button, joyup, joydown, joyleft, joyright, joyselect = buttons


class Input(Enum):
    BUTTON = auto()
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    SELECT = auto()


def get_inputs():
    inputs = []
    if not button.value:
        inputs.append(Input.BUTTON)
    if not joyup.value:
        inputs.append(Input.UP)
    if not joydown.value:
        inputs.append(Input.DOWN)
    if not joyleft.value:
        inputs.append(Input.LEFT)
    if not joyright.value:
        inputs.append(Input.RIGHT)
    if not joyselect.value:
        inputs.append(Input.SELECT)
    return inputs

DOTSTAR_DATA = board.D5
DOTSTAR_CLOCK = board.D6

RED = (0, 0, 255)
GREEN = (255, 0, 0)
OFF = (0, 0, 0)

dots = adafruit_dotstar.DotStar(DOTSTAR_CLOCK, DOTSTAR_DATA, 3, brightness=0.1)

jingle_count = 0

def color_fill(color, wait):
    dots.fill(color)
    dots.show()
    time.sleep(wait)

def jingle_keys(jingle_hard=False):
    global jingle_count
    jingle_count += 1
    if jingle_count > WARNING_COUNT:
        jingle_hard = True
    delay = 0.5 if jingle_hard else 2
    loop = 5 if jingle_hard else 1
    travel = 180 if jingle_hard else 135
    for _ in range(0, loop):
        for angle in (0, travel):
            servo.angle = angle
            time.sleep(delay)
    servo.angle = None

def main():
    global jingle_count
    model = ImageModel.load('~/model')

    # Check if there is a folder to keep the retraining data, if it there isn't make it
    if (not os.path.exists('./retraining_data')):
        os.mkdir('./retraining_data')

    with picamera.PiCamera(resolution=(224, 224), framerate=30) as camera:
        stream = io.BytesIO()
        camera.start_preview()
        # Camera warm-up time
        time.sleep(2)
        label = ''
        while True:
            stream.seek(0)
            camera.annotate_text = None
            camera.capture(stream, format='jpeg')
            camera.annotate_text = label
            img = Image.open(stream)
            result = model.predict(img)
            label = result.prediction
            confidence = result.labels[0][1]
            camera.annotate_text = label
            print(f'\rLabel: {label} | Confidence: {confidence*100: .2f}%', end='', flush=True)

            # Check if the current label is package and that the label has changed since last tine the code ran
            if label == LABEL_CAT:
                # Make Servo Jingle Keys
                jingle_keys()
            elif label == LABEL_MULTI_CAT:
                jingle_keys(True)
            elif label == LABEL_NOTHING:
                jingle_count = 0

            time.sleep(0.5)

            inputs = get_inputs()
            # Check if the joystick is pushed up
            if (Input.UP in inputs):
                color_fill(GREEN, 0)
                # Check if there is a folder to keep the retraining data, if it there isn't make it
                if (not os.path.exists(f'./retraining_data/{label}')):
                    os.mkdir(f'./retraining_data/{label}')
                # Remove the text annotation
                camera.annotate_text = None

                # File name
                name = datetime.now()
                # Save the current frame
                camera.capture(
                    os.path.join(
                        f'./retraining_data/{label}', 
                        f'{datetime.now().strftime("%Y-%m-%d_%H:%M:%S")}.jpg'
                    )
                )
                
                color_fill(OFF, 0)

            # Check if the joystick is pushed down
            elif (Input.DOWN in inputs or Input.BUTTON in inputs):
                color_fill(RED, 0)
                # Remove the text annotation
                camera.annotate_text = None
                # Save the current frame to the top level retraining directory
                camera.capture(
                    os.path.join(
                        f'./retraining_data',
                        f'{datetime.now().strftime("%Y-%m-%d_%H:%M:%S")}.jpg'
                    )
                )
                color_fill(OFF, 0)


if __name__ == '__main__':
    try:
        print(f"Predictions starting, to stop press \"CTRL+C\"")
        main()
    except KeyboardInterrupt:
        print("")
        print(f"Caught interrupt, exiting...")
