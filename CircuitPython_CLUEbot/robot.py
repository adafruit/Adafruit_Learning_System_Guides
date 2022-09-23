import time
import pwmio
import board
import digitalio
import displayio
import vectorio
import terminalio

import neopixel
import adafruit_motor.servo
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService
from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.color_packet import ColorPacket
from adafruit_bluefruit_connect.button_packet import ButtonPacket
from adafruit_display_text.label import Label

# Throttle Directions and Speeds
FWD = 1.0
REV = -1.0
STOP = 0

# Custom Colors
RED = (200, 0, 0)
GREEN = (0, 200, 0)
BLUE = (0, 0, 200)
PURPLE = (120, 0, 160)
YELLOW = (100, 100, 0)
AQUA = (0, 100, 100)

class Robot:
    def __init__(self, left_pin, right_pin, underlight_neopixel):
        self.left_motor = self._init_motor(left_pin)
        self.right_motor = self._init_motor(right_pin)
        self._init_display()
        self._init_ble()
        self.under_pixels = underlight_neopixel
        self.neopixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
        self.direction = STOP
        self.release_color = None
        self.headlights = digitalio.DigitalInOut(board.WHITE_LEDS)
        self.headlights.switch_to_output()
        self.set_underglow(PURPLE)
        self.set_speed(STOP)

    @classmethod
    def _init_motor(cls, pin):
        pwm = pwmio.PWMOut(pin, frequency=50)
        return adafruit_motor.servo.ContinuousServo(pwm, min_pulse=600, max_pulse=2400)

    @classmethod
    def _make_palette(cls, color):
        palette = displayio.Palette(1)
        palette[0] = color
        return palette

    def _init_ble(self):
        self.ble = BLERadio()
        self.uart_service = UARTService()
        self.advertisement = ProvideServicesAdvertisement(self.uart_service)

    def _init_display(self):
        self.display = board.DISPLAY
        self.display_group = displayio.Group()
        self.display.show(self.display_group)
        self.shape_color = 0
        self.bg_color = 0xFFFF00
        rect = vectorio.Rectangle(
            pixel_shader=self._make_palette(0xFFFF00),
            x=0, y=0,
            width=self.display.width,
            height=self.display.height)
        self.display_group.append(rect)

    def wait_for_connection(self):
        self.set_status_led(BLUE)
        self.ble.start_advertising(self.advertisement)
        self._set_status_waiting()
        while not self.ble.connected:
            # Wait for a connection.
            pass
        self.ble.stop_advertising()
        self.set_status_led(GREEN)
        self.set_throttle(STOP)

    def is_connected(self):
        return self.ble.connected

    def set_underglow(self, color, save_release_color = False):
        if save_release_color:
            self.release_color = self.get_underglow()
        for index, _ in enumerate(self.under_pixels):
            self.under_pixels[index] = color

    def get_underglow(self):
        # Set the 2 Neopixels on the underside fo the robot
        return self.under_pixels[0]

    def set_status_led(self, color):
        # Set the status NeoPixel on the CLUE
        self.neopixel[0] = color

    def toggle_headlights(self):
        self.headlights.value = not self.headlights.value

    def _set_left_throttle(self, speed):
        self.left_motor.throttle = speed

    def _set_right_throttle(self, speed):
        # Motor is rotated 180 degrees of the left, so we invert the throttle
        self.right_motor.throttle = -1 * speed

    def rotate_right(self):
        self.release_color = self.get_underglow()
        self.set_underglow(YELLOW, True)
        if self.direction == STOP:
            self._set_status_rotate_cw()
        else:
            self._set_status_right()
        speed = FWD if self.direction == STOP else self.direction
        self._set_left_throttle(speed)
        self._set_right_throttle(STOP if self.direction != STOP else -1 * speed)

    def rotate_left(self):
        self.release_color = self.get_underglow()
        self.set_underglow(YELLOW, True)
        if self.direction == STOP:
            self._set_status_rotate_ccw()
        else:
            self._set_status_left()
        speed = FWD if self.direction == STOP else self.direction
        self._set_left_throttle(STOP if self.direction != STOP else -1 * speed)
        self._set_right_throttle(speed)

    def set_throttle(self, speed):
        if speed == STOP:
            self._set_status_stop()
        elif speed > STOP:
            self._set_status_forward()
        elif speed < STOP:
            self._set_status_reverse()
        self.set_speed(speed)

    def set_speed(self, speed):
        self._set_left_throttle(speed)
        self._set_right_throttle(speed)
        self.direction = speed

    def stop(self):
        # Temporarily grab the current color
        color = self.get_underglow()
        self.set_underglow(RED)
        self.set_throttle(STOP)
        time.sleep(0.5)
        self.set_underglow(color)

    def check_for_packets(self):
        if self.uart_service.in_waiting:
            self._process_packet(Packet.from_stream(self.uart_service))

    def _handle_color_packet(self, packet):
        # Change the color
        self.set_underglow(packet.color)

    def _remove_shapes(self):
        while len(self.display_group) > 1:
            self.display_group.pop()

    def _add_centered_rect(self, width, height, x_offset=0, y_offset=0, color=None):
        if color is None:
            color = self.shape_color
        rectangle = vectorio.Rectangle(
            pixel_shader=self._make_palette(color),
            width=width,
            height=height,
            x=(self.display.width//2 - width//2) + x_offset - 1,
            y=(self.display.height//2 - height//2) + y_offset - 1
        )
        self.display_group.append(rectangle)

    def _add_centered_polygon(self, points, x_offset=0, y_offset=0, color=None):
        if color is None:
            color = self.shape_color
        # Figure out the shape dimensions by using min and max
        width = max(points, key=lambda item:item[0])[0] - min(points, key=lambda item:item[0])[0]
        height = max(points, key=lambda item:item[1])[1] - min(points, key=lambda item:item[1])[1]
        polygon = vectorio.Polygon(
            pixel_shader=self._make_palette(color),
            points=points,
            x=(self.display.width // 2 - width // 2) + x_offset - 1,
            y=(self.display.height // 2 - height // 2) + y_offset - 1
        )
        self.display_group.append(polygon)

    def _add_centered_circle(self, radius, x_offset=0, y_offset=0, color=None):
        if color is None:
            color = self.shape_color
        circle = vectorio.Circle(
            pixel_shader=self._make_palette(color),
            radius=radius,
            x=(self.display.width // 2) + x_offset - 1,
            y=(self.display.height // 2) + y_offset - 1
        )
        self.display_group.append(circle)

    def _set_status_waiting(self):
        self._remove_shapes()
        text_area = Label(
            terminalio.FONT,
            text="Waiting for\nconnection",
            color=self.shape_color,
            scale=3,
            anchor_point=(0.5, 0.5),
            anchored_position=(self.display.width // 2, self.display.height // 2)
        )
        self.display_group.append(text_area)

    def _set_status_reverse(self):
        self._remove_shapes()
        self._add_centered_polygon([(40, 0), (60, 0), (100, 100), (0, 100)], 0, 0)
        self._add_centered_polygon([(0, 40), (100, 40), (50, 0)], 0, -40)

    def _set_status_forward(self):
        self._remove_shapes()
        self._add_centered_polygon([(20, 0), (60, 0), (80, 100), (0, 100)])
        self._add_centered_polygon([(0, 0), (150, 0), (75, 50)], 0, 50)

    def _set_status_right(self):
        self._remove_shapes()
        self._add_centered_rect(100, 40)
        self._add_centered_polygon([(50, 0), (50, 100), (0, 50)], -50, 0)

    def _set_status_rotate_ccw(self):
        self._remove_shapes()
        self._add_centered_circle(80)
        self._add_centered_circle(50, 0, 0, self.bg_color)
        self._add_centered_rect(160, 60, 0, 0, self.bg_color)
        self._add_centered_polygon([(40, 0), (80, 40), (0, 40)], 60, 10)
        self._add_centered_polygon([(40, 40), (80, 0), (0, 0)], -60, -10)

    def _set_status_left(self):
        self._remove_shapes()
        self._add_centered_rect(100, 40)
        self._add_centered_polygon([(0, 0), (0, 100), (50, 50)], 50)

    def _set_status_rotate_cw(self):
        self._remove_shapes()
        self._add_centered_circle(80)
        self._add_centered_circle(50, 0, 0, self.bg_color)
        self._add_centered_rect(160, 60, 0, 0, self.bg_color)
        self._add_centered_polygon([(40, 0), (80, 40), (0, 40)], -60, 10)
        self._add_centered_polygon([(40, 40), (80, 0), (0, 0)], 60, -10)

    def _set_status_stop(self):
        self._remove_shapes()
        self._add_centered_rect(100, 100)

    def _handle_button_press_packet(self, packet):
        if packet.button == ButtonPacket.UP:  # UP button pressed
            self.set_throttle(FWD)
        elif packet.button == ButtonPacket.DOWN:  # DOWN button
            self.set_throttle(REV)
        elif packet.button == ButtonPacket.RIGHT:
            self.rotate_right()
        elif packet.button == ButtonPacket.LEFT:
            self.rotate_left()
        elif packet.button == ButtonPacket.BUTTON_1:
            self.stop()
        elif packet.button == ButtonPacket.BUTTON_2:
            self.set_underglow(GREEN)
        elif packet.button == ButtonPacket.BUTTON_3:
            self.set_underglow(BLUE)
        elif packet.button == ButtonPacket.BUTTON_4:
            self.toggle_headlights()

    def _handle_button_release_packet(self, packet):
        if self.release_color is not None:
            self.set_underglow(self.release_color)
            self.release_color = None
        if packet.button == ButtonPacket.RIGHT:
            self.set_throttle(self.direction)
        if packet.button == ButtonPacket.LEFT:
            self.set_throttle(self.direction)

    def _process_packet(self, packet):
        if isinstance(packet, ColorPacket):
            self._handle_color_packet(packet)
        elif isinstance(packet, ButtonPacket) and packet.pressed:
            # do this when buttons are pressed
            self._handle_button_press_packet(packet)
        elif isinstance(packet, ButtonPacket) and not packet.pressed:
            # do this when some buttons are released
            self._handle_button_release_packet(packet)
