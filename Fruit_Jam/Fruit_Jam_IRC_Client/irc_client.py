# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
import time

import adafruit_connection_manager

ANSI_ESCAPE_CODES = [
    chr(27) + "[30m",
    chr(27) + "[31m",
    chr(27) + "[32m",
    chr(27) + "[33m",
    chr(27) + "[34m",
    chr(27) + "[35m",
    chr(27) + "[36m",
]
ANSI_RESET = chr(27) + "[0m"


class IRCClient:
    """
    Handles interaction with IRC Server and makes incoming messages available.

    :param radio: The network radio to connect with.
    :param dict irc_config: Dictionary containing IRC configration for
      server, port, username and channel.
    :param audio_interface: Optional interface to play audio from for beep messages
    :param beep_wave: Optional wave file to use for beep messages
    :param int max_line_length: Maximum characters per line to format messages into.
    """

    def __init__(
        self,
        radio,
        irc_config,
        audio_interface=None,
        beep_wave=None,
        max_line_length=120,
    ):
        self.radio = radio
        self.config = irc_config
        required = {"username", "server", "channel"}
        for key in required:
            if key not in self.config:
                raise ValueError(
                    f"missing required config key. Required keys are: {required}"
                )

        if "port" not in self.config:
            self.config["port"] = 6667
        if "timeout" not in self.config:
            self.config["timeout"] = 120

        self.pool = adafruit_connection_manager.get_radio_socketpool(radio)
        self.connection_manager = adafruit_connection_manager.get_connection_manager(
            self.pool
        )

        ssl_context = adafruit_connection_manager.get_radio_ssl_context(radio)
        print(f"Connecting to {self.config['server']}:{self.config['port']}...")
        self.socket = self.connection_manager.get_socket(
            self.config["server"],
            self.config["port"],
            "",
            timeout=0.01,
            is_ssl=True,
            ssl_context=ssl_context,
        )
        print("Connected")

        # color to use for next unique username
        self.next_color_index = 4

        # map of unique usernames to color
        self.user_color_map = {}

        # buffer for incoming data until it's a full line
        self.line_buffer = ""

        # buffer for full incoming chat messages
        self.message_buffer = []

        # whether to show whois reply message on screen
        self.show_whois_reply = False

        self.audio_interface = audio_interface
        if audio_interface is not None:
            self.beep_wave = beep_wave

        self.max_line_length = max_line_length

    def connect(self):
        """
        Connect to IRC Server
        """
        # Send nick and user info
        self.socket.send(f"NICK {self.config['username']}\r\n".encode("utf-8"))
        self.socket.send(
            f"USER {self.config['username']} 0 * :{self.config['username']}\r\n".encode(
                "utf-8"
            )
        )

    def disconnect(self):
        """
        Disconnect from IRC Server
        """
        self.socket.send("QUIT :Goodbye\r\n".encode("utf-8"))
        self.socket.close()

    def readlines(self):
        """
        Read incoming data from the socket and return a list of lines read.
        """
        lines = []
        # Receive data
        data = self.socket.recv(4096).decode("utf-8")
        if not data:
            raise RuntimeError("Connection closed by server")

        self.line_buffer += data

        # Process complete lines
        while "\r\n" in self.line_buffer:
            line, self.line_buffer = self.line_buffer.split("\r\n", 1)

            if line:
                lines.append(line)

        return lines

    def update(self):
        """
        Check for udpates from the server. Main loop of the program should call this.
        """
        updated_display_lines = 0
        try:
            lines = self.readlines()
            for line in lines:
                updated_display_lines += self.process_message(line)

        except OSError as e:
            # no data before timeout
            # print(e)
            if "ETIMEDOUT" not in str(e):
                raise RuntimeError(e) from e
                # raise RuntimeError("Connection timed out")
        return updated_display_lines

    def send_message(self, message):
        """
        Send a message to the channel that the user is in.
        """
        irc_command = f"PRIVMSG {self.config['channel']} :{message}\r\n"
        self.socket.send(irc_command.encode("utf-8"))
        self.process_message(
            f":{self.config['username']}!~{self.config['username']}@localhost "
            + irc_command[:-2]
        )

    def send_dm(self, to_user, message):
        """
        Send a direct message to a specified user.
        """
        irc_command = f"PRIVMSG {to_user} :{message}\r\n"
        self.socket.send(irc_command.encode("utf-8"))
        color = self.get_color_for_user(to_user)
        self.message_buffer.append(f"DM out: <{color}{to_user}{ANSI_RESET}> {message}")

    def op(self, user):
        """
        Make specified user an operator in the channel that the user is in.
        You must already be an operator to grant operator privilege.
        """
        op_cmd = f"MODE {self.config['channel']} +o {user}\r\n"
        self.socket.send(op_cmd.encode("utf-8"))

    def deop(self, user):
        """
        Remove operator privilege from the specified user for this channel.
        """
        deop_cmd = f"MODE {self.config['channel']} -o {user}\r\n"
        self.socket.send(deop_cmd.encode("utf-8"))

    def kick(self, user):
        """
        Kick a specified user from the channel.
        """
        kick_cmd = f"KICK {self.config['channel']} {user}\r\n"
        self.socket.send(kick_cmd.encode("utf-8"))

    def get_technical_name(self, nickname):
        """
        Get the full technical name of a user given a nickname
        """
        start_time = time.monotonic()
        whois_cmd = f"WHOIS {nickname}\r\n"
        self.socket.send(whois_cmd.encode("utf-8"))

        whois_resp_lines = None
        while whois_resp_lines is None and start_time + 3.0 > time.monotonic():
            try:
                whois_resp_lines = self.readlines()
            except OSError as e:
                if "ETIMEDOUT" in str(e):
                    whois_resp_lines = None
                else:
                    raise RuntimeError(e) from e

        if whois_resp_lines is None:
            return None

        for line in whois_resp_lines:
            line = line.lstrip("\0")
            parts = line.split(" ", 2)
            if len(parts) >= 2:
                command = parts[1]
                if command != "311":
                    self.process_message(line)
                    continue

                whois_response = parts[2].split(" ", 1)[1]
                response_parts = whois_response.split(" ")
                technical_name = f"*!{response_parts[1]}@{response_parts[2]}"
                return technical_name

        return None

    def ban(self, user):
        """
        Ban the specified user from the channel
        """
        technical_name = self.get_technical_name(user)
        if technical_name is not None:
            ban_cmd = f"MODE {self.config['channel']} +b {technical_name}\r\n"
            self.socket.send(ban_cmd.encode("utf-8"))
        else:
            self.message_buffer.append(
                f"{ANSI_RESET} Error: failed whois lookup for ban"
            )

    def unban(self, user):
        """
        Unban the specified user from the channel
        """
        technical_name = self.get_technical_name(user)
        if technical_name is not None:
            ban_cmd = f"MODE {self.config['channel']} -b {technical_name}\r\n"
            self.socket.send(ban_cmd.encode("utf-8"))
        else:
            self.message_buffer.append(
                f"{ANSI_RESET} Error: failed whois lookup for unban"
            )

    def whois(self, user):
        """
        Run a whois query on the specified user
        """
        self.show_whois_reply = True
        whois_cmd = f"WHOIS {user}\r\n"
        self.socket.send(whois_cmd.encode("utf-8"))

    def leave_channel(self):
        """
        Leave the channel
        """

        self.socket.send(f"PART {self.config['channel']}\r\n".encode("utf-8"))

    def join(self, new_channel=None):
        """
        Join the specified channel. This will leave the prior channel.
        """
        if new_channel is not None and new_channel != self.config["channel"]:
            self.leave_channel()
            self.config["channel"] = new_channel

        print(f"Joining channel {self.config['channel']}...")
        self.socket.send(f"JOIN {self.config['channel']}\r\n".encode("utf-8"))
        self.message_buffer.append(f"{ANSI_RESET}* Joined {self.config['channel']} *")

    def get_color_for_user(self, username):
        """
        Get the color to use for the specified username
        """
        if username not in self.user_color_map:
            self.user_color_map[username] = self.next_color_index
            self.next_color_index += 1
            if self.next_color_index > 6:
                self.next_color_index = 1

        return ANSI_ESCAPE_CODES[self.user_color_map[username]]

    @staticmethod
    def split_string_chunks(s, chunk_size):
        """
        Split a string into chunks of specified size.
        """
        chunks = []
        for i in range(0, len(s), chunk_size):
            chunks.append(s[i : i + chunk_size])
        return chunks

    def process_message(self, message):
        # pylint: disable=too-many-branches, too-many-statements
        """
        Process an incoming IRC message
        :param message: The message that came from the IRC server.

        :return lines_added: The number of lines added to the display
        """
        # pylint: disable=too-many-locals
        lines_added = 0

        message = message.lstrip("\x00")
        print(f"RAW: {message.encode('utf-8')}")

        # Handle PING messages (keep connection alive)
        if message.startswith("PING"):
            pong_response = message.replace("PING", "PONG")
            self.socket.send(f"{pong_response}\r\n".encode("utf-8"))
            print("Responded to PING")
            return 0

        # Parse IRC message format: :prefix COMMAND params
        parts = message.split(" ", 2)
        # pylint: disable=too-many-nested-blocks
        if len(parts) >= 2:
            command = parts[1]
            try:
                command_num = int(command)
            except ValueError:
                command_num = None

            # End of MOTD - now we can join the channel
            if command in {"376", "422"}:  # 422 is "no MOTD"
                # join channel
                self.join()

            # Welcome messages (001-004 are standard welcome messages)
            elif command in [
                "001",
                "002",
                "003",
                "004",
                "251",
                "252",
                "253",
                "254",
                "255",
                "265",
                "266",
                "375",
                "372",
            ]:
                if len(parts) >= 3:
                    welcome_text = parts[2]
                    if welcome_text.startswith(":"):
                        welcome_text = welcome_text[1:]

                    print(
                        f"'{welcome_text[0:11]}' startswith '{self.config['username']}' ? {welcome_text.startswith(self.config['username'])}"  # pylint: disable=line-too-long
                    )
                    if welcome_text.startswith(self.config["username"]):
                        welcome_text = welcome_text.replace(
                            self.config["username"], "", 1
                        )
                    # terminal.write(f"WELCOME: {welcome_text}\n")
                    self.message_buffer.append(f"{welcome_text}")
                    lines_added += 1
                    print(f"WELCOME: {welcome_text}")

            # Channel messages
            elif command == "PRIVMSG":
                if len(parts) >= 3:
                    # Extract sender nickname
                    sender = parts[0]
                    if sender.startswith(":"):
                        sender = sender[1:]
                    if "!" in sender:
                        sender = sender.split("!")[0]

                    # Extract message content
                    message_content = parts[2]

                    inc_channel, inc_message = message_content.split(" ", 1)

                    message_content = inc_message[1:]

                    if "*beep*" in message_content:
                        if (
                            self.audio_interface is not None
                            and not self.audio_interface.playing
                        ):
                            print("playing beep")
                            self.audio_interface.play(self.beep_wave)
                            # print(f"is playing: {self.audio_interface.playing}")
                            while self.audio_interface.playing:
                                pass

                    print(f"message_content: {message_content.encode('utf-8')}")

                    color = self.get_color_for_user(sender)

                    if inc_channel == self.config["channel"]:
                        full_line = f"<{color}{sender}{ANSI_RESET}> {message_content}"
                        if len(full_line) < self.max_line_length:
                            self.message_buffer.append(full_line)
                            lines_added += 1
                        else:
                            chunks = self.split_string_chunks(
                                full_line, self.max_line_length
                            )
                            for chunk in chunks:
                                self.message_buffer.append(f"{ANSI_RESET}{chunk}")
                                lines_added += 1
                    elif inc_channel == self.config["username"]:
                        self.message_buffer.append(
                            f"DM in: <{color}{sender}{ANSI_RESET}> {message_content}"
                        )
                        lines_added += 1
                    print(f"<{sender}> {message_content}")

            # Join confirmations
            elif command == "JOIN":
                sender = parts[0]
                if sender.startswith(":"):
                    sender = sender[1:]
                if "!" in sender:
                    sender = sender.split("!")[0]

                if len(parts) >= 3:
                    joined_channel = parts[2]
                    if joined_channel.startswith(":"):
                        joined_channel = joined_channel[1:]
                    print(f"*** {sender} joined {joined_channel}")

            # error messages
            elif command_num is not None and 400 <= command_num <= 553:
                # message codes: https://www.alien.net.au/irc/irc2numerics.html
                self.message_buffer.append(f"{ANSI_RESET}{command} {parts[2]}")
                lines_added += 1

            # whois reply
            elif self.show_whois_reply and command == "311":
                whois_response = parts[2].split(" ", 1)[1]
                self.message_buffer.append(f"{ANSI_RESET}{whois_response}")
                lines_added += 1
                self.show_whois_reply = False

            # Mode messages
            elif command == "MODE":
                action_user = parts[0].split("!", 1)[0][1:]
                mode_msg_parts = parts[2].split(" ", 2)
                if len(mode_msg_parts) >= 3:
                    channel, mode, target_user = (  # pylint: disable=unused-variable
                        mode_msg_parts
                    )
                    action_user_color = self.get_color_for_user(action_user)
                    target_user_color = self.get_color_for_user(target_user)
                    self.message_buffer.append(
                        f"{action_user_color}{action_user}{ANSI_RESET} sets mode {mode} on {target_user_color}{target_user}{ANSI_RESET}"  # pylint: disable=line-too-long
                    )
                    lines_added += 1

            # Part messages
            elif command == "PART":
                sender = parts[0]
                if sender.startswith(":"):
                    sender = sender[1:]
                if "!" in sender:
                    sender = sender.split("!")[0]

                if len(parts) >= 3:
                    left_channel = parts[2]
                    print(f"*** {sender} left {left_channel}")

            # Quit messages
            elif command == "QUIT":
                sender = parts[0]
                if sender.startswith(":"):
                    sender = sender[1:]
                if "!" in sender:
                    sender = sender.split("!")[0]

                quit_message = ""
                if len(parts) >= 3:
                    quit_message = parts[2]
                    if quit_message.startswith(":"):
                        quit_message = quit_message[1:]

                print(f"*** {sender} quit ({quit_message})")

        return lines_added
