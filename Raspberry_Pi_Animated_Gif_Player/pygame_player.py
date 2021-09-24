"""
This example is for use on (Linux) computers that are using CPython with
Adafruit Blinka to support CircuitPython libraries. CircuitPython does
not support PIL/pillow (python imaging library)!

Author(s): Melissa LeBlanc-Williams for Adafruit Industries
"""
import serial
import adafruit_board_toolkit.circuitpython_serial
from animatedgif import AnimatedGif
import pygame

port = None


def detect_port():
    """
    Detect the port automatically
    """
    comports = adafruit_board_toolkit.circuitpython_serial.data_comports()
    ports = [comport.device for comport in comports]
    if len(ports) >= 1:
        if len(ports) > 1:
            print("Multiple devices detected, using the first detected port.")
        return ports[0]
    raise RuntimeError(
        "Unable to find any CircuitPython Devices with the CDC data port enabled."
    )


port = serial.Serial(
    detect_port(),
    9600,
    parity="N",
    rtscts=False,
    xonxoff=False,
    exclusive=True,
)


class PyGameAnimatedGif(AnimatedGif):
    def __init__(self, display, include_delays=True, folder=None):
        self._width, self._height = pygame.display.get_surface().get_size()
        self._incoming_packet = b""
        super().__init__(display, include_delays=include_delays, folder=folder)

    def get_next_value(self):
        if not port:
            return None
        while port.in_waiting:
            self._incoming_packet += port.read(port.in_waiting)
        while (
            self._running
            and not len(self._incoming_packet)
            and self._incoming_packet.decode().find(",")
        ):
            self._incoming_packet += port.read(port.in_waiting)
            self.check_pygame_events()

        all_values = self._incoming_packet.decode().split(",")
        value = all_values.pop(0)
        self._incoming_packet = ",".join(all_values).encode("utf-8")
        return value

    def check_pygame_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._running = False

    def update_display(self, image):
        pilImage = image
        self.display.blit(
            pygame.image.fromstring(pilImage.tobytes(), pilImage.size, pilImage.mode),
            (0, 0),
        )
        pygame.display.flip()


pygame.init()
pygame.mouse.set_visible(False)
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
gif_player = PyGameAnimatedGif(screen, include_delays=False, folder="images")
pygame.mouse.set_visible(True)
port.close()
