from adafruit_hid.keycode import Keycode
from adafruit_hid.consumer_control_code import ConsumerControlCode

MEDIA = 1
KEY = 2
STRING = 3
KEY_PRESS = 4
KEY_RELEASE = 5

touch_deck_config = {
    "layers": [
        {
            "name": "Youtube Controls",
            "shortcuts": [
                {
                    "label": "Play",
                    "icon": "touch_deck_icons/pr_play.bmp",
                    "actions": (KEY, [Keycode.K]),
                },
                {
                    "label": "Pause",
                    "icon": "touch_deck_icons/pr_pause.bmp",
                    "actions": (KEY, [Keycode.K]),
                },
                {
                    "label": "Rewind",
                    "icon": "touch_deck_icons/pr_rewind.bmp",
                    "actions": (KEY, [Keycode.LEFT_ARROW]),
                },
                {
                    "label": "FastForward",
                    "icon": "touch_deck_icons/pr_ffwd.bmp",
                    "actions": (KEY, [Keycode.RIGHT_ARROW]),
                },
                {
                    "label": "Previous",
                    "icon": "touch_deck_icons/pr_previous.bmp",
                    "actions": (KEY, [Keycode.RIGHT_SHIFT, Keycode.P]),
                },
                {
                    "label": "Next",
                    "icon": "touch_deck_icons/pr_next.bmp",
                    "actions": (KEY, [Keycode.RIGHT_SHIFT, Keycode.N]),
                },
                {
                    "label": "Vol -",
                    "icon": "touch_deck_icons/pr_voldown.bmp",
                    "actions": (MEDIA, ConsumerControlCode.VOLUME_DECREMENT),
                },
                {
                    "label": "Vol +",
                    "icon": "touch_deck_icons/pr_volup.bmp",
                    "actions": (MEDIA, ConsumerControlCode.VOLUME_INCREMENT),
                },
                {
                    "label": "Fullscreen",
                    "icon": "touch_deck_icons/pr_fullscreen.bmp",
                    "actions": (KEY, [Keycode.F]),
                },
                {
                    "label": "Slow",
                    "icon": "touch_deck_icons/pr_slow.bmp",
                    "actions": (KEY, [Keycode.RIGHT_SHIFT, Keycode.COMMA]),
                },
                {
                    "label": "Fast",
                    "icon": "touch_deck_icons/pr_fast.bmp",
                    "actions": (KEY, [Keycode.RIGHT_SHIFT, Keycode.PERIOD]),
                },
                {
                    "label": "Mute",
                    "icon": "touch_deck_icons/pr_mute.bmp",
                    "actions": (KEY, [Keycode.M]),
                },
            ],
        },
        {
            "name": "Discord",
            "shortcuts": [
                {
                    "label": "Blinka",
                    "icon": "touch_deck_icons/af_blinka.bmp",
                    "actions": (STRING, ":blinka:"),
                },
                {
                    "label": "Adabot",
                    "icon": "touch_deck_icons/af_adabot.bmp",
                    "actions": (STRING, ":adabot:"),
                },
                {
                    "label": "Billie",
                    "icon": "touch_deck_icons/af_billie.bmp",
                    "actions": (STRING, ":billie:"),
                },
                {
                    "label": "Cappy",
                    "icon": "touch_deck_icons/af_cappy.bmp",
                    "actions": (STRING, ":cappy:"),
                },
                {
                    "label": "Connie",
                    "icon": "touch_deck_icons/af_connie.bmp",
                    "actions": (STRING, ":connie:"),
                },
                {
                    "label": "Gus",
                    "icon": "touch_deck_icons/af_gus.bmp",
                    "actions": (STRING, ":gus:"),
                },
                {
                    "label": "Hans",
                    "icon": "touch_deck_icons/af_hans.bmp",
                    "actions": (STRING, ":hans:"),
                },
                {
                    "label": "Mho",
                    "icon": "touch_deck_icons/af_mho.bmp",
                    "actions": (STRING, ":mho:"),
                },
                {
                    "label": "Minerva",
                    "icon": "touch_deck_icons/af_minerva.bmp",
                    "actions": (STRING, ":minerva:"),
                },
                {
                    "label": "NeoTrellis",
                    "icon": "touch_deck_icons/af_neotrellis.bmp",
                    "actions": (STRING, ":neotrellis:"),
                },
                {
                    "label": "Ruby",
                    "icon": "touch_deck_icons/af_ruby.bmp",
                    "actions": (STRING, ":ruby:"),
                },
                {
                    "label": "Sparky",
                    "icon": "touch_deck_icons/af_sparky.bmp",
                    "actions": (STRING, ":sparky:"),
                },
            ],
        },
        {
            "name": "Symbols",
            "shortcuts": [
                {
                    "label": "Infinity",  # ∞
                    "icon": "touch_deck_icons/sy_infinity.bmp",
                    "actions": (KEY, [Keycode.ALT, Keycode.FIVE]),
                },
                {
                    "label": "Degree",  # º
                    "icon": "touch_deck_icons/sy_degree.bmp",
                    "actions": (KEY, [Keycode.ALT, Keycode.ZERO]),
                },
                {
                    "label": "Pi",  # π
                    "icon": "touch_deck_icons/sy_pi.bmp",
                    "actions": (KEY, [Keycode.ALT, Keycode.P]),
                },
                {
                    "label": "Sigma",  # ∑
                    "icon": "touch_deck_icons/sy_sigma.bmp",
                    "actions": (KEY, [Keycode.ALT, Keycode.W]),
                },
                {
                    "label": "Partial diff",  #
                    "icon": "touch_deck_icons/sy_pdiff.bmp",
                    "actions": (KEY, [Keycode.ALT, Keycode.D]),
                },
                {
                    "label": "Increment",  # ∆
                    "icon": "touch_deck_icons/sy_increment.bmp",
                    "actions": (KEY, [Keycode.ALT, Keycode.J]),
                },
                {
                    "label": "Omega",  # Ω
                    "icon": "touch_deck_icons/sy_omega.bmp",
                    "actions": (KEY, [Keycode.ALT, Keycode.Z]),
                },
                {
                    "label": "Mu",  # µ
                    "icon": "touch_deck_icons/sy_micro.bmp",
                    "actions": (KEY, [Keycode.ALT, Keycode.M]),
                },
                {
                    "label": "Rad O",  # Ø
                    "icon": "touch_deck_icons/sy_rado.bmp",
                    "actions": (KEY, [Keycode.ALT, Keycode.SHIFT, Keycode.O]),
                },
                {
                    "label": "Square root",  # √
                    "icon": "touch_deck_icons/sy_sqrrt.bmp",
                    "actions": (KEY, [Keycode.ALT, Keycode.V]),
                },
                {
                    "label": "Approx",  # ≈
                    "icon": "touch_deck_icons/sy_approx.bmp",
                    "actions": (KEY, [Keycode.ALT, Keycode.X]),
                },
                {
                    "label": "Plus minus",  # ±
                    "icon": "touch_deck_icons/sy_plusminus.bmp",
                    "actions": (KEY, [Keycode.ALT, Keycode.SHIFT, Keycode.EQUALS]),
                },
            ],
        },
    ]
}
