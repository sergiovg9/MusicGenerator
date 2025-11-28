from markov_generator import generate_sequence

seq = generate_sequence(
    order=2,
    seed=["NOTE_60", "NOTE_62"],
    measures=2,
    key="C"
)

print(seq)