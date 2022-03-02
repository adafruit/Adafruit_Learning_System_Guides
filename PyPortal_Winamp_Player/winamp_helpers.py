# SPDX-FileCopyrightText: 2022 Tim C, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
"""
PyPortal winamp displayio widget classes.
"""
import os
import time
import json
import board
import displayio
import terminalio
from audioio import AudioOut
from audiomp3 import MP3Decoder
from adafruit_display_text import bitmap_label, scrolling_label


class WinampApplication(displayio.Group):
    """
    WinampApplication

    Helper class that manages song playback and UI components.

    :param playlist_file: json file containing the playlist of songs
    :param skin_image: BMP image file for skin background
    :param skin_config_file: json file containing color values
    :param pyportal_titano: boolean value. True if using Titano, False otherwise.
    """

    STATE_PLAYING = 0
    STATE_PAUSED = 1
    # pylint: disable=too-many-statements,too-many-branches
    def __init__(
        self,
        playlist_file="playlist.json",
        skin_image="/base_240x320.bmp",
        skin_config_file="base_config.json",
        pyportal_titano=False,
    ):
        self.SKIN_IMAGE = skin_image
        self.SKIN_CONFIG_FILE = skin_config_file
        self.PLAYLIST_FILE = playlist_file

        # read the skin config data into variable
        f = open(self.SKIN_CONFIG_FILE, "r")
        self.CONFIG_DATA = json.loads(f.read())
        f.close()

        if self.PLAYLIST_FILE:
            try:
                # read the playlist data into variable
                f = open(self.PLAYLIST_FILE, "r")
                self.PLAYLIST = json.loads(f.read())
                f.close()
            except OSError:
                # file not found
                self.auto_find_tracks()
            except ValueError:
                # json parse error
                self.auto_find_tracks()
        else:
            # playlist file argument was None
            self.auto_find_tracks()

        if self.PLAYLIST:
            try:
                if len(self.PLAYLIST["playlist"]["files"]) == 0:
                    # valid playlist json data, but no tracks
                    self.auto_find_tracks()
            except KeyError:
                self.auto_find_tracks()

        # initialize clock display
        self.clock_display = ClockDisplay(text_color=self.CONFIG_DATA["time_color"])
        if not pyportal_titano:
            # standard PyPortal and pynt clock display location
            # and playlist display parameters
            self.clock_display.x = 44
            self.clock_display.y = 22
            _max_playlist_display_chars = 30
            _rows = 3
        else:
            # PyPortal Titano clock display location
            # and playlist display parameters
            self.clock_display.x = 65
            self.clock_display.y = 37
            _max_playlist_display_chars = 42
            _rows = 4

        # initialize playlist display
        self.playlist_display = PlaylistDisplay(
            text_color=self.CONFIG_DATA["text_color"],
            max_chars=_max_playlist_display_chars,
            rows=_rows,
        )
        if not pyportal_titano:
            # standard PyPortal and pynt playlist display location
            self.playlist_display.x = 13
            self.playlist_display.y = 234
        else:
            # PyPortal Titano playlist display location
            self.playlist_display.x = 20
            self.playlist_display.y = 354

        # set playlist into playlist display
        self.playlist_display.from_files_list(self.PLAYLIST["playlist"]["files"])
        self.playlist_display.current_track_number = 1

        # get name of current song
        self.current_song_file_name = self.PLAYLIST["playlist"]["files"][
            self.playlist_display.current_track_number - 1
        ]

        if not pyportal_titano:
            # standard PyPortal and pynt max characters for track title
            _max_chars = 22
        else:
            # PyPortal Titano max characters for track title
            _max_chars = 29
        # initialize ScrollingLabel for track name
        self.current_song_lbl = scrolling_label.ScrollingLabel(
            terminalio.FONT,
            text=self.playlist_display.current_track_title,
            color=self.CONFIG_DATA["text_color"],
            max_characters=_max_chars,
        )
        self.current_song_lbl.anchor_point = (0, 0)
        if not pyportal_titano:
            # standard PyPortal and pynt track title location
            self.current_song_lbl.anchored_position = (98, 19)
        else:
            # PyPortal Titano track title location
            self.current_song_lbl.anchored_position = (130, 33)

        # Setup the skin image file as the bitmap data source
        self.background_bitmap = displayio.OnDiskBitmap(self.SKIN_IMAGE)

        # Create a TileGrid to hold the bitmap
        self.background_tilegrid = displayio.TileGrid(
            self.background_bitmap, pixel_shader=self.background_bitmap.pixel_shader
        )

        # initialize parent displayio.Group
        super().__init__()

        # Add the TileGrid to the Group
        self.append(self.background_tilegrid)

        # add other UI componenets
        self.append(self.current_song_lbl)
        self.append(self.clock_display)
        self.append(self.playlist_display)

        # Start playing first track
        self.current_song_file = open(self.current_song_file_name, "rb")
        self.decoder = MP3Decoder(self.current_song_file)
        self.audio = AudioOut(board.SPEAKER)
        self.audio.play(self.decoder)

        self.CURRENT_STATE = self.STATE_PLAYING

        # behavior variables.
        self._start_time = time.monotonic()
        self._cur_time = time.monotonic()
        self._pause_time = None
        self._pause_elapsed = 0
        self._prev_time = None
        self._seconds_elapsed = 0
        self._last_increment_time = 0

    def auto_find_tracks(self):
        """
        Initialize the song_list by searching for all MP3's within
        two layers of directories on the SDCard.

        e.g. It will find all of:
        /sd/Amazing Song.mp3
        /sd/[artist_name]/Amazing Song.mp3
        /sd/[artist_name]/[album_name]/Amazing Song.mp3

        but won't find:
        /sd/my_music/[artist_name]/[album_name]/Amazing Song.mp3

        :return: None
        """
        # list that holds all files in the root of SDCard
        _root_sd_all_files = os.listdir("/sd/")

        # list that will hold all directories in the root of the SDCard.
        _root_sd_dirs = []

        # list that will hold all subdirectories inside of root level directories
        _second_level_dirs = []

        # list that will hold all MP3 file songs that we find
        _song_list = []

        # loop over all files found on SDCard
        for _file in _root_sd_all_files:
            try:
                # Check if the current file is a directory
                os.listdir("/sd/{}".format(_file))

                # add it to a list to look at later
                _root_sd_dirs.append(_file)
            except OSError:
                # current file was not a directory, nothing to do.
                pass

            # if current file is an MP3 file
            if _file.endswith(".mp3"):
                # we found an MP3 file, add it to the list that will become our playlist
                _song_list.append("/sd/{}".format(_file))

        # loop over root level directories
        for _dir in _root_sd_dirs:
            # loop over all files inside of root level directory
            for _file in os.listdir("/sd/{}".format(_dir)):

                # check if current file is a directory
                try:
                    # if it is a directory, loop over all files inside of it
                    for _inner_file in os.listdir("/sd/{}/{}".format(_dir, _file)):
                        # check if inner file is an MP3
                        if _inner_file.endswith(".mp3"):
                            # we found an MP3 file, add it to the list that will become our playlist
                            _song_list.append(
                                "/sd/{}/{}/{}".format(_dir, _file, _inner_file)
                            )
                except OSError:
                    # current file is not a directory
                    pass
                # if the current file is an MP3 file
                if _file.endswith(".mp3"):
                    # we found an MP3 file, add it to the list that will become our playlist
                    _song_list.append("/sd/{}/{}".format(_dir, _file))

        # format the songs we found into the PLAYLIST data structure
        self.PLAYLIST = {"playlist": {"files": _song_list}}

        # print message to user letting them know we auto-generated the playlist
        print("Auto Generated Playlist from MP3's found on SDCard:")
        print(json.dumps(self.PLAYLIST))

    def update(self):
        """
        Must be called each iteration from the main loop.
        Responsible for updating all sub UI components and
        managing song playback

        :return: None
        """
        self._cur_time = time.monotonic()
        if self.CURRENT_STATE == self.STATE_PLAYING:
            # if it's time to increase the time on the ClockDisplay
            if self._cur_time >= self._last_increment_time + 1:
                # increase ClockDisplay by 1 second
                self._seconds_elapsed += 1
                self._last_increment_time = self._cur_time
                self.clock_display.seconds = int(self._seconds_elapsed)

        # update the track label (scrolling)
        self.current_song_lbl.update()

        if self.CURRENT_STATE == self.STATE_PLAYING:
            # if we are supposed to be playing but aren't
            # it means the track ended.
            if not self.audio.playing:
                # start the next track
                self.next_track()

        # store time for comparison later
        self._prev_time = self._cur_time

    def play_current_track(self):
        """
        Update the track label and begin playing the song for current
        track in the playlist.

        :return: None
        """
        # set the track title
        self.current_song_lbl.full_text = self.playlist_display.current_track_title

        # save start time in a variable
        self._start_time = self._cur_time

        # if previous song is still playing
        if self.audio.playing:
            # stop playing
            self.audio.stop()

        # close previous song file
        self.current_song_file.close()

        # open new song file
        self.current_song_file_name = self.PLAYLIST["playlist"]["files"][
            self.playlist_display.current_track_number - 1
        ]
        self.current_song_file = open(self.current_song_file_name, "rb")
        self.decoder.file = self.current_song_file

        # play new song file
        self.audio.play(self.decoder)

        # if user paused the playback
        if self.CURRENT_STATE == self.STATE_PAUSED:
            # pause so it's loaded, and ready to resume
            self.audio.pause()

    def next_track(self):
        """
        Advance to the next track.
        :return: None
        """
        # reset ClockDisplay to 0
        self._seconds_elapsed = 0
        self.clock_display.seconds = int(self._seconds_elapsed)

        # increment current track number
        self.playlist_display.current_track_number += 1

        try:
            # start playing track
            self.play_current_track()
        except OSError as e:
            # file not found
            print("Error playing: {}".format(self.current_song_file_name))
            print(e)
            self.next_track()
            return

    def previous_track(self):
        """
        Go back to previous track.

        :return: None
        """
        # reset ClockDisplay to 0
        self._seconds_elapsed = 0
        self.clock_display.seconds = int(self._seconds_elapsed)

        # decrement current track number
        self.playlist_display.current_track_number -= 1

        try:
            # start playing track
            self.play_current_track()
        except OSError as e:
            # file not found
            print("Error playing: {}".format(self.current_song_file_name))
            print(e)
            self.previous_track()
            return

    def pause(self):
        """
        Stop playing song and wait until resume function.

        :return: None
        """
        if self.audio.playing:
            self.audio.pause()
        self.CURRENT_STATE = self.STATE_PAUSED

    def resume(self):
        """
        Resume playing song after having been paused.

        :return: None
        """
        self._last_increment_time = self._cur_time
        if self.audio.paused:
            self.audio.resume()
        self.CURRENT_STATE = self.STATE_PLAYING


class PlaylistDisplay(displayio.Group):
    """
    PlaylistDisplay

    Displayio widget class that shows 3 songs from the playlist.
    It has functions to help manage which song is currently at the
    top of the list.

    :param text_color: Hex color code for the text in the list
    :param song_list: Song names in the list
    :param current_track_number: initial track number shown at the top of the list.l
    :param max_chars: int max number of characters to show in a row. Excess characters are cut.
    :param rows: how many rows to show. One track per row. Default 3 rows
    """

    def __init__(
        self, text_color, song_list=None, current_track_number=0, max_chars=30, rows=3
    ):
        super().__init__()

        self._rows = rows
        if song_list is None:
            song_list = []
        self._song_list = song_list
        self._current_track_number = current_track_number

        self._max_chars = max_chars

        # the label to show track titles inside of
        self._label = bitmap_label.Label(terminalio.FONT, color=text_color)

        # default position, top left inside of the self instance group
        self._label.anchor_point = (0, 0)
        self._label.anchored_position = (0, 0)
        self.append(self._label)

        # initial refresh to show the songs
        self.update_display()

    def update_display(self):
        """
        refresh the label to show the current tracks based on current track number.

        :return: None
        """

        # get the current track plus the following 2
        _showing_songs = self.song_list[
            self.current_track_number - 1 : self.current_track_number + self._rows - 1
        ]

        # format the track titles into a single string with newlines
        _showing_string = ""
        for index, song in enumerate(_showing_songs):
            _cur_line = "{}. {}".format(
                self.current_track_number + index, song[: self._max_chars]
            )
            _showing_string = "{}{}\n".format(_showing_string, _cur_line)

        # put it into the label
        self._label.text = _showing_string

    @property
    def song_list(self):
        """

        :return: the list of songs
        """
        return self._song_list

    @song_list.setter
    def song_list(self, new_song_list):
        self._song_list = new_song_list
        self.update_display()

    def from_files_list(self, files_list):
        """
        Initialize the song_list from a list of filenames.
        Directories and MP3 file extension will be removed.

        :param files_list: list of strings containing filenames
        :return: None
        """
        _song_list = []
        for _file in files_list:
            _song_list.append(_file.split("/")[-1].replace(".mp3", ""))
        self.song_list = _song_list

    @property
    def current_track_number(self):
        """
        Track number is 1 based. Track number 1 is the first one in the playlist.
        Autowraps from 0 back to last song in the playlist.

        :return: current track number
        """
        return self._current_track_number

    @current_track_number.setter
    def current_track_number(self, new_index):
        if new_index <= len(self.song_list):
            if new_index != 0:
                self._current_track_number = new_index
            else:
                self._current_track_number = len(self.song_list)
        else:
            self._current_track_number = new_index % len(self.song_list)
        self.update_display()

    @property
    def current_track_title(self):
        """

        :return: Current track title as a formatted string with the track number pre-pended.

        e.g. "1. The Greatest Song"
        """

        if self.current_track_number == 0:
            return "1. {}".format(self.song_list[0])
        else:
            return "{}. {}".format(
                self.current_track_number, self.song_list[self.current_track_number - 1]
            )


class ClockDisplay(displayio.Group):
    """
    DisplayIO widget to show an incrementing minutes and seconds clock.
    2 digits for minutes, and 2 digits for seconds. Values will get
    zero padded. Does not include colon between the values.

    :param text_color: Hex color code for the clock text
    """

    def __init__(self, text_color):
        super().__init__()

        # seconds elapsed to show on the clock display
        self._seconds = 0

        # Minutes tens digit label
        self.first_digit = bitmap_label.Label(terminalio.FONT, color=text_color)
        self.first_digit.anchor_point = (0, 0)
        self.first_digit.anchored_position = (0, 0)
        self.append(self.first_digit)

        # Minutes ones digit label
        self.second_digit = bitmap_label.Label(terminalio.FONT, color=text_color)
        self.second_digit.anchor_point = (0, 0)
        self.second_digit.anchored_position = (10, 0)
        self.append(self.second_digit)

        # Seconds tens digit label
        self.third_digit = bitmap_label.Label(terminalio.FONT, color=text_color)
        self.third_digit.anchor_point = (0, 0)
        self.third_digit.anchored_position = (26, 0)
        self.append(self.third_digit)

        # Seconds ones digit label
        self.fourth_digit = bitmap_label.Label(terminalio.FONT, color=text_color)
        self.fourth_digit.anchor_point = (0, 0)
        self.fourth_digit.anchored_position = (36, 0)
        self.append(self.fourth_digit)

        # initialize showing the display
        self.update_display()

    @property
    def seconds(self):
        """
        :return: the seconds elapsed currently showing
        """
        return self._seconds

    @seconds.setter
    def seconds(self, new_seconds_value):
        """
        Save new seconds elapsed and update the display to reflect it.

        :param new_seconds_value: the new seconds elapsed to show
        :return: None
        """
        self._seconds = new_seconds_value
        self.update_display()

    def update_display(self):
        """
        Update the text in the labels to reflect the current seconds elapsed time.

        :return: None
        """
        # divide to get number of minutes elapsed
        _minutes = self.seconds // 60

        # modulus to get number of seconds elapsed
        # for the partial minute
        _seconds = self.seconds % 60

        # zero pad the values and format into strings
        _minutes_str = f"{_minutes:02}"
        _seconds_str = f"{_seconds:02}"

        # update the text in the minutes labels
        if self.first_digit.text != _minutes_str[0]:
            self.first_digit.text = _minutes_str[0]
        if self.second_digit.text != _minutes_str[1]:
            self.second_digit.text = _minutes_str[1]

        # update the text in the seconds label
        if self.third_digit.text != _seconds_str[0]:
            self.third_digit.text = _seconds_str[0]
        if self.fourth_digit.text != _seconds_str[1]:
            self.fourth_digit.text = _seconds_str[1]
