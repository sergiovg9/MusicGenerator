import json
from collections import defaultdict
from pathlib import Path


# Load token sequences for training
def load_train_sequences(root="outputs/token_sequences/train"):
    root = Path(root)
    sequences = []

    if not root.exists():
        raise FileNotFoundError(f"Train folder not found: {root}")

    for file in root.glob("*.json"):
        try:
            with open(file, "r") as f:
                data = json.load(f)
                tokens = data.get("tokens")
                if tokens:
                    sequences.append(tokens)
        except Exception as e:
            print(f"Error reading {file}: {e}")

    print(f"Loaded {len(sequences)} sequences for training.")
    return sequences


def train_markov_chain(sequences, order=1):
    """
    Train a Markov model of arbitrary order.
    states are n-grams of length = order
    """

    transitions = defaultdict(lambda: defaultdict(int))

    for seq in sequences:
        if len(seq) <= order:
            continue  # skip short sequences

        # build state transitions
        for i in range(len(seq) - order):
            state = tuple(seq[i:i + order])
            next_token = seq[i + order]
            transitions[state][next_token] += 1

    # convert counts to probabilities
    model = {}
    for state, next_counts in transitions.items():
        total = sum(next_counts.values())
        model[state] = {
            token: count / total
            for token, count in next_counts.items()
        }

    return model


# Save model as JSON (convert tuple keys to strings)
def save_model(model, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # convert tuple keys into strings for JSON compatibility
    json_ready = {",".join(state): probs for state, probs in model.items()}

    with open(path, "w") as f:
        json.dump(json_ready, f, indent=2)

    print(f"Saved model to {path}")


# Main training pipeline
if __name__ == "__main__":
    print("Loading training data...")
    sequences = load_train_sequences()

    for order in [1, 2, 3, 4]:
        print(f"\nTraining Markov model of order {order}")
        model = train_markov_chain(sequences, order=order)

        output_path = f"models/markov_order{order}.json"
        save_model(model, output_path)