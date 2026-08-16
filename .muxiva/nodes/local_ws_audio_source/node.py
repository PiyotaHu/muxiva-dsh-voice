from __future__ import annotations

import json
import time

import muxiva
from muxiva_voice_transport import client


class LocalWsAudioSource:
    def __init__(self, config=None):
        self.config = config or {}
        self.sequence = 0
        self.bridge = None
        self.paused = False
        self.pending_marker = None

    def on_prepare(self, _ctx=None):
        self.bridge = client("audio-source")

    def on_process(self, _frame, ctx):
        processed = 0
        while processed < 8:
            try:
                pcm = self.bridge.recv()
            except Exception:
                raise
            if pcm is None:
                break
            processed += 1
            if isinstance(pcm, str):
                try:
                    control = json.loads(pcm)
                except json.JSONDecodeError:
                    ctx.increment_counter("ingress.control_invalid")
                    continue
                kind = control.get("type")
                if kind == "benchmark.audio.marker":
                    marker_id = control.get("markerId")
                    captured_ns = control.get("capturedNs")
                    if isinstance(marker_id, str) and isinstance(captured_ns, int):
                        self.pending_marker = (marker_id, captured_ns)
                    else:
                        ctx.increment_counter("benchmark.marker_invalid")
                    continue
                if kind in {"client.mute", "client.unmute", "client.stop"}:
                    self.paused = kind != "client.unmute"
                    signal_name = "muxiva.voice.microphone.muted" if self.paused else "muxiva.voice.microphone.unmuted"
                    ctx.emit_signal(signal_name, {"source": "muxiva.dsh.local_ws_audio_source", "paused": self.paused})
                    ctx.increment_counter("ingress.pause_transitions")
                    ctx.set_gauge("ingress.paused", 1 if self.paused else 0)
                    ctx.publish_notification("muxiva.voice.audio_source.state", {"paused": self.paused})
                continue
            if not isinstance(pcm, bytes):
                continue
            if self.paused:
                ctx.increment_counter("ingress.audio_frames_dropped_paused")
                continue
            self.sequence += 1
            ctx.emit("audio_out", self._audio_frame(pcm, 16000, self.sequence))
            if self.pending_marker is not None:
                marker_id, captured_ns = self.pending_marker
                self.pending_marker = None
                ctx.emit("event_out", muxiva.EventFrame(
                    "muxiva.voice.benchmark.audio_admitted",
                    json.dumps({
                        "markerId": marker_id,
                        "capturedNs": captured_ns,
                        "admittedNs": time.monotonic_ns(),
                    }, separators=(",", ":")),
                    source="muxiva.dsh.local_ws_audio_source",
                    sequence=self.sequence,
                ))
                ctx.increment_counter("benchmark.markers_admitted")
            ctx.increment_counter("ingress.audio_frames")
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
