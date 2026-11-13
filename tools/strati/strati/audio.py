# SPDX-License-Identifier: GPL-3.0-only
"""Reading and writing sound: any file ffmpeg reads (wav, mp3, flac, aiff, ogg ...) becomes mono float at 44.1 kHz."""
import shutil
import subprocess
import wave

import numpy as np

SR = 44100


def load(path, sr=SR):
    """the file as mono float32 in -1..1 at `sr` (ffmpeg does the decoding and the resampling)"""
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is needed (apt install ffmpeg)")
    out = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(path), "-ac", "1", "-ar", str(sr),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(out, dtype="<f4").astype(np.float32)
    return x


def save(path, x, sr=SR):
    """16-bit mono wav"""
    x = np.asarray(x, dtype=np.float64)
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    if peak > 0.999:
        x = x * (0.999 / peak)
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
