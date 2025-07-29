# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
import adafruit_dang as curses
import time

from irc_client import IRCClient

ANSI_BLACK_ON_GREY = chr(27) + "[30;100m"
ANSI_RESET = chr(27) + "[0m"


class Window:
    """
    Terminal Window class that supports basic scrolling.
    """

    def __init__(self, n_rows, n_cols, row=0, col=0):
        self.n_rows = n_rows
        self.n_cols = n_cols
        self.row = row
        self.col = col

    @property
    def bottom(self):
        return self.row + self.n_rows - 1

    def up(self, cursor):  # pylint: disable=invalid-name
        if cursor.row == self.row - 1 and self.row > 0:
            self.row -= 1

    def down(self, buffer, cursor):
        if cursor.row == self.bottom + 1 and self.bottom < len(buffer) - 1:
            self.row += 1

    def horizontal_scroll(self, cursor, left_margin=5, right_margin=2):
        n_pages = cursor.col // (self.n_cols - right_margin)
        self.col = max(n_pages * self.n_cols - right_margin - left_margin, 0)

    def translate(self, cursor):
        return cursor.row - self.row, cursor.col - self.col


def irc_client_main(
    stdscr,
    radio,
    irc_config,
    terminal_tilegrid=None,
    audio_interface=None,
    beep_wave=None,
):
    """
    Main curses IRC client application loop.
    """
    irc_client = IRCClient(
        radio, irc_config, audio_interface=audio_interface, beep_wave=beep_wave
    )
    irc_client.connect()
    # irc_client.join()

    window = Window(terminal_tilegrid.height, terminal_tilegrid.width)
    stdscr.erase()
    img = [None] * window.n_rows
    status_bar = {
        "user_message": None,
        "user_message_shown_time": 0,
    }

    cur_row_index = 0

    user_input = ""

    def show_user_message(message):
        """
        Show a status message to the user
        """
        status_bar["user_message"] = message + (
            " " * (window.n_cols - 1 - len(message))
        )
        status_bar["user_message_shown_time"] = time.monotonic()

    def setline(row, line):
        """
        Set a line of text in the terminal window.
        """
        if img[row] == line:
            return
        img[row] = line
        line += " " * (window.n_cols - len(line) - 1)
        stdscr.addstr(row, 0, line)

    def get_page(row_index):
        """
        Get a page of messages from the message buffer.
        """
        page_len = window.n_rows - 2

        page_start = max((len(irc_client.message_buffer) + row_index) - page_len, 0)
        page_end = page_start + page_len

        page = irc_client.message_buffer[page_start:page_end]
        # print(f"get_page({row_index}) len: {len(page)} start: {page_start} end: {page_end} rows: {window.n_rows - 2}")
        return page

    try:
        # main application loop
        while True:
            lastrow = 0
            lines_added = irc_client.update()

            cur_page = get_page(cur_row_index)

            if lines_added > 0 and len(cur_page) < window.n_rows - 2:
                cur_row_index = max(cur_row_index - lines_added, 0)
                cur_page = get_page(cur_row_index)

            for row, line in enumerate(cur_page):
                lastrow = row
                setline(row, line)

            for row in range(lastrow + 1, window.n_rows - 2):
                setline(row, "")

            user_input_row = window.n_rows - 2
            if user_input:
                setline(user_input_row, user_input)
            else:
                setline(user_input_row, " " * (window.n_cols - 1))

            user_message_row = terminal_tilegrid.height - 1
            if status_bar["user_message"] is None:
                message = f" {irc_config['username']} | {irc_config['server']} | {irc_config['channel']}"
                message += " " * (terminal_tilegrid.width - len(message) - 1)
                line = f"{ANSI_BLACK_ON_GREY}{message}{ANSI_RESET}"
            else:
                line = f"{ANSI_BLACK_ON_GREY}{status_bar["user_message"]}{ANSI_RESET}"
                if status_bar["user_message_shown_time"] + 3.0 < time.monotonic():
                    status_bar["user_message"] = None
            setline(user_message_row, line)

            # read from the keyboard
            k = stdscr.getkey()
            if k is not None:
                if len(k) == 1 and " " <= k <= "~":
                    user_input += k

                elif k == "\n":  # enter key pressed
                    if not user_input.startswith("/"):
                        print(f"sending: {user_input}")
                        irc_client.send_message(user_input)
                        user_input = ""
                    else:  # slash commands
                        parts = user_input.split(" ", 1)
                        if parts[0] in {"/j", "/join"}:
                            if len(parts) >= 2 and parts[1] != "":
                                if parts[1] != irc_client.config["channel"]:
                                    irc_client.join(parts[1])
                                    user_input = ""
                                else:
                                    show_user_message("Already in channel")
                                    user_input = ""

                            else:
                                show_user_message(
                                    "Invalid /join arg. Use: /join <channel>"
                                )
                                user_input = ""
                        elif parts[0] == "/msg":
                            to_user, message_to_send = parts[1].split(" ", 1)
                            irc_client.send_dm(to_user, message_to_send)
                            user_input = ""
                        elif parts[0] == "/beep":
                            to_user = parts[1]
                            message_to_send = "*Beep*\x07"
                            irc_client.send_dm(to_user, message_to_send)
                            user_input = ""
                        elif parts[0] == "/op":
                            user_to_op = parts[1]
                            irc_client.op(user_to_op)
                            user_input = ""
                        elif parts[0] == "/deop":
                            user_to_op = parts[1]
                            irc_client.deop(user_to_op)
                            user_input = ""
                        elif parts[0] == "/kick":
                            user_to_kick = parts[1]
                            irc_client.kick(user_to_kick)
                            user_input = ""
                        elif parts[0] == "/ban":
                            user_to_ban = parts[1]
                            irc_client.ban(user_to_ban)
                            user_input = ""
                        elif parts[0] == "/unban":
                            user_to_unban = parts[1]
                            irc_client.unban(user_to_unban)
                            user_input = ""
                        elif parts[0] == "/whois":
                            user_to_check = parts[1]
                            irc_client.whois(user_to_check)
                            user_input = ""

                elif k in ("KEY_BACKSPACE", "\x7f", "\x08"):
                    user_input = user_input[:-1]
                elif k == "KEY_UP":
                    page_len = window.n_rows - 2
                    if len(irc_client.message_buffer) > page_len:
                        page_start = (
                            len(irc_client.message_buffer) + cur_row_index
                        ) - page_len
                        if page_start > 0:
                            cur_row_index -= 1
                elif k == "KEY_DOWN":
                    if cur_row_index < 0:
                        cur_row_index += 1

                elif k == "KEY_PGUP":
                    page_len = window.n_rows - 2
                    if len(irc_client.message_buffer) > page_len:
                        page_start = (
                            len(irc_client.message_buffer) + cur_row_index
                        ) - page_len
                        if page_start > 0:
                            cur_row_index -= 6
                elif k == "KEY_PGDN":
                    if cur_row_index <= 0:
                        cur_row_index = cur_row_index + 6
                else:
                    print(f"unknown key: {k}")

    except KeyboardInterrupt:
        irc_client.disconnect()
        raise KeyboardInterrupt


def run_irc_client(
    radio, irc_config, terminal, terminal_tilegrid, audio_interface=None, beep_wave=None
):
    """
    Entry point to run the curses IRC client application.
    """
    return curses.custom_terminal_wrapper(
        terminal,
        irc_client_main,
        radio,
        irc_config,
        terminal_tilegrid,
        audio_interface,
        beep_wave,
    )
