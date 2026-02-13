# Welcome to CircuitPython Tiny Wiki

A CircuitPython port of [tiny_wiki for Micropython](https://github.com/kevinmcaleer/tiny_wiki) by Kevin McAleer.
This lightweight Wiki is powered by [Adafruit CircuitPython HTTPServer](https://github.com/adafruit/Adafruit_CircuitPython_HTTPServer) + [Template Engine](https://github.com/adafruit/Adafruit_CircuitPython_TemplateEngine/).
Wiki pages are stored as files on the attached micro SD card. The pages are `.md` files that support a limited set of the markdown syntax.

## Usage

- Use **Edit** to modify the page you are currently viewing.
- Create new articles with **New Page**.
- Provide links to other Wiki pages using `[[AnotherPage]]`.
- Browse everything via **All Pages**.

---

## Configuration

These configuration options available by setting environment variables in the **settings.toml** file.

- `WIKI_TITLE`: The title to show at the top of all pages.
- `WIKI_PAGES_DIR`: The directory to store page files. "/sd/pages" by default. Must be writable.
- `WIKI_SERVER_PORT`: The HTTP port to host the server on. Defaults to 8000
- `WIKI_AUTH_DATA_FILE`: Optional path to JSON file containing valid user(s) authentication details. Defaults to None (auth disabled).
- `WIKI_PASSWORD_SALT`: [Pepper](https://en.wikipedia.org/wiki/Pepper_%28cryptography%29) used when hashing passwords if auth is enabled. You should change it from the default value.
- `WIKI_AUTH_SECRET_KEY`: Key string used when hashing values to derive session tokens if auth is enabled. You should change it from the default value.

---

## Authentication

### **Authentication Warning**

*The authentication system is meant to provide a minimal layer of security to prevent unauthorized editing of Wiki pages. It tries to follow best practices where possible given the constraints of running in CircuitPython on a microcontroller, but should not be considered highly secure. By default all data is stored and transmitted in plain text over HTTP. This Wiki is intended to be a fun demonstration and project, not store sensitive information securely.*

The authentication system is optional, and disabled by default. If enabled it will require logging in with valid credentials in order to create, update, or delete Wiki pages. 
To enable authentication create a JSON file on the CIRCUITPY drive and set the path to it as the value for `WIKI_AUTH_DATA_FILE` environment variable.

For example in **settings.toml**:
``` 
WIKI_AUTH_DATA_FILE="wiki_auth.json"
```

Go to the [Credential Hash](/credentials) page, enter the desired username and password, and click **Generate Hash**.
Copy the resulting username/hash JSON object into the auth data file mentioned above. It can contain either a single entry with one object containing a username and hash, or a list of objects containing usernames and hashes.
Single user example:
```
{"password_hash": "dbd1bdabd1c22032e7cb64217cc9d4bca7242f68bfba46aa0b9418a58138304f", "username": "wiki_user"}
```
Multiple user example:
```
[
  {"password_hash": "3eb1d64cde9d156c852dab00bccf9194932ed6e540a61f2bd53fdf1c03044dac", "username": "wiki_user"},
  {"password_hash": "12cdd16b8cec46aa1defc576342aaef5c0dd0773ba5c8a0c3a726c3ee56cd50f", "username": "test_user"}
]
```
