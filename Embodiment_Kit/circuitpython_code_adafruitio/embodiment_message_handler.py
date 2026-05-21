import array
import os
import time
import math

import terminalio
from displayio import Group, Palette
from vectorio import Rectangle

from adafruit_anchored_tilegrid import AnchoredTileGrid
import adafruit_imageload
from adafruit_display_text.text_box import TextBox

FACE_COMMAND_MAP = {
    "show_happy_face": {
        "eyebrows": ("eyebrow_happy.png", -40),
        "eyes": ("long_eyes_extremely_happy.png", -10),
        "blush": ("blush_star.png", 20),
        "mouth": ("mouth_smiling.png", 36),
    },
    "show_sad_face": {
        "eyebrows": ("eyebrow_sad.png", -40),
        "eyes": ("round_eyes_sad.png", -10),
        "blush": ("blush_round.png", 20),
        "mouth": ("mouth_sad.png", 46),
    },
    "show_angry_face": {
        "eyebrows": ("eyebrow_angry.png", -40),
        "eyes": ("square_eyes_angry.png", -10),
        "blush": ("blush_angry.png", 20),
        "mouth": ("mouth_small_straight.png", 46),
    },
    "show_confused_face": {
        "eyebrows": ("eyebrow_confused.png", -40),
        "eyes": ("shape_dizzy.png", -10),
        "mouth": ("mouth_confused.png", 40),
    },
    "show_sleepy_face": {
        "eyebrows": ("eyebrow_tired.png", -40),
        "eyes": ("squinty_eyes_closed.png", -20),
        "blush": ("blush_sleepy.png", 20),
        "mouth": ("mouth_small_smiling.png", 36),
    },
}


def mean(values):
    return sum(values) / len(values)


def normalized_rms(values):
    minbuf = int(mean(values))
    samples_sum = sum(float(sample - minbuf) * (sample - minbuf) for sample in values)

    return math.sqrt(samples_sum / len(values))


class EmbodimentMessageHandler:
    def __init__(self, config):
        self.display = config["display"]
        self.main_group = Group()
        self.face_group = Group()

        self.main_group.append(self.face_group)
        self.face_bg_palette = Palette(1)
        self.face_bg_rect = Rectangle(
            pixel_shader=self.face_bg_palette,
            width=self.display.width,
            height=self.display.height,
            x=0,
            y=0,
        )
        self.face_group.append(self.face_bg_rect)

        self.sensors = config["sensors"]

        self.message_lbl = TextBox(
            terminalio.FONT,
            self.display.width // 2,
            self.display.height // 2,
            TextBox.ALIGN_LEFT,
        )
        self.message_lbl.line_spacing = 1.0
        self.message_lbl.scale = 2
        self.message_lbl.anchor_point = (0.0, 0.0)
        self.message_lbl.anchored_position = (0, 0)
        self.message_lbl.hidden = True
        self.main_group.append(self.message_lbl)
        self._samples = array.array("H", [0] * 160)
        self.buzzer = config["piezo_buzzer"]
        self.vibration_driver = config["vibration_driver"]
        self.rgb_strip = config["neopixels"]
        self.buttons = config["buttons"]
        print("self.buttons", self.buttons)
        self._display_state = "None"

        for sensor_config in self.sensors:
            if sensor_config["type"] == "pdm_mic":
                self.mic = sensor_config["sensor"]
            elif sensor_config["type"] == "accelerometer":
                self.accelerometer = sensor_config["sensor"]
            elif sensor_config["type"] == "lux":
                self.lux_sensor = sensor_config["sensor"]

    def _display_face(self, face_options, background_color):
        while len(self.face_group) > 1:
            _ = self.face_group.pop()

        self.message_lbl.hidden = True
        self.face_group.hidden = False

        if "eyebrows" in face_options:
            eyebrow_image, eyebrow_palette = adafruit_imageload.load(
                f"embodiment_kit/eyebrows/{face_options['eyebrows'][0]}"
            )
            eyebrow_tg = AnchoredTileGrid(
                bitmap=eyebrow_image, pixel_shader=eyebrow_palette
            )
            eyebrow_tg.anchor_point = (0.5, 0.5)
            eyebrow_tg.anchored_position = (
                self.display.width // 2,
                self.display.height // 2 + face_options["eyebrows"][1],
            )
            eyebrow_palette.make_transparent(0)
            self.face_group.append(eyebrow_tg)

        if "eyes" in face_options:
            eyes_image, eyes_palette = adafruit_imageload.load(
                f"embodiment_kit/eyes/{face_options['eyes'][0]}"
            )
            eyes_tg = AnchoredTileGrid(bitmap=eyes_image, pixel_shader=eyes_palette)
            eyes_tg.anchor_point = (0.5, 0.5)
            eyes_tg.anchored_position = (
                self.display.width // 2,
                self.display.height // 2 + face_options["eyes"][1],
            )
            eyes_palette.make_transparent(0)
            self.face_group.append(eyes_tg)

        if "blush" in face_options:
            blush_image, blush_palette = adafruit_imageload.load(
                f"embodiment_kit/blush/{face_options['blush'][0]}"
            )
            blush_tg = AnchoredTileGrid(bitmap=blush_image, pixel_shader=blush_palette)
            blush_tg.anchor_point = (0.5, 0.5)
            blush_tg.anchored_position = (
                self.display.width // 2,
                self.display.height // 2 + face_options["blush"][1],
            )
            blush_palette.make_transparent(0)
            self.face_group.append(blush_tg)

        if "mouth" in face_options:
            mouth_image, mouth_palette = adafruit_imageload.load(
                f"embodiment_kit/mouths/{face_options['mouth'][0]}"
            )
            mouth_tg = AnchoredTileGrid(bitmap=mouth_image, pixel_shader=mouth_palette)
            mouth_tg.anchor_point = (0.5, 0.5)
            mouth_tg.anchored_position = (
                self.display.width // 2,
                self.display.height // 2 + face_options["mouth"][1],
            )
            mouth_palette.make_transparent(0)
            self.face_group.append(mouth_tg)

        self.face_bg_palette[0] = background_color

    def _message_is_command(self, message_obj):
        return (
            "metadata" in message_obj
            and "type" in message_obj["metadata"]
            and message_obj["metadata"]["type"] == "command"
            and "command" in message_obj
        )

    def handle_message(self, message_obj):
        if self._message_is_command(message_obj):
            return self._do_command(message_obj["command"])
        return None

    def handle_messages(self, message_list):
        resp_data = {"messages": []}
        for message in message_list:
            resp_data["messages"].append(self.handle_message(message))
        return resp_data

    def _do_command(self, command_obj):
        # pylint: disable=too-many-locals, too-many-return-statements, too-many-statements
        command = command_obj["name"]
        print(f"doing command: {command_obj}")
        arguments = {}
        if "arguments" in command_obj:
            arguments = command_obj["arguments"]
            print("ARGS", arguments)

        if command in FACE_COMMAND_MAP:
            _bg_color = arguments.get("background_color", 0x88DDFF)
            self._display_state = f"face: {command.replace('show_', '')}"
            self._display_face(FACE_COMMAND_MAP[command], _bg_color)
            return self._create_ack(command_obj)

        elif command == "show_custom_face":
            _face_options = arguments.get(
                "options", FACE_COMMAND_MAP["show_happy_face"]
            )
            _bg_color = arguments.get("background_color", 0x88DDFF)
            self._display_state = "face: custom_face"
            self._display_face(_face_options, _bg_color)
            return self._create_ack(command_obj)

        elif command == "get_data":
            return self._create_ack(command_obj)

        elif command == "list_custom_face_options":
            command_obj["response"] = {
                "eyes_options": os.listdir("embodiment_kit/eyes"),
                "blush_options": os.listdir("embodiment_kit/blush"),
                "mouth_options": os.listdir("embodiment_kit/mouths"),
                "eyebrow_option": os.listdir("embodiment_kit/eyebrows"),
            }
            return self._create_ack(command_obj)

        elif command == "play_tone":
            _frequency = arguments.get("frequency", 440)
            _duty_cycle = arguments.get("duty_cycle", 2**15)
            _duration = arguments.get("duration", 0.5)
            _proof = self._play_tone(_frequency, _duty_cycle, _duration)
            return self._create_ack(command_obj, _proof)

        elif command == "lights_on":
            _proof = {"idle_lux_level": self.lux_sensor.autolux}
            _color = arguments.get("color", 0xFF00FF)
            _brightness = arguments.get("brightness", self.rgb_strip.brightness)
            self.rgb_strip.brightness = _brightness
            self.rgb_strip.fill(_color)
            _proof["on_lux_level"] = self.lux_sensor.autolux
            return self._create_ack(command_obj, _proof)

        elif command == "lights_off":
            _proof = {"idle_lux_level": self.lux_sensor.autolux}
            self.rgb_strip.fill(0x000000)
            _proof["off_lux_level"] = self.lux_sensor.autolux
            return self._create_ack(command_obj, _proof)

        elif command == "vibrate":
            _x, _y, _z = self._average_acceleration(self.accelerometer, 100)
            _proof = {
                "idle_z_acceleration": _z,
            }
            self.vibration_driver.play()
            time.sleep(0.25)
            _x, _y, _z = self._average_acceleration(self.accelerometer, 100)
            _proof["vibrating_z_acceleration"] = _z
            time.sleep(0.5)
            self.vibration_driver.stop()
            return self._create_ack(command_obj, _proof)

        elif command == "show_message":
            _text = arguments.get("message", "")
            self._show_message(_text)
            return self._create_ack(command_obj)

        elif command == "show_prompt":
            _text = arguments.get("message", "Press a button")
            _timeout = arguments.get("timeout", 20)
            return self._show_prompt(command_obj, _text, _timeout)

        else:
            print(f"Unknown command: {command}")
            return None

    def _show_prompt(self, command_obj, prompt_text, timeout):
        self._show_message(prompt_text)

        _start_time = time.monotonic()
        _now = _start_time
        while _now < _start_time + timeout:
            for _btn_lbl in self.buttons.keys():
                _btn = self.buttons[_btn_lbl]
                _btn.update()
                if (_btn_lbl == "D0" and _btn.fell) or (
                    _btn_lbl in {"D1", "D2"} and _btn.rose
                ):
                    command_obj["response"] = {
                        "prompt_result": f"btn {_btn_lbl} pressed"
                    }
                    self._show_message("Thank you")
                    return self._create_ack(command_obj)

            _now = time.monotonic()

        command_obj["response"] = {"prompt_result": "timed out"}
        self._show_message("Prompt timed out")
        return self._create_ack(command_obj)

    def _show_message(self, message_text):
        self.message_lbl.text = message_text
        self.message_lbl.hidden = False
        self.face_group.hidden = True
        self._display_state = f"message: {message_text}"

    def _play_tone(self, frequency, duty_cycle, duration):
        _proof = {"idle_sound_level": self._get_sound_level()}
        time.sleep(0.05)
        self.buzzer.frequency = frequency
        self.buzzer.duty_cycle = duty_cycle
        time.sleep(duration / 2)
        _proof["playing_sound_level"] = self._get_sound_level()
        time.sleep(duration / 2)
        self.buzzer.duty_cycle = 0
        return _proof

    def _create_ack(self, command_obj, proof=None):
        _ack_obj = {
            "metadata": {"type": "ack"},
            "command": command_obj,
            "state": {
                "sensors": self._get_sensor_readings(),
                "outputs": self._get_output_state(),
            },
        }
        if proof is not None:
            _ack_obj["metadata"]["proof"] = proof
        return _ack_obj

    def _get_output_state(self):
        return {
            "neopixels": {
                "color": self.rgb_strip[0],
                "brightness": self.rgb_strip.brightness,
            },
            "display": self._display_state,
        }

    def _get_sensor_readings(self):
        _data = {}
        for _sensor_config in self.sensors:
            _type = _sensor_config["type"]
            _sensor = _sensor_config["sensor"]

            if _type in {"temperature", "pressure", "lux", "humidity"}:
                if "property" not in _sensor_config:
                    _data[_type] = getattr(_sensor, _type)
                else:
                    _data[_type] = getattr(_sensor, _sensor_config["property"])
            elif _type == "accelerometer":
                _x, _y, _z = self._average_acceleration(self.accelerometer, 10)
                _data[_type] = f"x={_x}, y={_y}, z={_z}"
            elif _type == "pdm_mic":
                _sensor.record(self._samples, len(self._samples))
                magnitude = normalized_rms(self._samples)
                _data[_type] = magnitude

            if "units" in _sensor_config:
                _data[_type] = str(_data[_type]) + " " + _sensor_config["units"]

        return _data

    def _get_sound_level(self):
        self.mic.record(self._samples, len(self._samples))
        return normalized_rms(self._samples)

    def _average_acceleration(self, sensor, n):
        """Take N readings from the accelerometer and return the average x, y, z values."""
        sum_x = sum_y = sum_z = 0
        for _ in range(n):
            x, y, z = sensor.acceleration
            sum_x += x
            sum_y += y
            sum_z += z
        return sum_x / n, sum_y / n, sum_z / n
