import unittest
import json
import tempfile
from pathlib import Path
from training_1 import load_train_sequences, train_markov_chain, save_model


class Testtraining_1(unittest.TestCase):
    """Unit tests for training_1.py functions."""

    def setUp(self):
        """Prepare a temporary directory for file-based tests."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    # load_train_sequences

    def test_load_train_sequences_raises_when_folder_missing(self):
        """Test that load_train_sequences raises FileNotFoundError for a missing folder."""
        with self.assertRaises(FileNotFoundError):
            load_train_sequences(root="non_existent_directory_123")

    def test_load_train_sequences_loads_only_json_files_with_tokens(self):
        """Test that load_train_sequences loads valid JSON files containing 'tokens'."""
        valid = self.temp_path / "file1.json"
        invalid = self.temp_path / "file2.json"
        non_json = self.temp_path / "file3.txt"

        valid.write_text(json.dumps({"tokens": [1, 2, 3]}))
        invalid.write_text(json.dumps({"no_tokens": [9]}))
        non_json.write_text("text file")

        result = load_train_sequences(root=str(self.temp_path))
        self.assertEqual(result, [[1, 2, 3]])

    # train_markov_chain

    def test_train_markov_chain_empty_input_returns_empty_model(self):
        """Test that training with an empty sequence list returns an empty model."""
        model = train_markov_chain([])
        self.assertEqual(model, {})

    def test_train_markov_chain_skips_short_sequences(self):
        """Test that sequences shorter than or equal to the order are ignored."""
        sequences = [[1], [2, 3]]
        model = train_markov_chain(sequences, order=2)
        self.assertEqual(model, {})

    def test_train_markov_chain_builds_correct_probabilities(self):
        """Test that model probabilities sum to 1 for a simple deterministic chain."""
        sequences = [[1, 2, 3]]
        model = train_markov_chain(sequences, order=1)
        state = (1,)
        self.assertAlmostEqual(sum(model[state].values()), 1.0)

    def test_train_markov_chain_multiple_transitions(self):
        """Test that transition counts convert into correct probabilities."""
        sequences = [[1, 2, 3, 2, 3]]
        model = train_markov_chain(sequences, order=1)
        state = (2,)
        # transitions: 2→3 occurs twice, 2→? no others
        self.assertAlmostEqual(model[state][3], 1.0)

    # save_model

    def test_save_model_raises_typeerror_when_state_contains_non_strings(self):
        """Test that save_model raises TypeError when tuple elements are not strings."""
        model = {(1, 2): {3: 0.5, 4: 0.5}}
        out_file = self.temp_path / "model.json"

        with self.assertRaises(TypeError):
            save_model(model, out_file)

    def test_save_model_raises_typeerror_for_nested_directories_with_non_string_state(self):
        """Test that save_model raises TypeError even when parent directories must be created."""
        model = {(9,): {1: 1.0}}
        nested_path = self.temp_path / "nested" / "deep" / "model.json"

        with self.assertRaises(TypeError):
            save_model(model, nested_path)
