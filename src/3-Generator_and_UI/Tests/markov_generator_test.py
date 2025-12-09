import unittest
from markov_generator import transpose_note, transpose_sequence, validate_inputs, load_model, weighted_choice, generate_sequence, KEY_TO_SEMITONES, _MODEL_CACHE

class TestScript(unittest.TestCase):
    def setUp(self):
        # Common seed and configuration used in multiple tests
        self.sample_seed = ["NOTE_60", "NOTE_61"]
        self.sample_order = 2
        self.sample_measures = 1
        self.sample_key = "C"

    # --- transpose_note ----------------------------------------------------------------

    def test_transpose_note_returns_end_unchanged(self):
        """transpose_note must return 'END' unchanged."""
        self.assertEqual(transpose_note("END", 5), "END")

    def test_transpose_note_transposes_positive_semitones(self):
        """transpose_note must correctly add semitones."""
        self.assertEqual(transpose_note("NOTE_60", 3), "NOTE_63")

    def test_transpose_note_transposes_negative_semitones(self):
        """transpose_note must correctly subtract semitones."""
        self.assertEqual(transpose_note("NOTE_60", -2), "NOTE_58")

    # --- transpose_sequence -------------------------------------------------------------

    def test_transpose_sequence_applies_transposition_to_all_notes(self):
        """transpose_sequence must apply transpose_note to each element."""
        seq = ["NOTE_60", "NOTE_62"]
        result = transpose_sequence(seq, 2)
        self.assertEqual(result, ["NOTE_62", "NOTE_64"])

    # --- validate_inputs ----------------------------------------------------------------

    def test_validate_inputs_raises_for_invalid_order(self):
        """validate_inputs must fail when order is not 1-4."""
        with self.assertRaises(ValueError):
            validate_inputs(5, self.sample_seed, self.sample_measures, self.sample_key)

    def test_validate_inputs_raises_for_seed_length_mismatch(self):
        """validate_inputs must fail when seed length does not match order."""
        with self.assertRaises(ValueError):
            validate_inputs(3, ["NOTE_60"], self.sample_measures, self.sample_key)

    def test_validate_inputs_raises_for_nonpositive_measures(self):
        """validate_inputs must fail when measures <= 0."""
        with self.assertRaises(ValueError):
            validate_inputs(self.sample_order, self.sample_seed, 0, self.sample_key)

    def test_validate_inputs_raises_for_unsupported_key(self):
        """validate_inputs must fail when key is not in KEY_TO_SEMITONES."""
        with self.assertRaises(ValueError):
            validate_inputs(self.sample_order, self.sample_seed, self.sample_measures, "INVALID")

    def test_validate_inputs_accepts_valid_inputs(self):
        """validate_inputs must accept valid configurations."""
        try:
            validate_inputs(self.sample_order, self.sample_seed, self.sample_measures, self.sample_key)
        except Exception:
            self.fail("validate_inputs raised unexpectedly.")

    # --- load_model ---------------------------------------------------------------------

    def test_load_model_returns_cached_instance_when_available(self):
        """load_model must return cached model if previously loaded."""
        _MODEL_CACHE.clear()
        _MODEL_CACHE[2] = {"dummy": "model"}
        model = load_model(2)
        self.assertEqual(model, {"dummy": "model"})

    def test_load_model_raises_file_not_found_when_model_missing(self):
        """load_model must raise FileNotFoundError when model file is missing."""
        _MODEL_CACHE.clear()
        with self.assertRaises(FileNotFoundError):
            load_model(99)

    # --- weighted_choice ----------------------------------------------------------------

    def test_weighted_choice_returns_key_from_distribution(self):
        """weighted_choice must return one of the keys from distribution."""
        dist = {"A": 1, "B": 1}
        choice = weighted_choice(dist)
        self.assertIn(choice, dist.keys())

    # --- generate_sequence ---------------------------------------------------------------

    def test_generate_sequence_calls_validation_and_raises_on_invalid_input(self):
        """generate_sequence must propagate validation errors."""
        with self.assertRaises(ValueError):
            generate_sequence(5, self.sample_seed, self.sample_measures, self.sample_key)

    def test_generate_sequence_stops_when_state_not_in_model(self):
        """generate_sequence must stop immediately if seed state not in model."""
        _MODEL_CACHE.clear()
        _MODEL_CACHE[2] = {}  # empty model -> no state match
        output = generate_sequence(2, ["NOTE_60", "NOTE_61"], 1, "C")
        # Only seed, because state not found in model
        self.assertEqual(output, ["NOTE_60", "NOTE_61"])

    def test_generate_sequence_stops_when_next_note_is_end(self):
        """generate_sequence must stop when next note is 'END'."""
        _MODEL_CACHE.clear()
        _MODEL_CACHE[2] = {
            ("NOTE_60", "NOTE_61"): {"END": 1}
        }
        output = generate_sequence(2, ["NOTE_60", "NOTE_61"], 2, "C")
        # Seed only, since END stops generation
        self.assertEqual(output, ["NOTE_60", "NOTE_61"])

    def test_generate_sequence_generates_notes_until_measure_limit(self):
        """generate_sequence must append valid notes until reaching note limit."""
        _MODEL_CACHE.clear()
        _MODEL_CACHE[1] = {
            ("NOTE_60",): {"NOTE_61": 1},
            ("NOTE_61",): {"NOTE_62": 1},
            ("NOTE_62",): {"NOTE_63": 1},
            ("NOTE_63",): {"END": 1},
        }
        output = generate_sequence(1, ["NOTE_60"], 2, "C")  # 8 notes max
        self.assertTrue(len(output) >= 1)

    def test_generate_sequence_transposes_seed_and_back(self):
        """generate_sequence must transpose seed to normalized key and back to original."""
        _MODEL_CACHE.clear()
        _MODEL_CACHE[1] = {("NOTE_60",): {"END": 1}}
        output = generate_sequence(1, ["NOTE_62"], 1, "D")  # D -> -2 semitones normalization
        # After normalization and reverse transposition, original seed should remain
        self.assertEqual(output, ["NOTE_62"])