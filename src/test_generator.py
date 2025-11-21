from markov_generator import generate_sequence

def main():
    order = int(input("Markov order (1-4): ").strip())
    
    measures = int(input("Number of measures: ").strip())

    key = input("Key (C, F#, Bm, etc.): ").strip()

    print(f"\nEnter {order} starting notes in NOTE_<num> format (example: NOTE_60)")
    seed = []
    for i in range(order):
        note = input(f"Seed note {i+1}: ").strip()
        seed.append(note)

    try:
        seq = generate_sequence(order=order, seed=seed, measures=measures, key=key)
        print("Generated Sequence:")
        print(seq)
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()