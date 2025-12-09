import os
import json
import pandas as pd
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from music21 import converter, instrument, note, chord, interval
from typing import Any

DATA_ROOT = Path("data/maestro-v3.0.0")
CSV_PATH = DATA_ROOT / "maestro-v3.0.0.csv"
OUTPUT_DIR = Path("outputs/token_sequences")

def normalize_key(midi_data):
    """
    Detects the key and transposes everything to C major or A minor.
    """
    try:
        key = midi_data.analyze('key')
    except:
        return midi_data  # fallback

    if key.mode == "major":
        interval_to_c = interval.Interval(key.tonic, note.Note("C"))
    else:  # minor
        interval_to_c = interval.Interval(key.tonic, note.Note("A"))

    return midi_data.transpose(interval_to_c)

def parse_midi_file(filepath):
    """Convert a MIDI file into a simplified token sequence (only highest note, normalized key)."""

    try:
        midi_data: Any = converter.parse(filepath)
    except Exception as e:
        return None, f"Error reading {filepath}: {e}"

    # Normalize key
    midi_data = normalize_key(midi_data)

    parts = instrument.partitionByInstrument(midi_data)

    piano_stream = None

    if parts is None:
        piano_stream = midi_data
    else:
        parts_list = getattr(parts, "parts", None)
        if parts_list and len(parts_list) > 0:
            piano_stream = parts_list[0]
        else:
            piano_stream = midi_data

    # Always flatten
    flat = piano_stream.flatten()

    tokens = []
    for element in flat.notesAndRests:
        if isinstance(element, note.Note):
            tokens.append(f"NOTE_{element.pitch.midi}")

        elif isinstance(element, chord.Chord):
            highest = max(p.midi for p in element.pitches)
            tokens.append(f"NOTE_{highest}")

    tokens.append("END")
    return tokens, None

def process_entry(row, output_dir):
    midi_path = DATA_ROOT / row["midi_filename"]
    out_path = output_dir / f"{midi_path.stem}.json"
    if out_path.exists():
        return f"File already exists. Skipping: {midi_path.name}"

    tokens, error = parse_midi_file(midi_path)
    if error or not tokens:
        return f"Error: {error}"

    metadata = {
        "composer": row["canonical_composer"],
        "title": row["canonical_title"],
        "year": row["year"],
        "split": row["split"],
        "midi_file": str(row["midi_filename"])
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"metadata": metadata, "tokens": tokens}, f, indent=2)

    return f"{midi_path.name}"

def process_maestro_parallel(csv_path=CSV_PATH, output_dir=OUTPUT_DIR, max_workers=6):
    df = pd.read_csv(csv_path)
    print(f"{len(df)} entries found in the dataset.")

    for split in ["train", "validation", "test"]:
        subset = df[df["split"] == split]
        split_dir = output_dir / split
        split_dir.mkdir(parents=True, exist_ok=True)
        print(f"\nProcessing {split} ({len(subset)} files)")

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_entry, row, split_dir) for _, row in subset.iterrows()]
            for i, f in enumerate(as_completed(futures), 1):
                msg = f.result()
                print(f"[{i}/{len(futures)}] {msg}")

if __name__ == "__main__":
    workers = (os.cpu_count() or 2) - 1
    workers = max(workers, 1)
    process_maestro_parallel(max_workers=workers)