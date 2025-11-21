import json
import random
from pathlib import Path

# GLOBAL CACHE (models are loaded only once)
_MODEL_CACHE = {}

# Semitone offsets to transpose any key to C major / A minor
KEY_TO_SEMITONES = {
    "C": 0, "Am": 0,
    "C#": -1, "A#m": -1,
    "D": -2, "Bm": -2,
    "D#": -3, "Cm": -3,
    "E": -4, "C#m": -4,
    "F": -5, "Dm": -5,
    "F#": -6, "D#m": -6,
    "G": -7, "Em": -7,
    "G#": -8, "Fm": -8,
    "A": -9, "F#m": -9,
    "A#": -10, "Gm": -10,
    "B": -11, "G#m": -11,
}

def transpose_note(note_str, semitones):
    """
    Transpose note like NOTE_60 -> NOTE_63 (+3 semitones)
    Handles only NOTE_<pitch> format.
    """
    if note_str == "END":
        return "END"

    prefix, pitch_str = note_str.split("_")
    pitch = int(pitch_str)
    transposed = pitch + semitones
    return f"{prefix}_{transposed}"

def transpose_sequence(seq, semitones):
    return [transpose_note(n, semitones) for n in seq]


# VALIDATION
def validate_inputs(order, seed, measures, key):
    if order not in {1, 2, 3, 4}:
        raise ValueError("Order must be 1, 2, 3, or 4")

    if len(seed) != order:
        raise ValueError(f"Seed must contain {order} notes")

    if measures <= 0:
        raise ValueError("Measures must be > 0")

    if key not in KEY_TO_SEMITONES:
        raise ValueError(f"Key {key} is not supported")


# MODEL LOADING
def load_model(order):
    """
    Loads the Markov model from cache. If not present, loads from file.
    """
    global _MODEL_CACHE

    if order in _MODEL_CACHE:
        return _MODEL_CACHE[order]

    path = Path(f"models/markov_order{order}.json")

    if not path.exists():
        raise FileNotFoundError(f"Model not found: {path}")

    raw_model = json.load(open(path, "r"))

    model = {}
    for key, transitions in raw_model.items():
        state = tuple(key.split(","))
        model[state] = transitions

    _MODEL_CACHE[order] = model
    return model


# WEIGHTED SAMPLING
def weighted_choice(distribution: dict):
    notes = list(distribution.keys())
    weights = list(distribution.values())
    return random.choices(notes, weights)[0]


# SEQUENCE GENERATION
def generate_sequence(order, seed, measures, key):
    """
    order: 1-4
    seed: list of initial notes ["NOTE_60", ...]
    measures: duration (1 measure = 4 notes)
    key: original key ("C", "F#", "Bm", etc)

    RETURNS: list of notes in the requested key
    """

    # Validation
    validate_inputs(order, seed, measures, key)

    # Convert measures to number of notes
    total_notes = measures * 4

    # Load model
    model = load_model(order)

    # Transpose input seed to C / Am normalization
    semitones = KEY_TO_SEMITONES[key]  # usually negative (to normalize)
    seed_transposed = transpose_sequence(seed, semitones)

    # Initial state
    state = tuple(seed_transposed)
    result = list(state)

    # Gneration loop
    while len(result) < total_notes:

        if state not in model:
            break  # unseen state

        next_note = weighted_choice(model[state])

        if next_note == "END":
            break

        result.append(next_note)

        # sliding window
        state = tuple(result[-order:])

    # Transpose back to the original key
    result_untransposed = transpose_sequence(result, -semitones)

    return result_untransposed
