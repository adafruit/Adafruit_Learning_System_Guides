Fonts are not checked in.

Download these from the public domain Misc-Fixed family, trim them to
printable ASCII (0x20 through 0x7E inclusive), and convert to PCF with
https://adafruit.github.io/web-bdftopcf/

  9x18B.pcf    newest message, short
  7x14B.pcf    newest message, long
  7x14.pcf     older messages
  6x13B.pcf    sender names and header readings
  6x10.pcf     status bar

Trimming gotchas, all of which fail silently:

  * Keep the space glyph (ENCODING 32). Without it words run together.
  * Keep digits and punctuation. "3pm." rendering as "pm" is worse
    than an error.
  * Keep capital M. adafruit_display_text uses it to work out line
    height and raises AttributeError without it.
