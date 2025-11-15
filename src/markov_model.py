import json
import random
from collections import defaultdict
from pathlib import Path


def train_markov_chain(sequences, order=1):
    """
    Train a first-order Markov chain.
    sequences: list of token lists
    Returns: dict mapping state -> dict of next_token -> probability
    """

    if order != 1:
        raise NotImplementedError("Only order=1 is supported for now.")

    transitions = defaultdict(lambda: defaultdict(int))

    for seq in sequences:
        for i in range(len(seq) - 1):
            state = seq[i]
            next_token = seq[i + 1]
            transitions[state][next_token] += 1

    model = {}
    for state, next_counts in transitions.items():
        total = sum(next_counts.values())
        model[state] = {
            token: count / total
            for token, count in next_counts.items()
        }

    return model


def generate_sequence(model, length=100):
    """
    Generate a new sequence of notes using a trained Markov model.
    """

    if not model:
        raise ValueError("Model is empty or not trained.")

    state = random.choice(list(model.keys()))
    output = [state]

    for _ in range(length - 1):
        next_probs = model.get(state)

        if not next_probs:
            state = random.choice(list(model.keys()))
            output.append(state)
            continue

        tokens = list(next_probs.keys())
        probs = list(next_probs.values())
        state = random.choices(tokens, probs)[0]
        output.append(state)

        if state == "END":
            break

    return output


def load_sequences_from_directory(root="outputs/token_sequences"):
    """
    Load all token JSON files from train/test/validation folders.
    Returns: list of sequences (list of str)
    """

    root_path = Path(root)
    sequences = []

    for split in ["train", "test", "validation"]:
        folder = root_path / split
        if not folder.exists():
            print(f"Warning: folder not found: {folder}")
            continue

        for file in folder.glob("*.json"):
            try:
                with open(file, "r") as f:
                    data = json.load(f)
                    seq = data.get("tokens")
                    if seq:
                        sequences.append(seq)
            except Exception as e:
                print(f"Error while reading {file}: {e}")

    print(f"Loaded {len(sequences)} sequences.")
    return sequences


def save_model(model, path="models/markov_model.json"):
    """
    Save trained model as JSON.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump(model, f, indent=2)

    print(f"Model saved to {path}")


if __name__ == "__main__":
    sequences = load_sequences_from_directory()
    model = train_markov_chain(sequences)
    save_model(model)
