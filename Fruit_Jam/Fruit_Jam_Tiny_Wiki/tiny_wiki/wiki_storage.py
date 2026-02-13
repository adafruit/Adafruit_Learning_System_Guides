# SPDX-FileCopyrightText: 2026 Tim C, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# Adapted from files found in tiny_wiki for Micropython by Kevin McAleer:
# https://github.com/kevinmcaleer/tiny_wiki
import os
import board
import busio
import storage
import digitalio
import adafruit_sdcard

class WikiStorage:
    """Handles file system operations for wiki pages"""

    def __init__(self, pages_dir="/sd/pages"):
        self.pages_dir = pages_dir

        self._sd_mounted = False
        sd_pins_in_use = False
        SD_CS = board.SD_CS
        # try to Connect to the sdcard card and mount the filesystem.
        try:
            # initialze CS pin
            cs = digitalio.DigitalInOut(SD_CS)
        except ValueError:
            # likely the SDCard was auto-initialized by the core
            sd_pins_in_use = True

            # if placeholder.txt file does not exist
            if "placeholder.txt" not in os.listdir("/sd/"):
                self._sd_mounted = True

        if not sd_pins_in_use:
            try:
                # if sd CS pin was not in use
                # try to initialize and mount the SDCard
                sdcard = adafruit_sdcard.SDCard(
                    busio.SPI(board.SD_SCK, board.SD_MOSI, board.SD_MISO), cs
                )
                vfs = storage.VfsFat(sdcard)
                storage.mount(vfs, "/sd")
                self._sd_mounted = True
            except OSError:
                # sdcard init or mounting failed
                self._sd_mounted = False

        print(f"sd mounted: {self._sd_mounted}")
        if not self._sd_mounted:
            raise RuntimeError("Please insert a micro SD card to use Tiny Wiki")

        self._ensure_pages_dir()

    def _ensure_pages_dir(self):
        """Create pages directory if it doesn't exist"""
        print(self.pages_dir)
        try:
            os.stat(self.pages_dir)
        except OSError:
            print(os.listdir("/sd/"))
            os.mkdir(self.pages_dir)

    def _get_page_path(self, page_name):
        """Get the file path for a page"""
        # Sanitize page name to prevent directory traversal
        page_name = page_name.replace("/", "_").replace("\\", "_")
        return "{}/{}.md".format(self.pages_dir, page_name)

    def page_exists(self, page_name):
        """Check if a page exists"""
        try:
            os.stat(self._get_page_path(page_name))
            return True
        except OSError:
            return False

    def read_page(self, page_name):
        """Read a page's content"""
        if not self.page_exists(page_name):
            return None

        path = self._get_page_path(page_name)
        with open(path, 'r') as f:
            return f.read()

    def write_page(self, page_name, content):
        """Write content to a page"""
        path = self._get_page_path(page_name)
        with open(path, 'w') as f:
            f.write(content)

    def delete_page(self, page_name):
        """Delete a page"""
        if self.page_exists(page_name):
            os.remove(self._get_page_path(page_name))

    def list_pages(self):
        """List all wiki pages"""
        try:
            files = os.listdir(self.pages_dir)
            # Remove .md extension and filter
            pages = [f[:-3] for f in files if f.endswith('.md')]
            pages.sort()
            return pages
        except OSError:
            return []
