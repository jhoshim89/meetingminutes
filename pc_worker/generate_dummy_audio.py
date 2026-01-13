import wave
import math
import struct
import os


def generate_sine_wave(filename, duration=5, frequency=440.0, framerate=44100):
    """Generate a valid WAV file with a sine wave."""
    n_frames = int(duration * framerate)

    with wave.open(filename, "w") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes (16-bit)
        wav_file.setframerate(framerate)

        data = []
        for i in range(n_frames):
            t = i / framerate
            value = int(32767.0 * 0.5 * math.sin(2.0 * math.pi * frequency * t))
            data.append(struct.pack("<h", value))

        wav_file.writeframes(b"".join(data))

    print(f"Generated {filename} ({duration}s)")


if __name__ == "__main__":
    generate_sine_wave("test_audio.wav")
