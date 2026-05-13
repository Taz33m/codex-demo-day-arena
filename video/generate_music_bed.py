#!/usr/bin/env python3
"""Generate the original ambient underscore for the HyperFrames video.

The bed is intentionally quiet, slow, and voice-safe: evolving pads, a low
pulse, sparse bell tones, and filtered texture. It uses only the Python
standard library so the audio source is reproducible without sample packs.
"""

from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path


SAMPLE_RATE = 48_000
DURATION_SECONDS = 165
OUTPUT = Path("assets/music-bed.wav")


def smoothstep(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def midi(note: int) -> float:
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


def main() -> None:
    random.seed(20260513)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    chords = [
        [38, 45, 53, 57, 60, 64],  # Dm9
        [34, 41, 50, 53, 57, 62],  # Bbmaj9 color
        [41, 48, 52, 55, 60, 67],  # Fadd9
        [36, 43, 50, 55, 59, 62],  # Csus2/add6
    ]
    voice_pans = [0.18, 0.82, 0.38, 0.66, 0.48, 0.72]
    voice_levels = [0.036, 0.030, 0.022, 0.017, 0.012, 0.008]
    phases = [random.random() * math.tau for _ in voice_pans]
    bell_events = [12, 28, 45, 62, 82, 104, 126, 148]
    noise_l = 0.0
    noise_r = 0.0

    with wave.open(str(OUTPUT), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)

        frames: list[bytes] = []
        total = SAMPLE_RATE * DURATION_SECONDS

        for i in range(total):
            t = i / SAMPLE_RATE
            chord = chords[int(t // 24) % len(chords)]
            section = 0.72 + 0.18 * math.sin(math.tau * t / 82.0)
            fade = smoothstep(t / 8.0) * smoothstep((DURATION_SECONDS - t) / 8.0)
            trem = 0.92 + 0.08 * math.sin(math.tau * 0.08 * t)

            left = 0.0
            right = 0.0

            for v, note in enumerate(chord):
                detune = 1.0 + 0.0015 * math.sin(math.tau * (0.011 + v * 0.003) * t)
                freq = midi(note) * detune
                phases[v] += math.tau * freq / SAMPLE_RATE
                phases[v] %= math.tau
                tone = math.sin(phases[v])
                tone += 0.18 * math.sin(2.0 * phases[v] + v * 0.4)
                tone *= voice_levels[v] * section * trem
                pan = voice_pans[v] + 0.035 * math.sin(math.tau * (0.017 + v * 0.002) * t)
                left += tone * math.cos(pan * math.pi / 2.0)
                right += tone * math.sin(pan * math.pi / 2.0)

            pulse_period = 2.5
            pulse_pos = (t % pulse_period) / pulse_period
            pulse_env = math.exp(-7.5 * pulse_pos)
            root = midi(chord[0] - 12)
            pulse = math.sin(math.tau * root * t) * pulse_env * 0.010
            left += pulse * 0.62
            right += pulse * 0.55

            bell = 0.0
            for event in bell_events:
                dt = t - event
                if 0.0 <= dt <= 4.2:
                    note = chord[(event // 7) % len(chord)] + 24
                    bell_freq = midi(note)
                    env = math.exp(-1.45 * dt) * smoothstep(dt / 0.08)
                    bell += math.sin(math.tau * bell_freq * t) * env * 0.006
                    bell += math.sin(math.tau * bell_freq * 1.5 * t) * env * 0.002
            left += bell * 0.52
            right += bell * 0.72

            noise_l = 0.996 * noise_l + 0.004 * random.uniform(-1.0, 1.0)
            noise_r = 0.996 * noise_r + 0.004 * random.uniform(-1.0, 1.0)
            left += noise_l * 0.022
            right += noise_r * 0.022

            left *= fade
            right *= fade
            peak_guard = 0.86
            left = max(-peak_guard, min(peak_guard, left))
            right = max(-peak_guard, min(peak_guard, right))
            frames.append(struct.pack("<hh", int(left * 32767), int(right * 32767)))

            if len(frames) >= 4096:
                wav.writeframes(b"".join(frames))
                frames.clear()

        if frames:
            wav.writeframes(b"".join(frames))

    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
