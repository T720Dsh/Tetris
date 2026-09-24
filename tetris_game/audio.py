"""程序化音效：用 numpy 合成复古 8-bit 风格音效，无外部素材依赖"""
from __future__ import annotations
import math

import numpy as np

SAMPLE_RATE = 44100


class Synth:
    """合成并缓存音效"""

    def __init__(self):
        self._cache: dict[str, np.ndarray] = {}
        self._build()

    # ------------------------------------------------------------ 基础合成
    @staticmethod
    def _tone(freq: float, dur: float, vol: float = 0.5,
              wave: str = "square", decay: float = 6.0) -> np.ndarray:
        n = int(SAMPLE_RATE * dur)
        t = np.arange(n) / SAMPLE_RATE
        if wave == "square":
            sig = np.sign(np.sin(2 * np.pi * freq * t))
        elif wave == "sine":
            sig = np.sin(2 * np.pi * freq * t)
        elif wave == "saw":
            sig = 2 * ((freq * t) % 1.0) - 1
        else:
            sig = np.sin(2 * np.pi * freq * t) + 0.5 * np.sin(4 * np.pi * freq * t)
        env = np.exp(-decay * t)
        sig = sig * env * vol
        return sig.astype(np.float32)

    @staticmethod
    def _noise(dur: float, vol: float = 0.4, decay: float = 12.0) -> np.ndarray:
        n = int(SAMPLE_RATE * dur)
        rng = np.random.default_rng(7)
        t = np.arange(n) / SAMPLE_RATE
        sig = rng.standard_normal(n) * np.exp(-decay * t) * vol
        # 低通一阶
        b = np.convolve(sig, np.ones(12) / 12, mode="same")
        return b.astype(np.float32)

    @staticmethod
    def _mix(*parts: np.ndarray) -> np.ndarray:
        length = max((len(p) for p in parts), default=0)
        out = np.zeros(length, dtype=np.float32)
        for p in parts:
            out[:len(p)] += p[:length]
        peak = np.max(np.abs(out)) or 1.0
        if peak > 0.95:
            out = out * (0.95 / peak)
        return out

    def _seq(self, freqs: list[float], step: float, vol: float = 0.5,
             wave: str = "square") -> np.ndarray:
        return self._mix(*[self._tone(f, step, vol * 0.9, wave) for f in freqs])

    # ------------------------------------------------------------ 音效表
    def _build(self) -> None:
        s = self
        self._cache["move"] = s._tone(320, 0.03, 0.18, "square", 18)
        self._cache["rotate"] = s._tone(420, 0.045, 0.22, "square", 14)
        self._cache["softdrop"] = s._tone(240, 0.02, 0.10, "square", 22)
        self._cache["harddrop"] = s._mix(
            s._noise(0.08, 0.5, 16), s._tone(140, 0.09, 0.45, "square", 10))
        self._cache["lock"] = s._tone(200, 0.06, 0.30, "square", 10)
        self._cache["hold"] = s._seq([520, 660], 0.05, 0.25)
        self._cache["line1"] = s._seq([523, 784], 0.07, 0.4)
        self._cache["line2"] = s._seq([523, 659, 784], 0.06, 0.4)
        self._cache["line3"] = s._seq([523, 659, 784, 1046], 0.055, 0.4)
        self._cache["tetris"] = s._seq([392, 523, 659, 784, 1046, 1318], 0.05, 0.45)
        self._cache["tspin"] = s._seq([880, 1108, 1318], 0.05, 0.45)
        self._cache["combo"] = s._tone(660 + 30 * 5, 0.07, 0.3, "square", 8)
        self._cache["countdown"] = s._tone(440, 0.09, 0.35, "square", 8)
        self._cache["go"] = s._seq([660, 880], 0.06, 0.4)
        self._cache["levelup"] = s._seq([523, 659, 784, 1046], 0.06, 0.4)
        self._cache["gameover"] = s._seq([392, 330, 262, 196], 0.12, 0.4, "saw")
        self._cache["record"] = s._seq([523, 659, 784, 1046, 784, 1046, 1318], 0.08, 0.4)
        self._cache["ui_move"] = s._tone(600, 0.03, 0.15, "square", 16)
        self._cache["ui_ok"] = s._seq([440, 660], 0.05, 0.25)
        self._cache["warning"] = s._seq([392, 392], 0.08, 0.3, "saw")
        self._cache["pc"] = s._seq([523, 659, 784, 1046, 1318, 1568, 2093], 0.06, 0.45)

    def play(self, name: str, channel=None) -> None:
        if name not in self._cache:
            return
        import pygame
        if pygame.mixer.get_init() is None:
            return
        if channel is not None:
            channel.play(pygame.sndarray.make_sound(self._cache[name]))
        else:
            pygame.mixer.Sound(self._cache[name]).play()
