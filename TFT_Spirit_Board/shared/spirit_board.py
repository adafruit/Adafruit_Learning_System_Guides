import math
import os
import random
import time

import displayio
from anchored_tilegrid import AnchoredTileGrid

class SpiritBoard(displayio.Group):
    """
    DisplayIO Based SpiritBoard

    Holds and manages everything needed to draw the spirit board and planchette, as well
    as move the planchette around to output messages from the spirits.
    """

    # Mapping of letters and words on the board to their pixel coordinates.
    # Points are centered on the target letter.
    # Words can contain a list of points, the planchette will move between them.
    LOCATIONS = {"a": (42, 145), "b": (63, 115), "c": (97, 97), "d": (133, 85),
                 "e": (172, 78), "f": (207, 75), "g": (245, 74), "h": (284, 75),
                 "i": (319, 80), "j": (345, 85), "k": (375, 95), "l": (410, 111),
                 "m": (435, 140), "n": (78, 190), "o": (96, 162), "p": (122, 145),
                 "q": (149, 132), "r": (179, 123), "s": (208, 118), "t": (235, 116),
                 "u": (267, 116), "v": (302, 119), "w": (334, 130), "x": (368, 147),
                 "y": (393, 168), "z": (405, 194),
                 " ": (151, 201), "<3": (247, 20), "?": (162, 18), "&": (339, 18),
                 "home": (234, 246), "yes": [(26, 20), (82, 20)], "no": [(418, 20), (450, 20)],
                 "hello": [(20, 300), (123, 300)], "goodbye": [(314, 300), (456, 300)]}

    # List of full words on the board (multi-character strings)
    # used to know whether to parse the message
    # one letter at a time, or with a full word.
    FULL_WORDS = ["yes", "no", "hello", "goodbye", "home", "<3"]

    def __init__(self, display):
        """
        Create a SpiritBoard instance and put it in the displays root_group to make it visible.

        :param displayio.Display display:  Display object to show the spirit board on.
        """
        self._display = display
        super().__init__()

        # board image file
        self.spirit_board_odb = displayio.OnDiskBitmap("spirit_board_480x320.bmp")
        self.spirit_board_tilegrid = displayio.TileGrid(bitmap=self.spirit_board_odb, pixel_shader=self.spirit_board_odb.pixel_shader)
        self.append(self.spirit_board_tilegrid)

        # planchette image file
        self.planchette_odb = displayio.OnDiskBitmap("planchette_v1.bmp")
        self.planchette_odb.pixel_shader.make_transparent(0)
        self.planchette_tilegrid = AnchoredTileGrid(bitmap=self.planchette_odb, pixel_shader=self.planchette_odb.pixel_shader)

        # AnchoredTileGrid is used so that we can move the planchette
        # relative to the cetner of the window.
        self.planchette_tilegrid.anchor_point = (0.5, 0.5)

        # move the planchette to it's home to start
        self.planchette_tilegrid.anchored_position = SpiritBoard.LOCATIONS['home']

        # append the planchette to the self Group instance
        self.append(self.planchette_tilegrid)

        # set the self Group instance to root_group, so it's shown on the display.
        display.root_group = self

    @staticmethod
    def dist(pointA, pointB):
        """
        Calculate the distance between two points.

        :param tuple pointA: x,y pair of the first point
        :param pointB: x,y pair of the second point
        :return: the distance between the two points
        """
        return math.sqrt((pointB[0] - pointA[0]) ** 2 + (pointB[1] - pointA[1]) ** 2)

    def slide_planchette(self, target_location, delay=0.1, step_size=4):
        """
        Slide the planchette to the target location.

        delay and step_size parameters can be used to control the speed of the sliding.

        If the planchette is already at the target_location it will jump up slightly and
        then return to the target location. This helps to clarify messages that contain
        consecutive matching letters.

        :param tuple target_location: x,y pair of the target location
        :param float delay: length of time to sleep inbetween each movement step
        :param int step_size: how big of a step to take with each movement.
        :return: None
        """
        # disable auto_refresh during sliding, we refresh manually for each step
        self._display.auto_refresh = False

        # current location
        current_location = self.planchette_tilegrid.anchored_position

        # get the distance between the two
        distance = SpiritBoard.dist(current_location, target_location)

        # if the planchette is already at the target location
        if distance == 0:
            # cannot slide to the location we're already at.
            # slide up a tiny bit and then back to where we were.
            self.slide_planchette((current_location[0], current_location[1] - 20), delay, step_size)

            # update the current location to where we moved to
            current_location = self.planchette_tilegrid.anchored_position

            distance = SpiritBoard.dist(current_location, target_location)

        # variables used to calculate where the next point
        # between where we are at and where we are going is.
        distance_ratio = step_size / distance
        one_minus_distance_ratio = (1 - distance_ratio)

        # calculate the next point
        next_point = (
            round(one_minus_distance_ratio * current_location[0] + distance_ratio * target_location[0]),
            round(one_minus_distance_ratio * current_location[1] + distance_ratio * target_location[1])
        )
        # print(current_location)
        # print(next_point)

        # update the anchored_position of the planchette to move it to
        # the next point.
        self.planchette_tilegrid.anchored_position = next_point

        # refresh the display
        self._display.refresh()

        # wait for delay amount of time (seconds)
        time.sleep(delay)

        # while we haven't made it to the target location
        while 0 < distance_ratio < 1:
            # update current location variable
            current_location = self.planchette_tilegrid.anchored_position

            # calculate distance between new current location and target location
            distance = SpiritBoard.dist(current_location, target_location)

            # if we have arrived at the target location
            if distance == 0:
                # break out of the function
                break

            # distance ratio variables used to calculate next point
            distance_ratio = step_size / distance
            one_minus_distance_ratio = (1 - distance_ratio)

            # calculate the next point
            next_point = (
                round(one_minus_distance_ratio * current_location[0] + distance_ratio * target_location[0]),
                round(one_minus_distance_ratio * current_location[1] + distance_ratio * target_location[1])
            )

            # if we have not arrived at the target location yet
            if 0 < distance_ratio < 1:

                # update the anchored position to move the planchette to the
                # next point
                self.planchette_tilegrid.anchored_position = next_point

                # refresh the display
                self._display.refresh()

                # wait for delay amount of time (seconds)
                time.sleep(delay)

        # update the anchored position to move the planchette to the
        # target_location. This is needed in-case we undershot
        # the target location due to a step size that does not
        # divide into the total distance evenly.
        self.planchette_tilegrid.anchored_position = target_location

        # refresh the display
        self._display.refresh()

        # re-enable auto_refresh in case any other parts of the program
        # want to update the display
        self._display.auto_refresh = True

    def write_message(self, message, skip_spaces=True, step_size=6):
        """

        :param string message: The message to output with the planchette
        :param skip_spaces: Whether to skip space characters
        :param step_size: How big of a step to take with each movement
        :return: None
        """
        # ignore empty messages
        if message == "":
            return

        # split the message on space to get a list of words
        message_words = message.split(" ")

        # loop over the words in the message
        for index, word in enumerate(message_words):
            print(f"index: {index}, word: {word}")

            # if the current word is one of the full words on the board
            if word in SpiritBoard.FULL_WORDS:

                # if the word on the board has multiple points
                if isinstance(SpiritBoard.LOCATIONS[word], list):
                    # loop over the points for the word
                    for location in SpiritBoard.LOCATIONS[word]:
                        print(f"sliding to: {location}")
                        # slide the planchette to each point
                        self.slide_planchette(location, delay=0.02, step_size=step_size)

                        # pause at each point
                        time.sleep(0.25)

                # if the word has only a single point
                elif isinstance(SpiritBoard.LOCATIONS[word], tuple):
                    # slide the planchette to the point
                    self.slide_planchette(SpiritBoard.LOCATIONS[word], delay=0.02, step_size=step_size)

                    # pause at the point
                    time.sleep(0.5)

            else:  # the current word is not one of the full words
                # go one character at a time

                # loop over each character in the word
                for character in word:
                    # slide the planchette to the current characters location
                    self.slide_planchette(SpiritBoard.LOCATIONS[character], delay=0.02, step_size=step_size)

                    # pause after we arrive
                    time.sleep(0.5)

            # if we are not skipping spaces, and we are not done with the message
            if not skip_spaces and index < len(message_words) - 1:
                # handle the space
                # slide the planchette to the empty space location.
                self.slide_planchette(SpiritBoard.LOCATIONS[" "], delay=0.02, step_size=step_size)

                # pause after we arrive
                time.sleep(0.5)

        # after we've shown the whole message
        # slide the planchette back to it's home location
        self.slide_planchette(SpiritBoard.LOCATIONS["home"], delay=0.02, step_size=6)

    @staticmethod
    def sync_with_io(io) -> list:
        """
        Fetch messages from AdafruitIO and store them in the context variable.

        You must create the "SpiritBoard" feed object inside AdafruitIO for
        this to succeed.

        Will raise an exception if connecting or fetching failed.

        :param io: The initialized adafruit IO object

        :return: List of messages
        """

        # fetch the latest data in the feed
        incoming_message = io.receive_data("spiritboard")

        # if it's multiple messages seperated by commas
        if "," in incoming_message["value"]:
            # split on the commas to seperate the messages
            # and put them in context
            messages = incoming_message["value"].split(",")

        else:  # it's only a single message
            # set the single message into the context
            messages = [incoming_message["value"]]

        # print if successful
        if len(messages) > 0:
            print("io fetch success")

        return messages


    @staticmethod
    def read_local_messages_file(shuffle=False) -> list:
        """
        Read messages from the local spirit_messages.txt file on the CIRCUITPY drive.
        Each message should be on its own line within that file.

        :param boolean shuffle: Whether to shuffle the messages. Default is False
        which will keep them in the same order they appear in the file.

        :return: List of messages
        """

        # if the spirit_messages.txt file exists
        if "spirit_messages.txt" in os.listdir("/"):
            # open the file
            with open("/spirit_messages.txt", "r") as f:
                # split on newline and set the messages found into the context
                messages = f.read().split("\n")

        # if there are no messages
        if len(messages) == 0:
            # raise an error and tell the user to set some up
            raise RuntimeError("Connection to adafruit.io failed, and there were "
                               "no messages in spirit_messages.txt. Enter your WIFI "
                               "credentials, aio username, and token in settings.toml, or add "
                               "messages to spirit_messages.txt.")

        # if there are messages and we need to shuffle them
        elif shuffle:
            # temporary list to hold them
            shuffled_list = []

            # while there are still messages in the context messages list
            while len(messages) > 0:
                # pop a randomly chosen message from the context and
                # put it into the temporary list
                shuffled_list.append(messages.pop(
                    random.randint(0, len(messages) - 1)))

            # update the context list to the shuffled one
            messages = shuffled_list

        return messages

    @staticmethod
    def get_messages(io) -> list:
        """
        Higher level get messages function. It will first attempt to
        fetch the messages from Adafruit IO. If that doesn't work,
        it will read them from the local spirit_messages.txt file.

        :param io: The initialized adafruit IO object

        :return: List of messages
        """
        try:
            return SpiritBoard.sync_with_io(io)
        except OSError:
            print("Caught OSError. Will try again next time.\n"
                  "Falling back to spirit_messages.txt file.")
            return SpiritBoard.read_local_messages_file()
