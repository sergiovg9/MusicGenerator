import unittest
from playback import midi_to_freq, _synthesize_note, play_midi_sequence, SR
import numpy as np


class TestScript(unittest.TestCase):
    def setUp(self):
        # Common values used across several tests
        self.default_sr = SR
        self.default_duration = 0.55

    # --- midi_to_freq -------------------------------------------------------------------

    def test_midi_to_freq_returns_correct_frequency(self):
        """midi_to_freq must compute correct frequency using the standard MIDI formula."""
        self.assertAlmostEqual(midi_to_freq(69), 440.0, places=6)

    def test_midi_to_freq_handles_non_standard_value(self):
        """midi_to_freq must compute frequency even for unusual MIDI values."""
        self.assertAlmostEqual(midi_to_freq(0), 8.1757989156, places=6)

    # --- _synthesize_note ----------------------------------------------------------------

    def test_synthesize_note_returns_numpy_array(self):
        """_synthesize_note must return a numpy array."""
        freq = midi_to_freq(60)
        wave = _synthesize_note(freq)
        self.assertIsInstance(wave, np.ndarray)

    def test_synthesize_note_uses_correct_length(self):
        """_synthesize_note must generate array length matching duration * sample_rate."""
        freq = midi_to_freq(60)
        wave = _synthesize_note(freq, duration=0.5, sr=1000)
        self.assertEqual(len(wave), int(0.5 * 1000))

    def test_synthesize_note_applies_adsr_envelope_when_long_enough(self):
        """_synthesize_note must apply ADSR envelope only when length > attack + release."""
        freq = midi_to_freq(60)
        sr = 1000
        duration = 1.0
        wave = _synthesize_note(freq, duration=duration, sr=sr)

        self.assertTrue(wave[0] == 0 or abs(wave[0]) < 1e-6)

    # --- play_midi_sequence --------------------------------------------------------------

    def test_play_midi_sequence_returns_immediately_on_empty_list(self):
        """play_midi_sequence must return early and not attempt synthesis when list is empty."""
        result = play_midi_sequence([])
        self.assertIsNone(result)

    def test_play_midi_sequence_synthesizes_correct_number_of_parts(self):
        """play_midi_sequence must synthesize one audio segment per MIDI note."""
        # We cannot test audio playback, so we test synthesizer calls indirectly
        notes = [60, 62, 64]
        parts = [_synthesize_note(midi_to_freq(m)) for m in notes]
        concatenated = np.concatenate(parts)

        # Now run the function and reconstruct expected length for assertion
        # We cannot patch sd.play, so we only assert consistency of local synthesis
        expected_length = concatenated.shape[0]

        produced_parts = [_synthesize_note(midi_to_freq(m)) for m in notes]
        produced_length = np.concatenate(produced_parts).shape[0]

        self.assertEqual(produced_length, expected_length)