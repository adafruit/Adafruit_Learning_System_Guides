# MACROPAD Hotkeys example: Minecraft Effects (Creative) for Bedrock Edition

# NOTE: There appears to be a line length limit. Exceeding that limit appears
#       to result in silent failure.  Therefore, the key sequences are split
#       across multiple lines.

from adafruit_hid.keycode import Keycode # REQUIRED if using Keycode.* values

# See https://minecraft.fandom.com/wiki/Effect

DELAY_AFTER_ESCAPE = 0.05
DELAY_AFTER_COMMAND = 0.10

app = {                              # REQUIRED dict, must be named 'app'
    'name' : 'Minecraft PE (effect)',   # Application name
    #
    # /effect <player: target> <effect: Effect>
    #         [seconds: int] [amplifier: int] [hideParticles: Boolean]
    #
    'macros' : [                     # List of button macros...
        # COLOR    LABEL    KEY SEQUENCE
        # 1st row ----------
        (0x002000, 'speed',  [
            Keycode.ESCAPE, -Keycode.ESCAPE,
            '/effect @s speed           999999999 1 true',
            Keycode.RETURN, -Keycode.RETURN,
            Keycode.ESCAPE, -Keycode.ESCAPE]),
        (0x002000, 'str',    [
            Keycode.ESCAPE, -Keycode.ESCAPE,
            '/effect @s strength        999999999 1 true',
            Keycode.RETURN, -Keycode.RETURN,
            Keycode.ESCAPE, -Keycode.ESCAPE]),
        (0x002000, 'haste',  [
            Keycode.ESCAPE, -Keycode.ESCAPE,
            '/effect @s haste           999999999 1 true',
            Keycode.RETURN, -Keycode.RETURN,
            Keycode.ESCAPE, -Keycode.ESCAPE]),
        # 2nd row ----------
        (0x002000, 'jump',   [
            Keycode.ESCAPE, -Keycode.ESCAPE,
            '/effect @s jump_boost      999999999 1 true',
            Keycode.RETURN, -Keycode.RETURN,
            Keycode.ESCAPE, -Keycode.ESCAPE]),
        (0x000030, 'breath', [
            Keycode.ESCAPE, -Keycode.ESCAPE,
            '/effect @s water_breathing 999999999 0 true',
            Keycode.RETURN, -Keycode.RETURN,
            Keycode.ESCAPE, -Keycode.ESCAPE]),
        (0x202020, 'darkv',  [
            Keycode.ESCAPE, -Keycode.ESCAPE,
            '/effect @s night_vision    999999999 0 true',
            Keycode.RETURN, -Keycode.RETURN,
            Keycode.ESCAPE, -Keycode.ESCAPE]),
        # 3rd row ----------
        (0x300000, 'health', [
            Keycode.ESCAPE, -Keycode.ESCAPE,
            '/effect @s health_boost    999999999 4 true',
            Keycode.RETURN, -Keycode.RETURN,
            Keycode.ESCAPE, -Keycode.ESCAPE]),
        (0x300000, 'regen',  [
            Keycode.ESCAPE, -Keycode.ESCAPE,
            '/effect @s regeneration    999999999 4 true',
            Keycode.RETURN, -Keycode.RETURN,
            Keycode.ESCAPE, -Keycode.ESCAPE]),
        (0x002000, 'absorb', [
            Keycode.ESCAPE, -Keycode.ESCAPE,
            '/effect @s absorption      999999999 3 true',
            Keycode.RETURN, -Keycode.RETURN,
            Keycode.ESCAPE, -Keycode.ESCAPE]),
        # 4th row ---------
        (0x002000, 'resist', [
            Keycode.ESCAPE, -Keycode.ESCAPE,
            '/effect @s resistance      999999999 3 true',
            Keycode.RETURN, -Keycode.RETURN,
            Keycode.ESCAPE, -Keycode.ESCAPE]),
        (0x101010, 'invis',  [
            Keycode.ESCAPE, -Keycode.ESCAPE,
            '/effect @s invisibility    999999999 0 true',
            Keycode.RETURN, -Keycode.RETURN,
            Keycode.ESCAPE, -Keycode.ESCAPE]),
        (0x300000, 'fire_r', [
            Keycode.ESCAPE, -Keycode.ESCAPE,
            '/effect @s fire_resistance 999999999 0 true',
            Keycode.RETURN, -Keycode.RETURN,
            Keycode.ESCAPE, -Keycode.ESCAPE]),
        # Encoder button --- Remove all status effects....
        (0x000000, '', [
            Keycode.ESCAPE, -Keycode.ESCAPE,
            '/effect @s clear',
            Keycode.RETURN, -Keycode.RETURN,
            Keycode.ESCAPE, -Keycode.ESCAPE]),
    ]
}
