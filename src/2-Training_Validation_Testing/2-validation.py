import json
import math
from pathlib import Path


# Load validation sequences
def load_validation_sequences(root="outputs/token_sequences/validation"):
    root = Path(root)
    sequences = []

    if not root.exists():
        raise FileNotFoundError(f"Validation folder not found: {root}")

    for file in root.glob("*.json"):
        try:
            with open(file, "r") as f:
                data = json.load(f)
                tokens = data.get("tokens")
                if tokens:
                    sequences.append(tokens)
        except Exception as e:
            print(f"Error reading {file}: {e}")

    print(f"Loaded {len(sequences)} validation sequences.")
    return sequences


# Load trained Markov model
def load_model(path):
    with open(path, "r") as f:
        raw_model = json.load(f)

    model = {}

    for state_str, transitions in raw_model.items():
        state_tuple = tuple(state_str.split(","))
        model[state_tuple] = transitions

    return model


# Compute log-likelihood of a sequence under a given model
def sequence_log_likelihood(sequence, model, order):
    ll = 0.0   # log-likelihood accumulator

    if len(sequence) <= order:
        return float("-inf")

    for i in range(len(sequence) - order):
        state = tuple(sequence[i:i + order])
        next_token = sequence[i + order]

        transitions = model.get(state)

        if transitions is None:
            # Unknown state → very low probability
            ll += -50  
            continue

        prob = transitions.get(next_token)

        if prob is None or prob == 0:
            # Unknown transition
            ll += -50
        else:
            ll += math.log(prob)

    return ll


# Evaluate all models and print results
if __name__ == "__main__":
    print("Loading validation data...")
    sequences = load_validation_sequences()

    print("\nEvaluating Markov models...\n")

    for order in [1, 2, 3, 4]:
        model_path = Path(f"models/markov_order{order}.json")

        if not model_path.exists():
            print(f"Model for order {order} not found: {model_path}")
            continue

        print(f"Evaluating order {order} model...")

        model = load_model(model_path)

        total_ll = 0.0
        count = 0

        for seq in sequences:
            ll = sequence_log_likelihood(seq, model, order)
            total_ll += ll
            count += 1

        avg_ll = total_ll / max(1, count)
        print(f"Order {order} average log-likelihood: {avg_ll:.2f}\n")