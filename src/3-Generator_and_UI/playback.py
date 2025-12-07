import numpy as np
import sounddevice as sd

SR = 44100


def midi_to_freq(midi):
    """Convert MIDI pitch value to frequency in Hz."""
    return 440.0 * (2 ** ((midi - 69) / 12.0))


def _synthesize_note(freq, duration=0.55, sr=SR):
    """Generate a single synthesized note with a simple ADSR envelope."""
    t = np.linspace(0, duration, int(sr * duration), False)

    env = np.ones_like(t)
    attack = int(0.02 * sr)
    release = int(0.04 * sr)

    if len(t) > attack + release:
        env[:attack] = np.linspace(0, 1, attack)
        env[-release:] = np.linspace(1, 0, release)

    wave = 0.25 * np.sin(2 * np.pi * freq * t) * env
    return wave


def play_midi_sequence(midi_list, sr=SR):
    """Play a list of MIDI notes sequentially."""
    if not midi_list:
        print("[AUDIO] No MIDI notes to play.")
        return

    # Synthesize all notes
    parts = [_synthesize_note(midi_to_freq(m)) for m in midi_list]
    audio = np.concatenate(parts)

    # Play the audio
    sd.play(audio, sr)
    sd.wait()
