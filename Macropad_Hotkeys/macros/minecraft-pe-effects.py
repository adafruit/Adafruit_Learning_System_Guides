# MACROPAD Hotkeys example: Minecraft Effects (Creative) for Bedrock Edition

# NOTE: There appears to be a line length limit. Exceeding that limit appears
#       to result in silent failure.  Therefore, the key sequences are split
#       across multiple lines.

from adafruit_hid.keycode import Keycode # REQUIRED if using Keycode.* values

# See https://minecraft.fandom.com/wiki/Effect

DELAY_AFTER_SLASH   = 0.80 # required so minecraft has time to bring up command screen
DELAY_BEFORE_RETURN = 0.10 # give minecraft time to show all the keys pressed...

app = {                                 # REQUIRED dict, must be named 'app'
    'name' : 'Minecraft PE (effect)',   # Application name
    #
    # /effect <player: target> <effect: Effect>
    #         [seconds: int] [amplifier: int] [hideParticles: Boolean]
    #
    'macros' : [                        # List of button macros...
        # COLOR    LABEL    KEY SEQUENCE
        # 1st row ----------
        (0x002000, 'speed',  [
            '/', DELAY_AFTER_SLASH,
            'effect @s speed           999999999 1 true',
            DELAY_BEFORE_RETURN, Keycode.RETURN, -Keycode.RETURN]),
        (0x002000, 'str',    [
            '/', DELAY_AFTER_SLASH,
            'effect @s strength        999999999 1 true',
            DELAY_BEFORE_RETURN, Keycode.RETURN, -Keycode.RETURN]),
        (0x002000, 'haste',  [
            '/', DELAY_AFTER_SLASH,
            'effect @s haste           999999999 1 true',
            DELAY_BEFORE_RETURN, Keycode.RETURN, -Keycode.RETURN]),
        # 2nd row ----------
        (0x002000, 'jump',   [
            '/', DELAY_AFTER_SLASH,
            'effect @s jump_boost      999999999 1 true',
            DELAY_BEFORE_RETURN, Keycode.RETURN, -Keycode.RETURN]),
        (0x000030, 'breath', [
            '/', DELAY_AFTER_SLASH,
            'effect @s water_breathing 999999999 0 true',
            DELAY_BEFORE_RETURN, Keycode.RETURN, -Keycode.RETURN]),
        (0x202020, 'darkv',  [
            '/', DELAY_AFTER_SLASH,
            'effect @s night_vision    999999999 0 true',
            DELAY_BEFORE_RETURN, Keycode.RETURN, -Keycode.RETURN]),
        # 3rd row ----------
        (0x300000, 'health', [
            '/', DELAY_AFTER_SLASH,
            'effect @s health_boost    999999999 4 true',
            DELAY_BEFORE_RETURN, Keycode.RETURN, -Keycode.RETURN]),
        (0x300000, 'regen',  [
            '/', DELAY_AFTER_SLASH,
            'effect @s regeneration    999999999 4 true',
            DELAY_BEFORE_RETURN, Keycode.RETURN, -Keycode.RETURN]),
        (0x002000, 'absorb', [
            '/', DELAY_AFTER_SLASH,
            'effect @s absorption      999999999 3 true',
            DELAY_BEFORE_RETURN, Keycode.RETURN, -Keycode.RETURN]),
        # 4th row ---------
        (0x002000, 'resist', [
            '/', DELAY_AFTER_SLASH,
            'effect @s resistance      999999999 3 true',
            DELAY_BEFORE_RETURN, Keycode.RETURN, -Keycode.RETURN]),
        (0x101010, 'invis',  [
            '/', DELAY_AFTER_SLASH,
            'effect @s invisibility    999999999 0 true',
            DELAY_BEFORE_RETURN, Keycode.RETURN, -Keycode.RETURN]),
        (0x300000, 'fire_r', [
            '/', DELAY_AFTER_SLASH,
            'effect @s fire_resistance 999999999 0 true',
            DELAY_BEFORE_RETURN, Keycode.RETURN, -Keycode.RETURN]),
        # Encoder button --- Remove all status effects....
        (0x000000, '', [
            '/', DELAY_AFTER_SLASH,
            'effect @s clear',
            DELAY_BEFORE_RETURN, Keycode.RETURN, -Keycode.RETURN]),
    ]
}
