# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Build CircuitPython audio effect objects from JSON config data.

The JSON describes only the end-user tunable parameters of an effect -- the
things that change how it sounds. The audio format arguments are
a property of the audio chain, not of the preset, so they are supplied by the
caller and ignored if they appear in the JSON.

A single effect is a dict with an ``"effect"`` key naming the type::

    {"effect": "echo", "max_delay_ms": 1000, "delay_ms": 500,
     "decay": 0.5, "mix": 1.0, "freq_shift": false}

Any effect may also carry ``"enabled": false`` to take it out of the chain
without deleting it from the config -- `create_effect_chain` and
`create_effects` skip it entirely. Omitting ``"enabled"`` (or setting it
``true``) builds the effect as normal.

Usage::

    import json
    from config_loader import create_effect, create_effect_chain

    config = json.load(open("/ep2350_circuitpython_config.json"))
    specs = config["presets"][0]["list"]

    chain = create_effect_chain(specs, sample_rate=48000, channel_count=2,
                                buffer_size=1024, source=mic)
    audio.play(chain[-1])

Block inputs
------------

Most tunable parameters are `synthio.BlockInput`, meaning they take a constant
*or* a block that varies over time. Anywhere a block is allowed the JSON may be:

* a number -- ``"mix": 0.6``
* ``null`` -- treated by synthio as 0
* a block object -- ``{"block": "lfo", ...}`` or ``{"block": "math", ...}``
* ``"$name"`` -- a reference to a shared block (see below)

An LFO takes the same keyword arguments as `synthio.LFO`::

    {"block": "lfo", "waveform": "sine", "rate": 0.25,
     "scale": 400, "offset": 600, "phase_offset": 0.0,
     "once": false, "interpolate": true}

``waveform`` is a shape name (``"triangle"``, ``"sine"``, ``"square"``,
``"saw"``/``"ramp_up"``, ``"ramp_down"``), ``{"shape": "sine", "size": 256}``
when the sample count matters, or a literal list of 16-bit signed ints.
Omitting it uses synthio's built-in triangle.

A Math block takes an operation name from `synthio.MathOperation`::

    {"block": "math", "operation": "constrained_lerp",
     "a": 0.1, "b": 0.9, "c": "$handle"}

``rate``/``scale``/``offset``/``phase_offset`` and ``a``/``b``/``c`` are block
inputs themselves, so blocks nest.

Writing the same block object twice builds two independent blocks. To drive
several parameters from one block, name it and refer to it with ``"$name"``.
Names come from a ``"blocks"`` mapping on the preset (or the whole config)::

    {"blocks": {"sweep": {"block": "lfo", "rate": 0.2,
                          "scale": 1200, "offset": 2000}},
     "list": [{"effect": "filter",
               "filter": {"mode": "low_pass", "frequency": "$sweep"}},
              {"effect": "phaser", "frequency": "$sweep", "stages": 8}]}

and from the ``blocks`` argument of `create_effect`, which is how host code
hands the config a value only it can produce -- a knob, say::

    handle = synthio.Math(synthio.MathOperation.SUM, 0.0, 0.0, 0.0)
    chain = create_preset(preset, source=mic, blocks={"handle": handle})
    ...
    handle.a = pot.value / 65535     # in the main loop

Host-supplied blocks win over same-named definitions in the config.
"""

import array
import math

import audiofilters
import synthio

# Audio format arguments. These are set by the caller from the hardware
# configuration, so they are skipped if a config file specifies them.
FORMAT_ARGS = (
    "buffer_size",
    "sample_rate",
    "channel_count",
    "bits_per_sample",
    "samples_signed",
)


# Converters all take (value, name, blocks) so they are interchangeable in the
# parameter tables; only the block-input ones look at `blocks`.
# pylint: disable=unused-argument, too-many-locals


def _int(value, name, blocks=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("{} must be a number".format(name))
    return int(value)


def _float(value, name, blocks=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("{} must be a number".format(name))
    return float(value)


def _bool(value, name, blocks=None):
    if not isinstance(value, bool):
        raise ValueError("{} must be true or false".format(name))
    return value


def _block(value, name, blocks=None):
    """Convert one synthio.BlockInput parameter.

    A number stays a number, ``null`` becomes ``None`` (synthio reads it as 0),
    a dict builds an `synthio.LFO` or `synthio.Math`, and ``"$name"`` looks up a
    shared block.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("{} must be a number, block or block reference".format(name))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        if not value.startswith("$"):
            raise ValueError(
                '{} must be a number, a block, or a "$name" reference'.format(name)
            )
        return _as_blocks(blocks).get(value, name)
    if isinstance(value, dict):
        return _make_block(value, name, _as_blocks(blocks))
    raise ValueError("{} must be a number, block or block reference".format(name))


def _distortion_mode(value, name, blocks=None):
    """Map "clip"/"LOFI"/... to an audiofilters.DistortionMode."""

    if not isinstance(value, str):
        raise ValueError("{} must be a string".format(name))
    try:
        return getattr(audiofilters.DistortionMode, value.upper())
    except AttributeError as exc:
        raise ValueError("unknown distortion mode: {}".format(value)) from exc


class _Blocks:
    """The ``"$name"`` namespace for one chain build.

    Holds the config's ``"blocks"`` definitions plus any ready-made blocks the
    host passed in, and caches what it builds so that two parameters referring
    to ``"$sweep"`` share one LFO instead of getting one each.
    """

    def __init__(self, definitions=None):
        self._definitions = definitions or {}
        self._built = {}
        self._resolving = []

    def get(self, ref, name):
        """Resolve a ``"$name"`` reference to a block."""
        key = ref[1:]
        if not key:
            raise ValueError("{} has an empty block reference".format(name))
        if key in self._built:
            return self._built[key]
        if key not in self._definitions:
            raise ValueError("{} refers to undefined block ${}".format(name, key))

        definition = self._definitions[key]
        if key in self._resolving:
            raise ValueError("block ${} depends on itself".format(key))
        self._resolving.append(key)
        try:
            if definition is None or isinstance(definition, (dict, float, int, str)):
                block = _block(definition, "block ${}".format(key), self)
            else:
                # Already a synthio object, handed in by the host.
                block = definition
        finally:
            self._resolving.pop()

        self._built[key] = block
        return block


def _as_blocks(blocks):
    if isinstance(blocks, _Blocks):
        return blocks
    return _Blocks(blocks)


_WAVEFORM_SIZE = 64

# Shape name -> waveform[i] for phase i/size, as a float in -1.0 to 1.0.
_WAVEFORM_SHAPES = {
    "triangle": lambda t: 4 * t if t < 0.25 else (2 - 4 * t if t < 0.75 else 4 * t - 4),
    "square": lambda t: 1.0 if t < 0.5 else -1.0,
    "saw": lambda t: 2 * t - 1,
    "ramp_down": lambda t: 1 - 2 * t,
}

_WAVEFORM_ALIASES = {
    "ramp_up": "saw",
    "sawtooth": "saw",
    "ramp": "saw",
    "reverse_saw": "ramp_down",
}


def _generate_waveform(shape, size, name):
    if not isinstance(shape, str):
        raise ValueError("{} shape must be a string".format(name))
    if size < 2:
        raise ValueError("{} needs at least 2 samples".format(name))

    key = shape.lower().replace(" ", "_").replace("-", "_")
    key = _WAVEFORM_ALIASES.get(key, key)

    if key == "sine":
        return array.array(
            "h",
            [int(32767 * math.sin(2 * math.pi * i / size)) for i in range(size)],
        )
    if key not in _WAVEFORM_SHAPES:
        raise ValueError("unknown waveform shape: {}".format(shape))

    point = _WAVEFORM_SHAPES[key]
    return array.array("h", [int(32767 * point(i / size)) for i in range(size)])


def _waveform(value, name, blocks=None):
    """Build an LFO waveform buffer.

    A shape name, ``{"shape": ..., "size": ...}``, or a literal list of 16-bit
    signed samples. ``None`` leaves synthio's built-in triangle in place.
    """
    if value is None:
        return None

    if isinstance(value, str):
        return _generate_waveform(value, _WAVEFORM_SIZE, name)

    if isinstance(value, dict):
        for key in value:
            if key not in ("shape", "size"):
                raise ValueError("{} has no parameter {}".format(name, key))
        if "shape" not in value:
            raise ValueError("{} requires a shape".format(name))
        size = _WAVEFORM_SIZE
        if "size" in value:
            size = _int(value["size"], "{} size".format(name))
        return _generate_waveform(value["shape"], size, name)

    if isinstance(value, (list, tuple)):
        samples = []
        for sample in value:
            sample = _int(sample, "{} sample".format(name))
            if not -32768 <= sample <= 32767:
                raise ValueError("{} samples must be -32768 to 32767".format(name))
            samples.append(sample)
        if len(samples) < 2:
            raise ValueError("{} needs at least 2 samples".format(name))
        return array.array("h", samples)

    raise ValueError("{} must be a name, dict or list".format(name))


def _math_operation(value, name, blocks=None):
    """Map "lerp"/"SCALE_OFFSET"/... to a synthio.MathOperation."""

    if not isinstance(value, str):
        raise ValueError("{} must be a string".format(name))
    key = value.replace(" ", "_").replace("-", "_").upper()
    try:
        return getattr(synthio.MathOperation, key)
    except AttributeError as exc:
        raise ValueError("unknown math operation: {}".format(value)) from exc


# block type -> (module, class, {parameter: converter}, (required parameters,))
_BLOCKS = {
    "lfo": (
        "LFO",
        {
            "waveform": _waveform,
            "rate": _block,
            "scale": _block,
            "offset": _block,
            "phase_offset": _block,
            "once": _bool,
            "interpolate": _bool,
        },
        (),
    ),
    "math": (
        "Math",
        {
            "operation": _math_operation,
            "a": _block,
            "b": _block,
            "c": _block,
        },
        ("operation", "a"),
    ),
}


def _make_block(spec, name, blocks):
    """Build one synthio.LFO or synthio.Math from a ``{"block": ...}`` dict."""

    kind = spec.get("block", spec.get("type"))
    if kind is None:
        raise ValueError('{} block is missing the "block" key'.format(name))
    if not isinstance(kind, str):
        raise ValueError("{} block type must be a string".format(name))

    key = kind.lower().replace(" ", "_").replace("-", "_")
    if key not in _BLOCKS:
        raise ValueError("unknown block type: {}".format(kind))
    class_name, params, required = _BLOCKS[key]

    kwargs = {}
    for param, value in spec.items():
        if param in ("block", "type"):
            continue
        if param not in params:
            raise ValueError("{} has no parameter {}".format(class_name, param))
        kwargs[param] = params[param](value, "{} {}".format(name, param), blocks)

    for param in required:
        if param not in kwargs:
            raise ValueError("{} requires {}".format(class_name, param))

    return getattr(synthio, class_name)(**kwargs)


def _biquad(value, name, blocks=None):
    """Build synthio.Biquad object(s) for audiofilters.Filter.

    Accepts one filter dict or a list of them, to run several biquads in
    series::

        "filter": {"mode": "LOW_PASS", "frequency": 800, "Q": 0.7071}
        "filter": [{"mode": "HIGH_PASS", "frequency": 100},
                   {"mode": "LOW_PASS", "frequency": 4000}]

    ``frequency``, ``Q`` and ``A`` are block inputs, so a filter can be swept.
    """

    if isinstance(value, (list, tuple)):
        return [_biquad(item, name, blocks) for item in value]

    if not isinstance(value, dict):
        raise ValueError("{} must be a dict or list of dicts".format(name))

    mode = value.get("mode", "LOW_PASS")
    if not isinstance(mode, str):
        raise ValueError("{} mode must be a string".format(name))
    try:
        mode = getattr(synthio.FilterMode, mode.upper())
    except AttributeError as exc:
        raise ValueError("unknown filter mode: {}".format(value["mode"])) from exc

    if "frequency" not in value:
        raise ValueError("{} requires a frequency".format(name))
    kwargs = {"frequency": _block(value["frequency"], "frequency", blocks)}
    if "Q" in value:
        kwargs["Q"] = _block(value["Q"], "Q", blocks)
    if value.get("A") is not None:
        # Gain of peaking and shelving filters: A = 10 ** (dBgain / 40).
        kwargs["A"] = _block(value["A"], "A", blocks)

    return synthio.Biquad(mode, **kwargs)


def _taps(value, name, blocks=None):
    """Tap positions/levels for audiodelays.MultiTapDelay.

    Each tap is either a position (0.0 - 1.0 of the delay buffer) or a
    ``[position, level]`` pair: ``"taps": [[0.666, 0.7], 1.0]``.
    """
    if value is None:
        return None
    if not isinstance(value, (list, tuple)):
        raise ValueError("{} must be a list".format(name))

    taps = []
    for tap in value:
        if isinstance(tap, (list, tuple)):
            if len(tap) != 2:
                raise ValueError("{} pairs must be [position, level]".format(name))
            taps.append((_float(tap[0], name), _float(tap[1], name)))
        else:
            taps.append(_float(tap, name))
    return tuple(taps)


# effect name -> (module name, class name, {parameter: converter})
#
# Only sound-affecting constructor parameters are listed; everything in
# FORMAT_ARGS is deliberately absent.
EFFECTS = {
    "chorus": (
        "audiodelays",
        "Chorus",
        {
            "max_delay_ms": _int,
            "delay_ms": _block,
            "voices": _block,
            "mix": _block,
        },
    ),
    "echo": (
        "audiodelays",
        "Echo",
        {
            "max_delay_ms": _int,
            "delay_ms": _block,
            "decay": _block,
            "mix": _block,
            "freq_shift": _bool,
        },
    ),
    "granular_pitch_shift": (
        "audiodelays",
        "GranularPitchShift",
        {
            "semitones": _block,
            "mix": _block,
            "grain_size": _int,
            "density": _int,
            # Not a block input: the core reads spread as a plain float.
            "spread": _float,
        },
    ),
    "multi_tap_delay": (
        "audiodelays",
        "MultiTapDelay",
        {
            "max_delay_ms": _int,
            "delay_ms": _block,
            "decay": _block,
            "mix": _block,
            "taps": _taps,
        },
    ),
    "pitch_shift": (
        "audiodelays",
        "PitchShift",
        {
            "semitones": _block,
            "mix": _block,
            "window": _int,
            "overlap": _int,
        },
    ),
    "distortion": (
        "audiofilters",
        "Distortion",
        {
            "drive": _block,
            "pre_gain": _block,
            "post_gain": _block,
            "mode": _distortion_mode,
            "soft_clip": _bool,
            "mix": _block,
        },
    ),
    "filter": (
        "audiofilters",
        "Filter",
        {
            "filter": _biquad,
            "mix": _block,
        },
    ),
    "phaser": (
        "audiofilters",
        "Phaser",
        {
            "frequency": _block,
            "feedback": _block,
            "mix": _block,
            "stages": _int,
        },
    ),
    "freeverb": (
        "audiofreeverb",
        "Freeverb",
        {
            "roomsize": _block,
            "damp": _block,
            "mix": _block,
        },
    ),
}

# Friendlier spellings accepted for the "effect" key.
ALIASES = {
    "reverb": "freeverb",
    "delay": "echo",
    "multitap_delay": "multi_tap_delay",
    "multitapdelay": "multi_tap_delay",
    "pitchshift": "pitch_shift",
    "granularpitchshift": "granular_pitch_shift",
}


def _normalize(name):
    """ "GranularPitchShift", "granular pitch shift", "reverb" -> table key."""
    if not isinstance(name, str):
        raise ValueError("effect name must be a string")

    # Insert underscores at CamelCase boundaries so class names work directly.
    out = ""
    for i, char in enumerate(name):
        if char.isupper() and i and not name[i - 1].isupper():
            out += "_"
        out += char
    key = out.lower().replace(" ", "_").replace("-", "_")
    key = ALIASES.get(key, key)

    if key not in EFFECTS:
        raise ValueError("unknown effect: {}".format(name))
    return key


def create_effect(
    spec,
    blocks=None,
    sample_rate=48000,
    channel_count=1,
    bits_per_sample=16,
    samples_signed=True,
    buffer_size=1024,
):
    """Create one audio effect object from a JSON effect dict.

    :param dict spec: The effect config. Must have an ``"effect"`` key naming
        the effect type; every other key is a tunable parameter of that effect.
    :param dict blocks: Blocks that ``"$name"`` parameters may refer to. Values
        are either block config dicts or ready-made `synthio` block objects.
    :param int sample_rate: Frame rate of the audio chain, in Hz.
    :param int channel_count: 1 = mono, 2 = stereo.
    :param int bits_per_sample: Bit depth of the audio chain.
    :param bool samples_signed: Whether chain samples are signed.
    :param int buffer_size: Size in bytes of each of the effect's two buffers.
    :return: The constructed effect, ready to be given a source with ``play()``.
    """
    if not isinstance(spec, dict):
        raise ValueError("effect config must be a dict")
    if "effect" not in spec:
        raise ValueError('effect config is missing the "effect" key')

    key = _normalize(spec["effect"])
    module_name, class_name, params = EFFECTS[key]
    blocks = _as_blocks(blocks)

    kwargs = {
        "sample_rate": sample_rate,
        "channel_count": channel_count,
        "bits_per_sample": bits_per_sample,
        "samples_signed": samples_signed,
        "buffer_size": buffer_size,
    }
    for name, value in spec.items():
        if name == "effect" or name == "enabled" or name in FORMAT_ARGS:
            # Format args come from the audio chain, not the preset; "enabled"
            # is handled by the caller (create_effect_chain/create_effects),
            # which skips disabled specs before they ever reach here.
            continue
        if name not in params:
            raise ValueError("{} has no parameter {}".format(class_name, name))
        kwargs[name] = params[name](value, name, blocks)

    try:
        module = __import__(module_name)
    except ImportError as exc:
        raise ValueError(
            "{} is unavailable: this build has no {}".format(class_name, module_name)
        ) from exc

    return getattr(module, class_name)(**kwargs)


def _is_enabled(spec, name):
    """Whether an effect spec's ``"enabled"`` key allows it into the chain.

    Missing means enabled -- ``"enabled"`` is opt-out, not opt-in, so existing
    configs without the key are unaffected.
    """
    if "enabled" not in spec:
        return True
    value = spec["enabled"]
    if not isinstance(value, bool):
        raise ValueError("{} enabled must be true or false".format(name))
    return value


def create_effects(preset, blocks=None, **format_args):
    """Create the effects of a preset dict, without wiring them together.

    For callers that build their own graph -- notably ones that have to wire
    from the output backwards -- and still want the preset's shared blocks.

    An effect spec with ``"enabled": false`` is skipped entirely, same as in
    `create_effect_chain`.

    :param preset: A preset dict, ``{"blocks": ..., "list": ...}``, or a bare
        list of effect configs.
    :param dict blocks: Ready-made blocks (or block configs) from the host.
    :param format_args: Audio format arguments, passed to `create_effect`.
    :return: The list of effect objects, in signal-flow order, unconnected,
        omitting any that were disabled.
    """
    if isinstance(preset, dict):
        specs = preset.get("list", ())
        definitions = preset.get("blocks", None)
    else:
        specs, definitions = preset, None

    if definitions is not None and not isinstance(definitions, dict):
        raise ValueError('"blocks" must be a mapping of name to block')

    # The preset's definitions and the host's blocks share one namespace, so
    # that "$name" means the same object wherever it appears in the preset.
    # The host's win, letting a config name a fallback for a knob that this
    # particular program does not provide.
    namespace = dict(definitions) if definitions else {}
    if blocks:
        namespace.update(blocks)
    namespace = _Blocks(namespace)

    return [
        create_effect(spec, blocks=namespace, **format_args)
        for index, spec in enumerate(specs)
        if _is_enabled(spec, "specs[{}]".format(index))
    ]


# --- Samples ---

# Recognized values for a sample's "playmode":
#
# * "oneshot"   -- plays through once when the button is pressed.
# * "hold"      -- loops for as long as the button stays held down.
# * "startstop" -- starts looping on press, keeps looping until the button is
#                  pressed again to stop it.
PLAYMODES = ("oneshot", "hold", "startstop")


def _playmode(value, name, blocks=None):
    if not isinstance(value, str):
        raise ValueError("{} must be a string".format(name))
    key = value.lower().replace(" ", "_").replace("-", "_")
    if key not in PLAYMODES:
        raise ValueError("unknown playmode: {}".format(value))
    return key


def load_samples(config, max_samples=None):
    """Read the ``"samples"`` list out of a parsed config dict.

    Each entry names a wave file, how a button press should play it back, and
    optionally an effect chain to run the wave through::

        {"file": "3.wav", "playmode": "oneshot",
         "effects": [{"effect": "freeverb", "mix": 0.6}]}

    ``playmode`` is one of `PLAYMODES` and defaults to ``"oneshot"`` when
    omitted. ``effects`` is a list of effect specs in the same shape as a
    preset's ``"list"`` -- and defaults to an empty list when omitted, meaning
    the wave plays unprocessed. Like a preset, a sample may also carry a
    ``"blocks"`` mapping naming LFOs/Math blocks that its effects refer to by
    ``"$name"``::

        {"file": "3.wav",
         "blocks": {"wobble": {"block": "lfo", "rate": 4, "scale": 3}},
         "effects": [{"effect": "pitch_shift", "semitones": "$wobble"}]}

    Pass the whole entry to `create_effects` (or `create_preset`) to build it
    -- its ``"blocks"``/``"effects"`` line up with `create_effects`'s
    ``"blocks"``/``"list"`` -- and it will pick up both the sample's own block
    definitions and any host-supplied blocks (like a hardware knob) the same
    way a preset does. The host is responsible for actually opening the file,
    building the effects, and driving playback according to the mode -- this
    only parses and validates the list.

    :param dict config: A parsed config file, as from ``json.load``.
    :param int max_samples: Cap on how many entries are returned, or ``None``
        for no cap.
    :return: A list of ``{"file": str, "playmode": str, "effects": list,
        "blocks": dict}`` dicts, in config order.
    """
    samples = config.get("samples", ())
    if not isinstance(samples, (list, tuple)):
        raise ValueError('"samples" must be a list')
    if max_samples is not None:
        samples = samples[:max_samples]

    out = []
    for index, sample in enumerate(samples):
        name = "samples[{}]".format(index)
        if not isinstance(sample, dict):
            raise ValueError("{} must be a dict".format(name))
        if "file" not in sample:
            raise ValueError("{} requires a file".format(name))
        file = sample["file"]
        if not isinstance(file, str) or not file:
            raise ValueError("{} file must be a non-empty string".format(name))
        playmode = _playmode(
            sample.get("playmode", "oneshot"), "{} playmode".format(name)
        )
        effects = sample.get("effects", ())
        if not isinstance(effects, (list, tuple)):
            raise ValueError("{} effects must be a list".format(name))
        blocks = sample.get("blocks", {})
        if not isinstance(blocks, dict):
            raise ValueError(
                '{} "blocks" must be a mapping of name to block'.format(name)
            )
        out.append(
            {
                "file": file,
                "playmode": playmode,
                "effects": list(effects),
                "blocks": dict(blocks),
            }
        )
    return out
