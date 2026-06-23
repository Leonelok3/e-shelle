import math
import random
import struct
import wave
from pathlib import Path


class MusicGenerator:
    """Simple procedural music generator producing WAV files.

    This creates original, royalty-free music by algorithmic composition (sine waves,
    basic chords and envelopes). Good as a starting point for background tracks
    suitable for ads; you can sell generated music as you own the output.
    """

    def __init__(self, sample_rate: int = 44100, bit_depth: int = 16):
        self.sample_rate = sample_rate
        self.bit_depth = bit_depth

    def generate(self, output_path: Path, duration: int = 30, seed: int | None = None) -> Path:
        rng = random.Random(seed)
        bpm = rng.choice([90, 100, 110, 120])
        beats = int(duration * bpm / 60)

        # simple chord progression in C major (frequencies)
        chords = [
            (261.63, 329.63, 392.00),  # C E G
            (293.66, 369.99, 440.00),  # D F# A
            (329.63, 392.00, 493.88),  # E G B
            (392.00, 493.88, 587.33),  # G B D
        ]

        samples = []
        sr = self.sample_rate
        total_frames = int(duration * sr)
        envelope = self._adsr_envelope(total_frames, sr)

        for i in range(total_frames):
            t = i / sr
            # chord rotates every whole note
            chord_idx = int((t * bpm) // 60) % len(chords)
            chord = chords[chord_idx]
            value = 0.0
            for f in chord:
                # slight detune and amplitude variation
                detune = f * (1 + rng.uniform(-0.002, 0.002))
                value += 0.3 * math.sin(2 * math.pi * detune * t)
            # simple bass sine underlay
            bass = 0.2 * math.sin(2 * math.pi * chords[chord_idx][0] / 2 * t)
            sample = (value + bass) * envelope[i]
            # soft clipping
            sample = max(-1.0, min(1.0, sample))
            samples.append(int(sample * 32767))

        # write WAV 16-bit mono
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_path), 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sr)
            frames = struct.pack('<' + 'h' * len(samples), *samples)
            wav.writeframes(frames)

        return output_path

    def _adsr_envelope(self, frames: int, sr: int):
        # Attack 0.5s, decay 1s to sustain 0.8, release 1s
        attack = int(0.5 * sr)
        decay = int(1.0 * sr)
        release = int(1.0 * sr)
        sustain_level = 0.8
        env = [0.0] * frames
        for i in range(frames):
            if i < attack:
                env[i] = i / max(1, attack)
            elif i < attack + decay:
                env[i] = 1 - (1 - sustain_level) * ((i - attack) / max(1, decay))
            elif i < frames - release:
                env[i] = sustain_level
            else:
                env[i] = sustain_level * (1 - ((i - (frames - release)) / max(1, release)))
        return env
