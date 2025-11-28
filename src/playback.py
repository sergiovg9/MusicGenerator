# Simple audio synthesis playback using sounddevice and numpy
# This is intentionally simple—sine-wave based monophonic playback.

import numpy as np
import sounddevice as sd
import threading

SR = 44100

# Play a list of MIDI pitches sequentially. Each note length is fixed (quarter note = 0.4s)

def midi_to_freq(midi):
    return 440.0 * (2 ** ((midi - 69) / 12.0))


def _synthesize_note(freq, duration=0.35, sr=SR):
    t = np.linspace(0, duration, int(sr * duration), False)
    # simple ADSR-like amplitude envelope
    env = np.ones_like(t)
    attack = int(0.02 * sr)
    release = int(0.04 * sr)
    if len(t) > attack + release:
        env[:attack] = np.linspace(0, 1, attack)
        env[-release:] = np.linspace(1, 0, release)
    wave = 0.25 * env * np.sin(2 * np.pi * freq * t)
    return wave


def play_from_pitches(pitches, bpm=120):
    # Play in separate thread so UI doesn't block
    def _play_thread(pitches):
        parts = []
        for p in pitches:
            freq = midi_to_freq(p)
            w = _synthesize_note(freq)
            parts.append(w)
        if parts:
            audio = np.concatenate(parts)
            sd.play(audio, SR)
            sd.wait()

    t = threading.Thread(target=_play_thread, args=(pitches,), daemon=True)
    t.start()