# SPDX-FileCopyrightText: 2026 Tim C, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""CircuitPython port of Tiny Wiki for the Fruit Jam.

This project was ported from tiny_wiki for Micropython by Kevin McAleer:
https://github.com/kevinmcaleer/tiny_wiki

This script runs on CircuitPython with the ESP32SPI WiFi coprocessor. It uses
Adafruit's HTTP Server and TemplateEngine libraries to serve a small Wiki system.
Wiki pages are stored as markdown pages on the micro SD card.
"""

import hashlib
import json
import os

import board
import busio
from digitalio import DigitalInOut
import adafruit_esp32spi
import adafruit_connection_manager
from adafruit_httpserver import Response, Redirect, Server
from adafruit_httpserver.methods import POST
from adafruit_templateengine import render_template

from tiny_wiki.markdown import SimpleMarkdown
from tiny_wiki.wiki_storage import WikiStorage

# directory for HTML template files
TEMPLATES_DIR = "/templates"

# title to show at the top of the Wiki pages
WIKI_TITLE = os.getenv("WIKI_TITLE", "CircuitPython Tiny Wiki")

# name of the auto created default page
DEFAULT_PAGE_NAME = "Home"

# location of the directory to store Wiki page markdown files
PAGES_DIR = os.getenv("WIKI_PAGES_DIR", "/sd/pages")

# port to host the webserver on
SERVER_PORT = int(os.getenv("WIKI_SERVER_PORT", "8000"))

# location of the auth data file, None / auth disabled by default
WIKI_AUTH_DATA_FILE = os.getenv("WIKI_AUTH_DATA_FILE", None)

# static salt string used when hashing passwords
PASSWORD_SALT = os.getenv("WIKI_PASSWORD_SALT", "tinywiki_salt")

# secret key used to generate authenticated session tokens
WIKI_AUTH_SECRET_KEY = os.getenv("WIKI_AUTH_SECRET_KEY", "Sup3r$ecre7")

# valid characters for random dynamic string used to generate authenticated session tokens
RANDOM_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!#$%&-_()^"

# WIFI credentials
WIFI_SSID = os.getenv("CIRCUITPY_WIFI_SSID")
WIFI_PASSWORD = os.getenv("CIRCUITPY_WIFI_PASSWORD")
if not WIFI_SSID or not WIFI_PASSWORD:
    raise ValueError("Set WIFI_SSID (or CIRCUITPY_WIFI_SSID) and WIFI_PASSWORD in the environment")

# list to hold valid session tokens if auth is enabled
valid_session_tokens = []


with open("Home.md") as f:
    DEFAULT_PAGE_CONTENT = f.read()

# --- Hardware and networking -------------------------------------------------

def _init_wifi():
    """Connect to WiFi via the ESP32SPI coprocessor and return the socket pool."""

    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    esp32_ready = DigitalInOut(board.ESP_BUSY)
    esp32_reset = DigitalInOut(board.ESP_RESET)
    esp32_cs = DigitalInOut(board.ESP_CS)

    _radio = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

    print(f"Connecting to {WIFI_SSID}...")
    _radio.connect(WIFI_SSID, WIFI_PASSWORD)
    print("WiFi connected")

    pool = adafruit_connection_manager.get_radio_socketpool(_radio)
    _ssl_context = adafruit_connection_manager.get_radio_ssl_context(_radio)
    connection_manager = adafruit_connection_manager.get_connection_manager(pool)

    # Keep the connection manager alive to ensure sockets stay open
    return _radio, pool, connection_manager

# initialize WiFi and server object
radio, socket_pool, _connection_manager = _init_wifi()
server = Server(socket_pool, debug=True)


# --- Storage & Markdown helpers ---------------------------------------------
storage = WikiStorage(PAGES_DIR)
markdown_parser = SimpleMarkdown()

# create the default first page if it doesn't exist
if not storage.page_exists(DEFAULT_PAGE_NAME):
    storage.write_page(DEFAULT_PAGE_NAME, DEFAULT_PAGE_CONTENT)


# --- Helper functions -------------------------------------------------------

def _url_decode(value: str) -> str:
    """Decode URL-encoded form values (spaces, percent escapes)."""

    if not value:
        return value

    result_chars = []
    index = 0
    length = len(value)
    while index < length:
        char = value[index]
        if char == "+":
            result_chars.append(" ")
            index += 1
        elif char == "%" and index + 2 < length:
            hex_value = value[index + 1 : index + 3]
            try:
                result_chars.append(chr(int(hex_value, 16)))
                index += 3
            except ValueError:
                result_chars.append(char)
                index += 1
        else:
            result_chars.append(char)
            index += 1

    return "".join(result_chars)


def _url_encode(value: str, safe: str = "/") -> str:
    """Encode URL values for redirects, keeping safe characters unescaped."""

    if not value:
        return value

    safe_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~" + safe)
    encoded = []
    for char in value:
        if char in safe_chars:
            encoded.append(char)
        else:
            encoded.append(f"%{ord(char):02X}")

    return "".join(encoded)


def _load_auth_entries():
    """Load authentication entries from the configured data file.
    Decode both single object and list of objects syntax."""

    if not WIKI_AUTH_DATA_FILE:
        return [], "WIKI_AUTH_DATA_FILE is not configured."

    try:
        with open(WIKI_AUTH_DATA_FILE, "r") as auth_file:
            data = json.load(auth_file)
    except OSError as exc:
        return [], f"Unable to read auth data file: {exc}"
    except ValueError:
        return [], "Auth data file is not valid JSON."

    if isinstance(data, dict):
        entries = [data]
    elif isinstance(data, list):
        entries = [entry for entry in data if isinstance(entry, dict)]
    else:
        entries = []

    return entries, ""


def _is_authenticated(request):
    """Return True if authentication is disabled or token is valid."""

    if not WIKI_AUTH_DATA_FILE:
        return True

    token = request.cookies.get("wiki_token", "")
    return token in valid_session_tokens

# --- Routes -----------------------------------------------------------------

@server.route("/")
def homepage(request):
    """Render the configured default wiki page as the home route."""

    page_name = DEFAULT_PAGE_NAME
    context = {"wiki_title": WIKI_TITLE, "page_name": page_name}
    if storage.page_exists(page_name):
        markdown_content = storage.read_page(page_name) or ""
        context["html_content"] = markdown_parser.to_html(markdown_content)
        template_name = "view_page_exists.html"
    else:
        template_name = "view_page_missing.html"

    body = render_template(f"{TEMPLATES_DIR}/{template_name}", context=context)
    return Response(request, body, content_type="text/html")


@server.route("/list")
def list_pages(request):
    """Return the page listing."""

    pages = storage.list_pages()
    context = {
        "wiki_title": WIKI_TITLE,
        "page_count": len(pages),
        "pages": pages,
        "has_pages": bool(pages),
    }
    body = render_template(f"{TEMPLATES_DIR}/list_pages.html", context=context)
    return Response(request, body, content_type="text/html")


@server.route("/credentials")
def credentials_form(request):
    """Render the credential hash generator form."""

    context = {
        "wiki_title": WIKI_TITLE,
        "error_message": "",
        "response_json": "",
        "username": "",
    }
    body = render_template(f"{TEMPLATES_DIR}/credentials.html", context=context)
    return Response(request, body, content_type="text/html")


@server.route("/credentials", POST)
def credentials_hash(request):
    """Hash a password with the configured salt and show the JSON output."""

    form = request.form_data
    username = (form.get("username", "") or "").strip()
    password = (form.get("password", "") or "").strip()

    error_message = ""
    response_json = ""

    if not username or not password:
        error_message = "Username and password are required."
    else:
        input_data = f"{password}{PASSWORD_SALT}".encode("utf-8")
        password_hash = hashlib.new("sha256", input_data).digest().hex()
        response_json = json.dumps(
            {"username": username, "password_hash": password_hash}
        )

    context = {
        "wiki_title": WIKI_TITLE,
        "error_message": error_message,
        "response_json": response_json,
        "username": username,
    }
    body = render_template(f"{TEMPLATES_DIR}/credentials.html", context=context)
    return Response(request, body, content_type="text/html")


@server.route("/login")
def login_form(request):
    """Render the login form."""

    redirect_to = _url_decode(request.query_params.get("redirect_to", "/"))
    context = {
        "wiki_title": WIKI_TITLE,
        "error_message": "",
        "info_message": "",
        "username": "",
        "redirect_to": redirect_to,
    }
    body = render_template(f"{TEMPLATES_DIR}/login.html", context=context)
    return Response(request, body, content_type="text/html")


@server.route("/login", POST)
def login_submit(request):
    """Validate credentials and set session token auth cookie."""

    # pylint: disable=too-many-locals
    form = request.form_data
    username = (form.get("username", "") or "").strip()
    password = (form.get("password", "") or "").strip()

    redirect_to = (form.get("redirect_to", "") or "").strip() or "/"
    redirect_to = _url_decode(redirect_to)
    error_message = ""
    info_message = ""
    response_cookies = {}

    if not username or not password:
        error_message = "Username and password are required."
    else:
        entries, load_error = _load_auth_entries()
        if load_error:
            error_message = load_error
        else:
            matching_entry = None
            for entry in entries:
                if entry.get("username") == username:
                    matching_entry = entry
                    break

            # username not found
            if not matching_entry:
                error_message = "Invalid username or password."
            else:
                input_data = f"{password}{PASSWORD_SALT}".encode("utf-8")
                password_hash = hashlib.new("sha256", input_data).digest().hex()

                # username found, but incorrect password
                if password_hash != matching_entry.get("password_hash"):
                    error_message = "Invalid username or password."
                else:
                    # username and password correct
                    random_bytes = os.urandom(12)
                    random_str = "".join(
                        RANDOM_ALPHABET[byte % len(RANDOM_ALPHABET)] for byte in random_bytes
                    )

                    # combine password_hash + server secret_key + random str
                    token_input_data = (f"{password_hash}:)"
                                        f"{WIKI_AUTH_SECRET_KEY}=D"
                                        f"{random_str}").encode("utf-8")

                    # session token will be the hash of above str
                    token = hashlib.new("sha256", token_input_data).digest().hex()
                    valid_session_tokens.append(token)

                    response_cookies = {"wiki_token": token}
                    info_message = "Login successful."

    # if successful login, redirect to specified page
    if not error_message and response_cookies:
        redirect_target = _url_encode(redirect_to, safe="/")
        return Redirect(request, redirect_target, cookies=response_cookies)

    # unsuccessful login return to login page with error message
    context = {
        "wiki_title": WIKI_TITLE,
        "error_message": error_message,
        "info_message": info_message,
        "username": username,
        "redirect_to": redirect_to,
    }
    body = render_template(f"{TEMPLATES_DIR}/login.html", context=context)
    return Response(
        request,
        body,
        content_type="text/html",
        cookies=response_cookies,
    )


@server.route("/new")
def new_page(request):
    """Render the "New Page" form."""

    if not _is_authenticated(request):
        return Redirect(request, "/login?redirect_to=new")

    context = {"wiki_title": WIKI_TITLE, "error_message": ""}
    body = render_template(f"{TEMPLATES_DIR}/new_page.html", context=context)
    return Response(request, body, content_type="text/html")


@server.route("/create", POST)
def create_page(request):
    """Accept a page name and redirect to the editor."""

    if not _is_authenticated(request):
        return Redirect(request, "/login?redirect_to=new")

    form = request.form_data
    page_name = _url_decode((form.get("page_name", "") or "")).strip()
    print(f"page_name: {page_name}")
    if not page_name:
        error_message = "Page name cannot be empty."
        body = render_template(
            f"{TEMPLATES_DIR}/new_page.html",
            context={"wiki_title": WIKI_TITLE, "error_message": error_message},
        )
        return Response(request, body, content_type="text/html")

    if storage.page_exists(page_name):
        error_message = f"Page '{page_name}' already exists."
        body = render_template(
            f"{TEMPLATES_DIR}/new_page.html",
            context={"wiki_title": WIKI_TITLE, "error_message": error_message},
        )
        return Response(request, body, content_type="text/html")

    return Redirect(request, f"/edit/{page_name}")


@server.route("/edit/<page_name>")
def edit_page(request, page_name):
    """Render the markdown editor for the requested page."""

    if not _is_authenticated(request):
        return Redirect(request, f"/login?redirect_to=edit/{page_name}")

    page_name = _url_decode(page_name)

    existing_content = storage.read_page(page_name)
    if existing_content is None:
        existing_content = f"# {page_name}\n\nWrite your content here..."

    context = {
        "wiki_title": WIKI_TITLE,
        "page_name": page_name,
        "markdown_content": existing_content,
    }
    body = render_template(f"{TEMPLATES_DIR}/edit_page.html", context=context)
    return Response(request, body, content_type="text/html")


@server.route("/save/<page_name>", POST)
def save_page(request, page_name):
    """Persist edits and redirect back to the page view."""

    if not _is_authenticated(request):
        return Redirect(request, f"/login?redirect_to=edit/{page_name}")

    page_name = _url_decode(page_name)

    raw_body = request.body.decode("utf-8")
    prefix = "content="
    if raw_body.startswith(prefix):
        content = raw_body[len(prefix):]
    else:
        content = raw_body

    if content.endswith("\r\n"):
        content = content[:-2]
    elif content.endswith("\n"):
        content = content[:-1]

    storage.write_page(page_name, content)
    return Redirect(request, f"/wiki/{page_name}")



@server.route("/delete/<page_name>", POST)
def delete_page(request, page_name):
    """Delete the requested page and redirect back to the list."""

    if not _is_authenticated(request):
        return Redirect(request, f"/login?redirect_to=wiki/{page_name}")

    page_name = _url_decode(page_name)

    storage.delete_page(page_name)
    return Redirect(request, "/list")


@server.route("/wiki/<page_name>")
def view_page(request, page_name):
    """Render an existing page or the "missing" CTA."""
    page_name = _url_decode(page_name)
    context = {"wiki_title": WIKI_TITLE, "page_name": page_name}
    if storage.page_exists(page_name):
        markdown_content = storage.read_page(page_name) or ""
        context["html_content"] = markdown_parser.to_html(markdown_content)
        template_name = "view_page_exists.html"
    else:
        template_name = "view_page_missing.html"

    body = render_template(f"{TEMPLATES_DIR}/{template_name}", context=context)
    return Response(request, body, content_type="text/html")


# --- Application startup ----------------------------------------------------

def main() -> None:
    """Start the HTTP server."""

    print("Starting CircuitPython TinyWiki server")
    print(f"Listening on http://{radio.ipv4_address}:{SERVER_PORT}")
    try:
        server.serve_forever(str(radio.ipv4_address), SERVER_PORT)
    except KeyboardInterrupt:
        print("Shutting down TinyWiki server...")


if __name__ == "__main__":
    main()
