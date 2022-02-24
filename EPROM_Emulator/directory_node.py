# SPDX-FileCopyrightText: 2018 Dave Astels for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
The MIT License (MIT)

Copyright (c) 2018 Dave Astels

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

--------------------------------------------------------------------------------

Manage a directory in the file system.
"""

import os


class DirectoryNode:
    """Display and navigate the SD card contents"""

    def __init__(self, display, parent=None, name="/"):
        """Initialize a new instance.
           :param adafruit_ssd1306.SSD1306 on: the OLED instance to display on
           :param DirectoryNode below: optional parent directory node
           :param string named: the optional name of the new node
        """
        self.display = display
        self.parent = parent
        self.name = name
        self.files = []
        self.top_offset = 0
        self.old_top_offset = -1
        self.selected_offset = 0
        self.old_selected_offset = -1

    def __cleanup(self):
        """Dereference things for speedy gc."""
        self.display = None
        self.parent = None
        self.name = None
        self.files = None
        return self

    @staticmethod
    def __is_dir(path):
        """Determine whether a path identifies a machine code bin file.
           :param string path: path of the file to check
        """
        if path[-2:] == "..":
            return False
        try:
            os.listdir(path)
            return True
        except OSError:
            return False

    @staticmethod
    def __sanitize(name):
        """Nondestructively strip off a trailing slash, if any, and return the result.
           :param string name: the filename
        """
        if name[-1] == "/":
            return name[:-1]
        return name

    # pylint: disable=protected-access
    def __path(self):
        """Return the result of recursively follow the parent links, building a full
           path to this directory."""
        if self.parent:
            return self.parent.__path() + os.sep + self.__sanitize(self.name)
        return self.__sanitize(self.name)

    def __make_path(self, filename):
        """Return a full path to the specified file in this directory.
           :param string filename: the name of the file in this directory
         """
        return self.__path() + os.sep + filename

    def __number_of_files(self):
        """The number of files in this directory, including the ".." for the parent
            directory if this isn't the top directory on the SD card."""
        self.__get_files()
        return len(self.files)

    def __get_files(self):
        """Return a list of the files in this directory.
           If this is not the top directory on the SD card, a
           ".." entry is the first element.
           Any directories have a slash appended to their name."""
        if len(self.files) == 0:
            self.files = os.listdir(self.__path())
            self.files.sort()
            if self.parent:
                self.files.insert(0, "..")
            for index, name in enumerate(self.files, start=1):
                if self.__is_dir(self.__make_path(name)):
                    self.files[index] = name + "/"

    def __update_display(self):
        """Update the displayed list of files if required."""
        if self.top_offset != self.old_top_offset:
            self.__get_files()
            self.display.fill(0)
            min_offset = min(self.top_offset + 4, self.__number_of_files())

            for i in range(self.top_offset, min_offset):
                self.display.text(self.files[i], 10, (i - self.top_offset) * 8)
            self.display.show()
            self.old_top_offset = self.top_offset

    def __update_selection(self):
        """Update the selected file lighlight if required."""
        if self.selected_offset != self.old_selected_offset:
            if self.old_selected_offset > -1:
                old_offset = (self.old_selected_offset - self.top_offset) * 8

                self.display.text(">", 0, old_offset, 0)

            new_offset = (self.selected_offset - self.top_offset) * 8
            self.display.text(">", 0, new_offset, 1)
            self.display.show()
            self.old_selected_offset = self.selected_offset

    @staticmethod
    def __is_directory_name(filename):
        """Is a filename the name of a directory.
           :param string filename: the name of the file
        """
        return filename[-1] == '/'

    @property
    def selected_filename(self):
        """The name of the currently selected file in this directory."""
        self.__get_files()
        return self.files[self.selected_offset]

    @property
    def selected_filepath(self):
        """The full path of the currently selected file in this directory."""
        return self.__make_path(self.selected_filename)

    def force_update(self):
        """Force an update of the file list and selected file highlight."""
        self.old_selected_offset = -1
        self.old_top_offset = -1
        self.__update_display()
        self.__update_selection()

    def down(self):
        """Move down in the file list if possible, adjusting the selected file
        indicator and scrolling the display as required."""
        if self.selected_offset < self.__number_of_files() - 1:
            self.selected_offset += 1
            if self.selected_offset == self.top_offset + 4:
                self.top_offset += 1
                self.__update_display()
        self.__update_selection()

    def up(self):
        """Move up in the file list if possible, adjusting the selected file indicator
           and scrolling the display as required."""
        if self.selected_offset > 0:
            self.selected_offset -= 1
            if self.selected_offset < self.top_offset:
                self.top_offset -= 1
                self.__update_display()
        self.__update_selection()

    def click(self):
        """Handle a selection and return the new current directory.
           If the selected file is the parent, i.e. "..", return to the parent
           directory.
           If the selected file is a directory, go into it."""
        if self.selected_filename == "..":
            if self.parent:
                p = self.parent
                p.force_update()
                self.__cleanup()
                return p
        elif self.__is_directory_name(self.selected_filename):
            new_node = DirectoryNode(
                self.display, self, self.selected_filename)
            new_node.force_update()
            return new_node
        return self
