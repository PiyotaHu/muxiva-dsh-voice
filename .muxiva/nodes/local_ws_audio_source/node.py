from __future__ import annotations

import muxiva
from muxiva_voice_transport import client


class LocalWsAudioSource:
    def __init__(self, config=None):
        self.config = config or {}
        self.sequence = 0
        self.bridge = None

    def on_prepare(self, _ctx=None):
        self.bridge = client("audio-source")

    def on_process(self, _frame, ctx):
        emitted = 0
        while emitted < 8:
            try:
                pcm = self.bridge.recv()
            except Exception:
                raise
            if pcm is None:
                break
            if not isinstance(pcm, bytes):
                continue
            self.sequence += 1
            ctx.emit("audio_out", self._audio_frame(pcm, 16000, self.sequence))
            emitted += 1
        ctx.schedule_next_tick(10)

    @staticmethod
    def _audio_frame(pcm, sample_rate_hz, sequence):
        try:
            return muxiva.AudioFrame(
                pcm, sample_rate_hz, 1, len(pcm) // 2,
                sample_format_name="i16le", layout="interleaved", sequence=sequence,
            )
        except TypeError:
            # Muxiva's out-of-process project-node host supplies a compact SDK shim.
            return muxiva.AudioFrame(pcm, sample_rate_hz, 1, sequence)

    def on_finish(self, _ctx=None):
        if self.bridge is not None:
            self.bridge.close()
            self.bridge = None

    def on_abort(self, _reason, ctx=None):
        self.on_finish(ctx)
