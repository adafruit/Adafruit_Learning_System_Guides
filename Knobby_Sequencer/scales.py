# SPDX-FileCopyrightText: John Park for Adafruit 2025 Scales for Knobby MIDI Step Sequencer
# SPDX-License-Identifier: MIT
"""
Optimized Musical Scales Library for MIDI Step Sequencer
Contains single-octave scale patterns that can be expanded across any range
All base scales start from C (MIDI note 0 relative)
"""

# Base scale patterns - single octave starting from C (relative to 0)
BASE_SCALES = {
    # Western scales
    "pentatonic_major": [0, 2, 4, 7, 9],  # C, D, E, G, A
    "pentatonic_minor": [0, 3, 5, 7, 10], # C, Eb, F, G, Bb
    "major": [0, 2, 4, 5, 7, 9, 11],      # C, D, E, F, G, A, B (Ionian)
    "dorian": [0, 2, 3, 5, 7, 9, 10],     # C, D, Eb, F, G, A, Bb
    "phrygian": [0, 1, 3, 5, 7, 8, 10],   # C, Db, Eb, F, G, Ab, Bb
    "lydian": [0, 2, 4, 6, 7, 9, 11],     # C, D, E, F#, G, A, B
    "mixolydian": [0, 2, 4, 5, 7, 9, 10], # C, D, E, F, G, A, Bb
    "minor": [0, 2, 3, 5, 7, 8, 10],      # C, D, Eb, F, G, Ab, Bb (Aeolian)
    "locrian": [0, 1, 3, 5, 6, 8, 10],    # C, Db, Eb, F, Gb, Ab, Bb
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],  # C, D, Eb, F, G, Ab, B
    "melodic_minor": [0, 2, 3, 5, 7, 9, 11],   # C, D, Eb, F, G, A, B
    "blues": [0, 3, 5, 6, 7, 10],         # C, Eb, F, Gb, G, Bb
    "chromatic": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],  # All 12 notes

    # Middle Eastern Maqams (approximated in 12-TET)
    "maqam_rast": [0, 2, 4, 5, 7, 9, 10, 11],     # C, D, E, F, G, A, Bb, B
    "maqam_hijaz": [0, 1, 4, 5, 7, 8, 10],        # C, Db, E, F, G, Ab, Bb
    "maqam_bayati": [0, 1, 3, 5, 7, 8, 10],       # C, Db, Eb, F, G, Ab, Bb
    "maqam_saba": [0, 1, 2, 5, 7, 8, 10],         # C, Db, D, F, G, Ab, Bb
    "maqam_kurd": [0, 1, 3, 5, 7, 8, 10],         # C, Db, Eb, F, G, Ab, Bb

    # Indonesian Gamelan (approximated in 12-TET)
    "slendro": [0, 2, 5, 7, 10],          # C, D, F, G, Bb
    "pelog_lima": [0, 1, 4, 7, 10],       # C, Db, E, G, Bb
    "pelog_tujuh": [0, 1, 3, 6, 7, 10, 11],  # C, Db, Eb, F#, G, Bb, B

    # Japanese Scales
    "hirajoshi": [0, 2, 3, 7, 8],         # C, D, Eb, G, Ab
    "in_scale": [0, 1, 5, 7, 8],          # C, Db, F, G, Ab
    "yo_scale": [0, 2, 5, 7, 9],          # C, D, F, G, A

    # Indian Ragas (simplified 12-TET approximations)
    "raga_bhairav": [0, 1, 4, 5, 7, 8, 11],   # C, Db, E, F, G, Ab, B
    "raga_yaman": [0, 2, 4, 6, 7, 9, 11],     # C, D, E, F#, G, A, B
    "raga_kafi": [0, 2, 3, 5, 7, 9, 10],      # C, D, Eb, F, G, A, Bb

    # Chinese Scales
    "chinese_pentatonic": [0, 2, 4, 7, 9], # C, D, E, G, A

    # African-influenced scales
    "african_pentatonic": [0, 3, 5, 7, 10], # C, Eb, F, G, Bb

    # Eastern European
    "ee_scale": [0, 2, 3, 6, 7, 8, 11],    # C, D, Eb, F#, G, Ab, B (Hungarian/Romani)

    # Celtic
    "irish_scale": [0, 2, 4, 5, 7, 9, 10]  # C, D, E, F, G, A, Bb
}

def generate_scale(scale_name, start_note=24, end_note=95):
    """
    Generate a full-range scale from a base pattern

    Args:
        scale_name (str): Name of the scale to generate
        start_note (int): Starting MIDI note (default 24 = C1)
        end_note (int): Ending MIDI note (default 95 = B6)

    Returns:
        list: List of MIDI note numbers, or None if scale not found
    """
    if scale_name not in BASE_SCALES:
        return None

    pattern = BASE_SCALES[scale_name]
    notes = []

    # Start from the octave that contains or is below start_note
    start_octave = (start_note // 12) * 12

    # Generate notes across all octaves in range
    octave = start_octave
    while octave <= end_note:
        for interval in pattern:
            note = octave + interval
            if start_note <= note <= end_note:
                notes.append(note)
        octave += 12

    return notes

def get_scale(scale_name, start_note=24, end_note=95):
    """
    Get a scale by name with specified range

    Args:
        scale_name (str): Name of the scale to retrieve
        start_note (int): Starting MIDI note (default 24 = C1)
        end_note (int): Ending MIDI note (default 95 = B6)

    Returns:
        list: List of MIDI note numbers, or None if scale not found
    """
    return generate_scale(scale_name, start_note, end_note)

def list_scales():
    """
    Get a list of all available scale names

    Returns:
        list: List of scale names
    """
    return sorted(BASE_SCALES.keys())

def get_scale_pattern(scale_name):
    """
    Get the base pattern for a scale (single octave, relative to 0)

    Args:
        scale_name (str): Name of the scale

    Returns:
        list: Base pattern or None if not found
    """
    return BASE_SCALES.get(scale_name)

def get_scale_info():
    """
    Get information about all scales organized by category

    Returns:
        dict: Dictionary with scale categories and descriptions
    """
    return {
        "Western": [
            "pentatonic_major", "pentatonic_minor", "major", "dorian", "phrygian",
            "lydian", "mixolydian", "minor", "locrian", "harmonic_minor",
            "melodic_minor", "blues", "chromatic"
        ],
        "Middle Eastern": [
            "maqam_rast", "maqam_hijaz", "maqam_bayati", "maqam_saba", "maqam_kurd"
        ],
        "Indonesian": [
            "slendro", "pelog_lima", "pelog_tujuh"
        ],
        "Japanese": [
            "hirajoshi", "in_scale", "yo_scale"
        ],
        "Indian": [
            "raga_bhairav", "raga_yaman", "raga_kafi"
        ],
        "Chinese": [
            "chinese_pentatonic"
        ],
        "African": [
            "african_pentatonic"
        ],
        "Eastern European": [
            "ee_scale"
        ],
        "Celtic": [
            "irish_scale"
        ]
    }
