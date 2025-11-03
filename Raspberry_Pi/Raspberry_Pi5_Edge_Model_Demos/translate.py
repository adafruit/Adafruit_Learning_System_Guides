# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# pylint: disable=line-too-long
import argparse
import json
import os
import sys
from pathlib import Path
import wave
from ollama import chat
from ollama import ChatResponse
from piper import PiperVoice

translation_wavs_dir = Path("translation_wavs")

if not translation_wavs_dir.exists():
    translation_wavs_dir.mkdir()

history_file = Path("history.json")
if not history_file.exists():
    history_obj = {"history": []}
    with open(history_file, "w") as f:
        f.write(json.dumps(history_obj))

with open(history_file, "r") as f:
    history_obj = json.loads(f.read())


def save_history():
    with open(history_file, "w") as open_history_file:
        open_history_file.write(json.dumps(history_obj))


def get_translation_filepath(text):
    filename = text.replace(" ", "_")
    return str(translation_wavs_dir / Path(filename + ".wav"))


def create_history_entry(text, translated_text, language_choice):
    new_entry = {
        "input_text": text,
        "translation_file": get_translation_filepath(text),
        "translated_text": translated_text,
        "language": language_choice,
    }
    return new_entry


def add_to_history(entry_obj):
    history_obj["history"].append(entry_obj)
    save_history()


def play_translation_wav(entry_obj):
    print(f"{entry_obj['language']}: {entry_obj['translated_text']}")
    os.system(f"aplay --disable-softvol {entry_obj['translation_file']}")


parser = argparse.ArgumentParser(
    prog="translate.py",
    description="Translates a word or phrase from english to another language and then speak the translation.",
    epilog="Made with: SmolLM3 & Piper TTS.",
)

language_name_map = {
    "es": "spanish",
    "de": "german",
    "fr": "french",
    "it": "italian",
    "pt": "portuguese",
}

language_voice_map = {
    "es": "es_MX-claude-high.onnx",
    "de": "de_DE-kerstin-low.onnx",
    "fr": "fr_FR-upmc-medium.onnx",
    "it": "it_IT-paola-medium.onnx",
    "pt": "pt_BR-jeff-medium.onnx",
}

parser.add_argument("input", nargs="?")
parser.add_argument("-l", "--language", default="es")
parser.add_argument("-r", "--replay", action="store_true")
parser.add_argument("-t", "--history", action="store_true")
args = parser.parse_args()
input_str = args.input

if args.replay:
    replay_num = None
    try:
        replay_num = int(args.input)
    except (ValueError, TypeError):
        if args.input is not None:
            print("Replay number must be an integer.")
            sys.exit()

    if replay_num is None:
        chosen_entry = history_obj["history"][-1]
    else:
        index = len(history_obj["history"]) - replay_num
        chosen_entry = history_obj["history"][index]

    play_translation_wav(chosen_entry)
    sys.exit()

if args.history:
    for i, entry in enumerate(reversed(history_obj["history"])):
        print(
            f"{i+1}: {entry['language']} - {entry['input_text']} - {entry['translated_text']}"
        )
    sys.exit()


if args.language not in language_name_map.keys(): # pylint: disable=consider-iterating-dictionary
    raise ValueError(
        f"Invalid language {args.language}. Valid languages are {language_name_map.keys()}"
    )

language = language_name_map[args.language]

for history_entry in history_obj["history"]:
    if (
        history_entry["input_text"].lower() == input_str.lower()
        and history_entry["language"] == args.language
    ):
        play_translation_wav(history_entry)
        sys.exit()

response: ChatResponse = chat(
    model="translator-smollm3",
    messages=[
        {
            "role": "system",
            "content": "You are a translation assistant. The user is going to give you a word or short phrase in english, "
            f"please translate it to {language}. Output only the {language} translation of the input. Do not output "
            "explanations, notes, or anything else. If there is not an exact literal translation, just output "
            "the best fitting alternate word or phrase that you can. Do not explain anything, only output "
            "the translation.",
        },
        {
            "role": "user",
            "content": f"{input_str}",
        },
    ],
)

translation = response["message"]["content"]
# print(translation)
if "\n" in translation:
    translation = translation.split("\n")[0]
    if len(translation) == 0:
        parts = translation.split("\n")
        for part in parts:
            if len(part) > 0:
                translation = part

history_entry = create_history_entry(input_str, translation, args.language)

voice = PiperVoice.load(language_voice_map[args.language])
with wave.open(history_entry["translation_file"], "wb") as wav_file:
    voice.synthesize_wav(translation, wav_file)

add_to_history(history_entry)
play_translation_wav(history_entry)
