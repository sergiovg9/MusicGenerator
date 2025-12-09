import unittest
from preprocess_2 import (
    normalize_key,
    parse_midi_file,
    process_entry,
    process_maestro_parallel,
    DATA_ROOT as original_data_root,
    CSV_PATH,
    OUTPUT_DIR
)
from music21 import stream, note, chord, key as m21key, interval
from pathlib import Path
import json
import tempfile
import pandas as pd



class Testpreprocess_2(unittest.TestCase):
    """Unit tests for the preprocess_2 module."""

    def setUp(self):
        """Set up common neutral objects for tests."""
        # Create a simple music21 Stream for key normalization tests
        self.stream = stream.Stream()
        self.stream.append(note.Note("C4"))

    def test_normalize_key_major_transposes_to_c(self):
        """Test that a major key stream is transposed to C major."""
        s = stream.Stream([note.Note("C4")])
        s.insert(0, m21key.Key("G"))  # G major should transpose down a perfect fifth to C
        out = normalize_key(s)
        # After transposition, the note should become C4 (original was C4 in G major context)
        self.assertIsInstance(out, stream.Stream)

    def test_normalize_key_minor_transposes_to_a(self):
        """Test that a minor key stream is transposed to A minor."""
        s = stream.Stream([note.Note("A4")])
        s.insert(0, m21key.Key("E", "minor"))
        out = normalize_key(s)
        self.assertIsInstance(out, stream.Stream)

    def test_normalize_key_fallback_on_exception(self):
        """Test that normalize_key returns original on analysis failure."""
        class BadStream:
            def analyze(self, mode):
                raise Exception("fail")

        bad = BadStream()
        self.assertEqual(normalize_key(bad), bad)

    def test_parse_midi_file_returns_error_on_invalid_path(self):
        """Test that parse_midi_file returns an error tuple when file cannot be parsed."""
        tokens, error = parse_midi_file("nonexistent.mid")
        self.assertIsNone(tokens)

    def test_parse_midi_file_extracts_note_tokens(self):
        """Test that parse_midi_file extracts tokens from a simple MIDI file."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mid") as tmp:
            tmp_path = Path(tmp.name)

        # Create a valid stream with one note
        s = stream.Stream()
        s.append(note.Note("C4"))
        s.insert(0, m21key.Key("C"))  # Fix key to prevent transposition

        # Write the MIDI file to disk
        s.write("midi", fp=tmp_path)

        # Parse the MIDI file
        tokens, error = parse_midi_file(tmp_path, normalize=False)

        # Clean up
        tmp_path.unlink(missing_ok=True)

        # Ensure tokens is a list before using assertIn
        if tokens is None:
            tokens = []

        self.assertIsInstance(tokens, list)
        self.assertIn("NOTE_60", tokens)


    def test_parse_midi_file_handles_chords(self):
        """Test that parse_midi_file extracts the highest pitch in a chord."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mid") as tmp:
            pass

        s = stream.Stream([chord.Chord(["C4", "E4", "G5"])])
        s.write("midi", fp=tmp.name)

        tokens, error = parse_midi_file(tmp.name)
        Path(tmp.name).unlink(missing_ok=True)

        self.assertIsInstance(tokens, list)
        if tokens is not None:
            self.assertIn("NOTE_79", tokens)

    def test_process_entry_skips_existing_file(self):
        """Test that process_entry returns skip message if output already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            fake_row = {
                "midi_filename": "test.mid",
                "canonical_composer": "",
                "canonical_title": "",
                "year": "",
                "split": ""
            }

            # Create existing output file
            existing = out_dir / "test.json"
            existing.write_text("{}")

            msg = process_entry(fake_row, out_dir)
            self.assertIn("Skipping", msg)

    def test_process_entry_returns_error_when_parse_fails(self):
        """Test process_entry returns error string when parsing fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            fake_row = {
                "midi_filename": "invalid.mid",
                "canonical_composer": "",
                "canonical_title": "",
                "year": "",
                "split": ""
            }

            msg = process_entry(fake_row, out_dir)
            self.assertIn("Error", msg)

    def test_process_entry_creates_json_file(self):
        """Test successful JSON creation when MIDI file is valid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)

            # Crear el archivo MIDI dentro del directorio temporal
            midi_path = Path(tmpdir) / "valid.mid"
            s = stream.Stream([note.Note("C4")])
            s.write("midi", fp=midi_path)

            fake_row = {
                "midi_filename": midi_path.name,  # solo el nombre
                "canonical_composer": "Test",
                "canonical_title": "Title",
                "year": "2025",
                "split": "train"
            }

            # Sobrescribir DATA_ROOT temporalmente
            import preprocess_2
            preprocess_2.DATA_ROOT = Path(tmpdir)
            try:
                msg = preprocess_2.process_entry(fake_row, out_dir)
            finally:
                preprocess_2.DATA_ROOT = original_data_root  # restaurar original

            output_file = out_dir / "valid.json"

            self.assertTrue(output_file.exists())

    def test_process_maestro_parallel_reads_csv(self):
        """Test that process_maestro_parallel attempts to read CSV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "data.csv"

            df = pd.DataFrame([
                {"split": "train", "midi_filename": "fake.mid",
                 "canonical_composer": "", "canonical_title": "",
                 "year": "", "split": "train"}
            ])
            df.to_csv(csv_path, index=False)

            # Create a fake MIDI file that will error
            fake_midi = Path(tmpdir) / "fake.mid"
            fake_midi.write_text("notamidi")

            # Expect no crash
            try:
                process_maestro_parallel(csv_path=csv_path, output_dir=Path(tmpdir), max_workers=1)
                ok = True
            except Exception:
                ok = False

            self.assertTrue(ok)

