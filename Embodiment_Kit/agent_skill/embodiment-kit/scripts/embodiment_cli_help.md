# Embodiment Kit — Command Capabilities

This document describes the commands exposed by `embodiment_cli.py`.

Every command returns an **ack** message containing the original command, the current sensor readings, and the current output state. Some commands also attach a `proof` object inside `metadata` that records measurements taken before and during the action, which can be used to confirm the action actually had a physical effect.

---

## Display capabilities

### `show_happy_face`
Renders a preset "happy" face on the display, composed of eyebrows, eyes, blush, and a mouth layered on a solid background.

Arguments:
- `background_color` (int, optional) — Background fill color as a 24-bit RGB integer. Defaults to `0x88ddff`.

### `show_custom_face`
Renders a face built from caller-supplied layer choices, letting the caller pick its own combination of eyebrows, eyes, blush, and mouth.

Arguments:
- `options` (object, optional) — A dict whose keys are any of `eyebrows`, `eyes`, `blush`, `mouth`. Each value is a `[filename, y_offset]` pair, e.g. `["eyebrow_happy.png", -40]`. Defaults to the happy-face preset. See `list_custom_face_options` for valid filenames.
- `background_color` (int, optional) — Background color. Defaults to `0x88ddff`.

### `list_custom_face_options`
Returns the filenames available for each face layer, so the caller knows which assets it can mix and match in a subsequent `show_custom_face` call.

Response contains:
- `eyes_options`
- `blush_options`
- `mouth_options`
- `eyebrow_option`

### `show_message`
Hides the face and displays a text message on screen.

Arguments:
- `message` (string, optional) — Text to display. Defaults to an empty string. Display space is limited to 5 rows with 19 characters per row.

### `show_prompt`
Displays a prompt message and waits for the user to press a hardware button, returning which one was pressed (or that it timed out).

Arguments:
- `message` (string, optional) — Prompt text. Defaults to `"Press a button"`. Display space is limited to 5 rows with 19 characters per row. Ideally should contain newlines to split options example: `message="Agree?\n0) Yes\n1) No\n2) Maybe"`
- `timeout` (number, optional) — Seconds to wait. Defaults to `20`.

Response contains:
- `prompt_result` — One of `"btn D0 pressed"`, `"btn D1 pressed"`, `"btn D2 pressed"`, or `"timed out"`. On a successful press the display shows `"Thank you"`, on a time out it shows `"Prompt timed out"`.

---

## Sound capabilities

### `play_tone`
Plays a tone through the piezo buzzer for a set duration, then silences it.

Arguments:
- `frequency` (int, optional) — Tone frequency in Hz. Defaults to `440`.
- `duty_cycle` (int, optional) — PWM duty cycle. Defaults to `2**15` (≈50%).
- `duration` (number, optional) — Length in seconds. Defaults to `0.5`. Maximum allowed value is `3`.

Proof contains:
- `idle_sound_level` — Microphone RMS before the tone.
- `playing_sound_level` — Microphone RMS while playing the tone. RMS is expected to be higher when playing sound.

---

## Light capabilities

### `lights_on`
Turns on the NeoPixel strip at a given color and brightness.

Arguments:
- `color` (int, optional) — 24-bit RGB color. Defaults to `0xff00ff` (magenta).
- `brightness` (float, optional) — `0.0`–`1.0`. Defaults to the strip's current brightness.

Proof contains:
- `idle_lux_level` — Ambient lux before turning on.
- `on_lux_level` — Lux after turning on. Lux is expected to be higher when the lights are off.

### `lights_off`
Turns off the NeoPixel strip (fills with black).

Proof contains:
- `idle_lux_level` — Lux before turning off.
- `off_lux_level` — Lux after turning off. Lux is expected to be lower when the lights are off.

---

## Haptic capabilities

### `vibrate`
Runs the vibration motor for ~0.75 seconds total (0.25s settle, 0.5s sustained).

Proof contains:
- `idle_z_acceleration` — Average Z-axis acceleration before vibrating.
- `vibrating_z_acceleration` — Average Z-axis acceleration just after the motor starts, used to confirm the vibration was physically felt by the accelerometer. Z acceceration is expected to decrease during vibration.

---

## Sensor data (always included)

Every ack contains the current readings from all configured sensors under `state.sensors`. Depending on what's attached, this can include:

- `temperature`
- `pressure`
- `humidity`
- `lux` — Ambient light level.
- `accelerometer` — A string of the form `"x=<x>, y=<y>, z=<z>"` averaged over 10 samples.
- `pdm_mic` — Normalized RMS magnitude of recent audio samples.

Sensors may attach units to their values when configured to do so.

### `get_data`

Returns the standard ack response which includes sensor data.

## Output state (always included)

Every ack also contains `state.outputs` describing the current state of the actuators:

- `neopixels` — `{ "color": <current color>, "brightness": <current brightness> }`
- `display` — A short string describing what the screen is currently showing, e.g. `"face: happy_face"`, `"face: custom_face"`, or `"message: <text>"`.

