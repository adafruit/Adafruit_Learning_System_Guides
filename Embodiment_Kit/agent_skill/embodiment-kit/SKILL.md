---
name: embodiment-kit
description: Interact with a physical embodiment kit microcontroller located in the user's room. Send commands to control a display (faces, messages, prompts), NeoPixel lights, a piezo buzzer, and a vibration motor — and to read sensors (temperature, humidity, pressure, ambient lux, microphone, accelerometer). Use to answer questions about the physical environment and to express status, get the human's attention, or communicate visually/audibly/haptically in the room.
metadata:
  version: "1.1"
  requires: ["python3", "either (ADAFRUIT_AIO_USERNAME + ADAFRUIT_AIO_KEY env vars) or (EMBODIMENT_KIT_HOST env var)"]
---

# Embodiment Kit Skill

This skill lets you read sensors from and drive actuators on a physical embodiment kit microcontroller located in the user's room. Every command round-trips and returns a JSON ack containing the current sensor readings and output state — and, for actuator commands, a `proof` block with before/after sensor readings that confirm the action had a physical effect.

## When to Use This Skill

Use this skill when you need to:

- **Sense the room**: answer questions about the current temperature, humidity, pressure, ambient light, sound level, or device orientation.
- **Express into the room**: signal status, completion, attention, or mood using the display, lights, buzzer, or vibration motor.
- **Interact with the human**: display a message they should read, or pose a multiple-choice question and wait for a button press.
- **Verify physical effects**: confirm an actuator actually fired by reading the `proof` block in the ack.

Choose actuators thoughtfully — these produce real light, sound, and motion in the human's room. Avoid firing them gratuitously or when the human may be sleeping/focused unless they've asked for it.

## Requirements

- Python virtual environment with `requests` installed.
- If using the Adafruit IO transport (see below), also need installed:
  - `adafruit-circuitpython-adafruitio`
  - `adafruit-circuitpython-connectionmanager`
  - `adafruit-circuitpython-minimqtt`
- One of the two transports below must be configured via environment variables.
- CLI script at `<skills_directory>/embodiment-kit/scripts/embodiment_cli.py`.

### Transports

The CLI supports two ways of reaching the device. Set one (the CLI prefers HTTP when both are present):

- **Direct HTTP (recommended for same-network use)**: set `EMBODIMENT_KIT_HOST` to the device's URL or hostname, e.g. `http://192.168.1.189:5000` or `embodiment.local:5000`. A scheme is optional; `http://` is assumed if missing. Port `5000` is default. The CLI POSTs the command JSON to `<host>/embodiment_kit` and reads the ack from the HTTP response — no MQTT broker or Adafruit account needed. This is the lowest-latency option and works fully offline from the public internet.
- **Adafruit IO MQTT (for remote / cross-network use)**: set both `ADAFRUIT_AIO_USERNAME` and `ADAFRUIT_AIO_KEY`. The CLI publishes the command on the `embodiment.client-to-mcu` feed and waits for the ack on `embodiment.mcu-to-client`. Use this when you cannot reach the device directly on the local network.

If neither transport's env vars are set, the CLI exits with an error before sending anything.

## How to Run a Command

General form:

```bash
python <skills_directory>/embodiment-kit/scripts/embodiment_cli.py <command> [key=value ...] [-t TIMEOUT] [-q]
```

- `key=value` arguments are parsed as JSON when possible. Integers like `0xff8800` are parsed as hex. Strings with spaces should be quoted at the shell level (`message="Hello world"`).
- `-q` / `--quiet` suppresses connection logging on stderr, leaving stdout as pure JSON suitable for piping into `jq` or `json.loads`.
- Default timeout is 10s (22s for `show_prompt`). Override with `-t SECONDS`.
- `--commandlist` prints the full command reference from `embodiment_cli_help.md`.

Every successful response is a single line of JSON on stdout, parseable directly:

```json
{
  "state": {
    "sensors": { "...": "current readings" },
    "outputs": { "neopixels": {}, "display": "..." }
  },
  "metadata": { "type": "ack", "proof": {} },
  "command": { "name": "...", "uuid": "...", "arguments": {} }
}
```

The `metadata.proof` field is only present on actuator commands. To consume the output programmatically, pipe through `jq` or read it with `json.loads`:

```bash
python embodiment_cli.py get_data -q | jq '.state.sensors.temperature'
python embodiment_cli.py get_data -q | python -c "import sys, json; print(json.load(sys.stdin)['state']['sensors']['temperature'])"
```

## Sensors (always returned in every ack)

Under `state.sensors`:

- `temperature` — degrees C
- `humidity` — percent
- `pressure` — hPa
- `lux` — ambient light
- `pdm_mic` — normalized RMS sound magnitude
- `accelerometer` — string `"x=<x>, y=<y>, z=<z> G"`, averaged over 10 samples. A device sitting flat reads roughly `z≈9.8`.

### `get_data`
Returns the standard ack with no side effects. Use to answer questions about the room's current state.

```bash
python embodiment_cli.py get_data
```

## Display Face Commands

### Preset Faces
- `show_happy_face`
- `show_sad_face`
- `show_angry_face`
- `show_confused_face`
- `show_sleepy_face`

Shows the specified preset face. Optional `background_color` (24-bit RGB int, default `0x88ddff`).

```bash
python embodiment_cli.py show_happy_face
python embodiment_cli.py show_happy_face background_color=0xffcc00
python embodiment_cli.py show_sleepy_face
python embodiment_cli.py show_sleepy_face background_color=0xffcc00
```

### `show_custom_face`
Build a face from layer choices. First call `list_custom_face_options` to see valid filenames for each layer (`eyebrows`, `eyes`, `blush`, `mouth`). Each layer is a `[filename, y_offset]` pair. The y_offset is relative to the center of the screen. Negative values move the sprite up, positive values move it down. The display height is only 135px, offset values should be within the range -50 to 50 in order to keep them visible.

```bash
python embodiment_cli.py list_custom_face_options
python embodiment_cli.py show_custom_face options='{"eyes":["round_eyes_happy.png",-20],"mouth":["mouth_smiling.png",60]}'
```

## Display Message Commands

### `show_message` — important formatting rules
Hides the face and displays text.

**Display constraints — the screen fits at most 5 rows of 19 characters per row.** Plan messages around this:

- Keep each line ≤ 19 characters. Longer lines will be cut off.
- Use at most 5 lines total. Additional lines will not render.
- Use `\n` (literal backslash-n in the shell argument) to break lines manually — do NOT rely on auto-wrapping.
- Prefer short, scannable phrasing over paragraphs. Abbreviate when needed.

```bash
python embodiment_cli.py show_message message="Build passed\nReady to deploy"
python embodiment_cli.py show_message message="Tests: 42/42 OK\nLint: clean\nCoverage: 87%"
```

Bad (too long per line, will be truncated):

```bash
# DON'T: 23 chars on line 1, no newlines — will overflow / wrap unpredictably
python embodiment_cli.py show_message message="The deployment finished successfully a moment ago"
```

### `show_prompt` — important formatting rules
Displays a message and waits for the human to press one of three hardware buttons (`D0`, `D1`, `D2`) or time out.

**Same display constraints as `show_message`: 5 rows × 19 chars.** Use them to your advantage by structuring the prompt as a question followed by labeled options on their own lines.

Recommended structure: question on line 1, then up to three options on the remaining lines, each labeled with the button index that selects it (`0)`, `1)`, `2)`):

```bash
python embodiment_cli.py show_prompt message="Deploy now?\n0) Yes\n1) No\n2) Later" timeout=30
python embodiment_cli.py show_prompt message="Mood?\n0) Good\n1) OK\n2) Tired"
```

Arguments:
- `message` (string, default `"Press a button"`).
- `timeout` (seconds, default `20`). If you set this, the CLI's own ack-timeout (`-t`) is auto-bumped to `timeout + 2`. If you override both, `-t` must be strictly greater than `timeout`.

The ack's `command.response.prompt_result` will be one of:
- `"btn D0 pressed"` → option 0 chosen
- `"btn D1 pressed"` → option 1 chosen
- `"btn D2 pressed"` → option 2 chosen
- `"timed out"` → no press before timeout

Map the button → option by the labels you wrote in the message. After a press the display briefly shows `"Thank you"`; on timeout it shows `"Prompt timed out"`.

Tips:
- Only three buttons exist — never offer more than three options.
- Keep option labels very short (e.g. `Yes`, `No`, `Later`) so the `N) label` line fits in 19 chars.
- If asking a yes/no question, you can use 2 options and leave the third button unused.
- Pick a `timeout` long enough that the human can read and decide, but not so long that the prompt blocks the conversation indefinitely (20–60s is usually right).

## Light Commands (NeoPixel strip)

### `lights_on`
Turns on the strip. `color` is a 24-bit RGB int (default magenta `0xff00ff`). `brightness` is 0.0–1.0 (default is the current brightness).

```bash
python embodiment_cli.py lights_on color=0x00ff00 brightness=0.4
```

Proof block: `idle_lux_level` vs `on_lux_level` (lux should rise).

### `lights_off`
Fills the strip with black.

```bash
python embodiment_cli.py lights_off
```

Proof block: `idle_lux_level` vs `off_lux_level` (lux should drop).

## Sound Command

### `play_tone`
Plays a tone on the piezo buzzer.

- `frequency` (Hz, default `440`)
- `duty_cycle` (default `2**15` ≈ 50%)
- `duration` (seconds, default `0.5`, **max `3`**)

```bash
python embodiment_cli.py play_tone frequency=523 duration=0.8
```

Proof block: `idle_sound_level` vs `playing_sound_level` (mic RMS should rise).

## Haptic Command

### `vibrate`
Runs the vibration motor for ~0.75 s. No arguments.

```bash
python embodiment_cli.py vibrate
```

Proof block: `idle_z_acceleration` vs `vibrating_z_acceleration` (Z-axis acceleration usually decreases during vibration).

## Patterns for Expressing Status

Some useful patterns for using actuators meaningfully:

- **Task complete, low-key**: `show_message message="Done"` or a brief `play_tone frequency=880 duration=0.2`.
- **Task complete, celebratory**: `show_happy_face` + `lights_on color=0x00ff00 brightness=0.5`, then `lights_off` a few seconds later.
- **Need attention**: `vibrate` + `show_message` describing what you need.
- **Error / warning**: `lights_on color=0xff0000 brightness=0.7` + `show_message message="Build failed\nsee terminal"`.
- **Ask the human a question**: `show_prompt` with a short question and 2–3 labeled options.
- **Ambient status indicator**: `lights_on` with a color encoding state (e.g. blue=working, green=done, red=blocked), turn off when state ends.

Always pair attention-grabbing actuators (sound, vibration, bright lights) with a display message that explains *why* you grabbed attention, so the human knows what to do next. Clean up after yourself — turn lights off when the signal is no longer relevant.

## Reference Files

- `embodiment_cli.py` — the CLI itself.
- `embodiment_cli_help.md` — the canonical command reference (also printable via `--commandlist`).
- `embodiment_message_handler.py`, `code_mcu_mqtt.py`, `code_mcu_httpserver.py` — MCU-side firmware (for context, not invoked from this skill).
