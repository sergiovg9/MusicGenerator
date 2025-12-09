import json
import math
from pathlib import Path


def load_model(path):
    """Load a trained Markov model JSON."""
    with open(path, "r") as f:
        raw_model = json.load(f)

    model = {}
    for state_str, transitions in raw_model.items():
        # Convert string "NOTE_60,NOTE_62" -> tuple ("NOTE_60", "NOTE_62")
        state_tuple = tuple(state_str.split(","))
        model[state_tuple] = transitions

    return model

def load_sequences(root="outputs/token_sequences/test"):
    """
    Load sequences from the test dataset.
    Returns: list of token lists
    """
    root_path = Path(root)
    sequences = []

    if not root_path.exists():
        raise FileNotFoundError(f"Test directory not found: {root}")

    for file in root_path.glob("*.json"):
        try:
            with open(file, "r") as f:
                data = json.load(f)
                seq = data.get("tokens")
                if seq:
                    sequences.append(seq)
        except Exception as e:
            print(f"Error reading {file}: {e}")

    print(f"Loaded {len(sequences)} test sequences.")
    return sequences


def compute_log_likelihood(model, sequence):
    """
    Compute log-likelihood for higher-order Markov models.
    Determines model order automatically from the key lengths.
    """
    # Determine order from model keys
    example_key = next(iter(model.keys()))
    order = len(example_key)

    log_likelihood = 0.0

    for i in range(len(sequence) - order):
        state = tuple(sequence[i : i + order])  # window of size = order
        next_token = sequence[i + order]

        # Unknown state → very small probability
        if state not in model:
            log_likelihood += math.log(1e-12)
            continue

        next_probs = model[state]
        prob = next_probs.get(next_token, 1e-12)
        log_likelihood += math.log(prob)

    return log_likelihood


def evaluate_model(model, sequences):
    """
    Evaluate a model by averaging log-likelihood across sequences.
    """
    total_ll = 0
    count = 0

    for seq in sequences:
        ll = compute_log_likelihood(model, seq)
        total_ll += ll
        count += 1

    return total_ll / count if count > 0 else float("-inf")


if __name__ == "__main__":
    '''
    Although validation.py indicated that the first-order model performed the best, 
    "first-order generation sounds quite random" ↓↓↓
    '''
    best_order = 2

    model_path = f"models/markov_order{best_order}.json"
    print(f"Loading best model (order {best_order}) from {model_path}")

    model = load_model(model_path)

    print("Loading test sequences")
    test_sequences = load_sequences()

    print("Evaluating on test split")
    avg_ll = evaluate_model(model, test_sequences)

    print("\nTEST RESULTS:")
    print(f"Final average log-likelihood (order {best_order}): {avg_ll:.4f}")