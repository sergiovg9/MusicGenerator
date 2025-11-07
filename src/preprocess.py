import os
import json
import pandas as pd
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from music21 import converter, instrument, note, chord

DATA_ROOT = Path("data/maestro-v3.0.0")
CSV_PATH = DATA_ROOT / "maestro-v3.0.0.csv"
OUTPUT_DIR = Path("outputs/token_sequences")
RESOLUTION = 0.25
VELOCITY_BINS = 8
TIME_SHIFT_LIMIT = 32

def velocity_to_bin(velocity, n_bins=VELOCITY_BINS):
    bin_size = 128 // n_bins
    return velocity // bin_size

def quantize_time(t, resolution=RESOLUTION):
    return round(t / resolution) * resolution

def parse_midi_file(filepath):
    """Convert a MIDI file to a sequence of token events."""
    try:
        midi_data = converter.parse(filepath)
    except Exception as e:
        return None, f"Error reading {filepath}: {e}"

    parts = instrument.partitionByInstrument(midi_data)
    piano_part = parts.parts[0] if parts else midi_data.flat.notes

    events = []
    prev_time = 0.0
    current_velocity_bin = None

    for element in piano_part.flat.notesAndRests:
        start = quantize_time(element.offset)
        delta = start - prev_time
        if delta > 0:
            for _ in range(min(int(delta / RESOLUTION), TIME_SHIFT_LIMIT)):
                events.append("TIME_SHIFT_1")

        if isinstance(element, note.Note):
            velocity = element.volume.velocity or 64
            velocity_bin = velocity_to_bin(velocity)
            if velocity_bin != current_velocity_bin:
                events.append(f"VELOCITY_{velocity_bin}")
                current_velocity_bin = velocity_bin
            pitch = element.pitch.midi
            events.append(f"NOTE_ON_{pitch}")
            for _ in range(min(int(element.quarterLength / RESOLUTION), TIME_SHIFT_LIMIT)):
                events.append("TIME_SHIFT_1")
            events.append(f"NOTE_OFF_{pitch}")

        elif isinstance(element, chord.Chord):
            velocity = element.volume.velocity or 64
            velocity_bin = velocity_to_bin(velocity)
            if velocity_bin != current_velocity_bin:
                events.append(f"VELOCITY_{velocity_bin}")
                current_velocity_bin = velocity_bin
            for pitch in [p.midi for p in element.pitches]:
                events.append(f"NOTE_ON_{pitch}")
            for _ in range(min(int(element.quarterLength / RESOLUTION), TIME_SHIFT_LIMIT)):
                events.append("TIME_SHIFT_1")
            for pitch in [p.midi for p in element.pitches]:
                events.append(f"NOTE_OFF_{pitch}")

        prev_time = start + element.quarterLength

    events.append("END")
    return events, None

def process_entry(row, output_dir):
    midi_path = DATA_ROOT / row["midi_filename"]
    out_path = output_dir / f"{midi_path.stem}.json"
    if out_path.exists():
        return f"The file already exists. Skipping: {midi_path.name}"

    tokens, error = parse_midi_file(midi_path)
    if error or not tokens:
        return f"Error: {error}"

    metadata = {
        "composer": row["canonical_composer"],
        "title": row["canonical_title"],
        "year": row["year"],
        "duration": row["duration"],
        "split": row["split"],
        "midi_file": str(row["midi_filename"])
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"metadata": metadata, "tokens": tokens}, f, indent=2)

    return f"{midi_path.name}"

def process_maestro_parallel(csv_path=CSV_PATH, output_dir=OUTPUT_DIR, max_workers=6):
    df = pd.read_csv(csv_path)
    print(f"{len(df)} found entries in the dataset.")

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
    process_maestro_parallel(max_workers=os.cpu_count() - 1)
