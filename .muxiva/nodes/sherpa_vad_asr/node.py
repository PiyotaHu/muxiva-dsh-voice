"""Silero VAD + low-latency preview + multilingual final ASR."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import muxiva


class SherpaVadAsr:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.sherpa = None
        self.np = None
        self.vad = None
        self.recognizer = None
        self.final_recognizer = None
        self.stream = None
        self.vad_buffer = None
        self.vad_window_size = 512
        self.vad_offset = 0
        self.speaking = False
        self.muted = False
        self.barge_in_confirmed = False
        self.last_partial = ""

    def on_prepare(self, _ctx=None) -> None:
        try:
            import numpy as np
            import sherpa_onnx
        except ImportError as error:
            raise RuntimeError("run `muxiva-dsh-voice doctor --fix` to install sherpa-onnx and numpy") from error
        self.np = np
        self.sherpa = sherpa_onnx
        model_dir = Path(str(self.config.get("model_dir", ".models/asr-zh"))).resolve()
        final_model_dir = Path(str(self.config.get(
            "final_model_dir",
            ".models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17",
        ))).resolve()
        vad_model = Path(str(self.config.get("vad_model", ".models/silero_vad.onnx"))).resolve()
        required = [
            model_dir / "model.onnx",
            model_dir / "tokens.txt",
            final_model_dir / "model.int8.onnx",
            final_model_dir / "tokens.txt",
            vad_model,
        ]
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise RuntimeError(f"voice model files are missing: {', '.join(missing)}; run `npm run models`")

        self.recognizer = sherpa_onnx.OnlineRecognizer.from_zipformer2_ctc(
            tokens=str(model_dir / "tokens.txt"),
            model=str(model_dir / "model.onnx"),
            num_threads=int(self.config.get("num_threads", 2)),
            sample_rate=16_000,
            feature_dim=80,
            enable_endpoint_detection=False,
            decoding_method="greedy_search",
            provider="cpu",
            debug=False,
        )
        self.stream = self.recognizer.create_stream()
        self.final_recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=str(final_model_dir / "model.int8.onnx"),
            tokens=str(final_model_dir / "tokens.txt"),
            num_threads=int(self.config.get("final_num_threads", 2)),
            sample_rate=16_000,
            feature_dim=80,
            decoding_method="greedy_search",
            provider="cpu",
            language=str(self.config.get("final_language", "auto")),
            use_itn=bool(self.config.get("final_use_itn", True)),
            debug=False,
        )

        vad_config = sherpa_onnx.VadModelConfig()
        vad_config.silero_vad.model = str(vad_model)
        vad_config.silero_vad.threshold = float(self.config.get("vad_threshold", 0.70))
        vad_config.silero_vad.min_silence_duration = float(self.config.get("min_silence_seconds", 2.0))
        vad_config.silero_vad.min_speech_duration = float(self.config.get("min_speech_seconds", 0.35))
        vad_config.silero_vad.max_speech_duration = float(self.config.get("max_speech_seconds", 30.0))
        vad_config.sample_rate = 16_000
        self.vad_window_size = vad_config.silero_vad.window_size
        self.vad = sherpa_onnx.VoiceActivityDetector(vad_config, buffer_size_in_seconds=60)
        self.vad_buffer = np.empty(0, dtype=np.float32)

    def on_process(self, frame, ctx) -> None:
        if frame.sample_rate_hz != 16_000 or frame.channels != 1:
            raise ValueError("Sherpa VAD/ASR input must be mono PCM16 at 16 kHz")
        if self.muted:
            ctx.increment_counter("input.audio_frames_dropped_muted")
            return
        samples = self.np.frombuffer(frame.data, dtype=self.np.int16).astype(self.np.float32) / 32768.0
        ctx.increment_counter("input.audio_frames")
        ctx.set_gauge("input.audio_peak_pcm16", int(self.np.max(self.np.abs(samples)) * 32768) if len(samples) else 0)
        self.stream.accept_waveform(16_000, samples)
        while self.recognizer.is_ready(self.stream):
            self.recognizer.decode_stream(self.stream)
        partial = self.recognizer.get_result(self.stream).strip()
        self.vad_buffer = self.np.concatenate((self.vad_buffer, samples))
        window = self.vad_window_size
        while self.vad_offset + window <= len(self.vad_buffer):
            self.vad.accept_waveform(self.vad_buffer[self.vad_offset:self.vad_offset + window])
            self.vad_offset += window
            detected = self.vad.is_speech_detected()
            if detected and not self.speaking:
                self.speaking = True
                self.barge_in_confirmed = False
                self.last_partial = ""
                ctx.increment_counter("vad.candidates")
                self._event(ctx, "muxiva.voice.speech.started", {"active": True, "detector": "silero"}, frame.sequence)
            if self.speaking:
                self._preview(ctx, frame.sequence, partial)
            while not self.vad.empty():
                segment = self.vad.front
                # `front` is backed by the VAD queue; copy before `pop`
                # invalidates that native storage.
                utterance = self.np.array(segment.samples, dtype=self.np.float32, copy=True)
                self.vad.pop()
                self._commit(ctx, frame.sequence, utterance)
        if self.speaking:
            self._preview(ctx, frame.sequence, partial)
        if self.vad_offset > window * 20:
            self.vad_buffer = self.vad_buffer[self.vad_offset - window * 4:]
            self.vad_offset = window * 4

    def on_signal(self, signal, ctx) -> None:
        name = getattr(signal, "name", "")
        if name not in {"muxiva.voice.microphone.muted", "muxiva.voice.microphone.unmuted"}:
            return
        self.muted = name.endswith(".muted")
        self._reset_decoder(ctx, "microphone_muted" if self.muted else "microphone_unmuted")
        ctx.increment_counter("asr.microphone_state_resets")
        ctx.set_gauge("microphone.muted", 1 if self.muted else 0)

    def _reset_decoder(self, ctx, reason: str) -> None:
        self.vad.reset()
        self.stream = self.recognizer.create_stream()
        self.vad_buffer = self.np.empty(0, dtype=self.np.float32)
        self.vad_offset = 0
        self.speaking = False
        self.barge_in_confirmed = False
        self.last_partial = ""
        ctx.publish_notification("muxiva.voice.asr.reset", {"reason": reason})

    def _commit(self, ctx, sequence: int, utterance) -> None:
        if not self.speaking:
            return
        self.speaking = False
        self.stream.input_finished()
        while self.recognizer.is_ready(self.stream):
            self.recognizer.decode_stream(self.stream)
        preview_text = self.recognizer.get_result(self.stream).strip()
        text = preview_text
        self._event(ctx, "muxiva.voice.speech.stopped", {"active": False, "detector": "silero"}, sequence)
        started = time.monotonic_ns()
        if len(utterance) > 0:
            final_stream = self.final_recognizer.create_stream()
            final_stream.accept_waveform(16_000, utterance)
            self.final_recognizer.decode_stream(final_stream)
            text = final_stream.result.text.strip() or preview_text
        process_ms = max(0, (time.monotonic_ns() - started) // 1_000_000)
        ctx.set_gauge("asr.final_process_ms", process_ms)
        if text:
            self._confirm_barge_in(ctx, sequence, text, "final")
            ctx.increment_counter("asr.finals")
            ctx.emit("text_out", muxiva.TextFrame(text, sequence=sequence))
            self._event(ctx, "muxiva.voice.transcript.completed", {
                "text": text,
                "recognizer": "sensevoice",
                "language": str(self.config.get("final_language", "auto")),
                "processing_ms": process_ms,
            }, sequence)
        else:
            ctx.increment_counter("asr.rejected")
            self._event(ctx, "muxiva.voice.transcript.rejected", {
                "reason": "no_text",
                "detector": "silero",
                "processing_ms": process_ms,
            }, sequence)
        self.stream = self.recognizer.create_stream()
        self.last_partial = ""
        self.barge_in_confirmed = False

    def _preview(self, ctx, sequence: int, partial: str) -> None:
        if not partial or partial == self.last_partial:
            return
        self.last_partial = partial
        ctx.increment_counter("asr.partials")
        ctx.emit("transcript_preview_out", muxiva.TextFrame(partial, sequence=sequence))
        self._event(ctx, "muxiva.voice.transcript.preview", {"text": partial}, sequence)
        minimum = int(self.config.get("barge_in_min_chars", 1))
        if len(partial.replace(" ", "")) >= minimum:
            self._confirm_barge_in(ctx, sequence, partial, "partial")

    def _confirm_barge_in(self, ctx, sequence: int, text: str, stage: str) -> None:
        if self.barge_in_confirmed:
            return
        self.barge_in_confirmed = True
        ctx.increment_counter("barge_in.confirmed")
        payload = {"detector": "silero+asr", "stage": stage, "text_chars": len(text)}
        self._event(ctx, "muxiva.voice.barge_in.confirmed", payload, sequence)
        ctx.emit_signal("muxiva.voice.barge_in.confirmed", {
            "node": "muxiva.sherpa_vad_asr",
            "detector": "silero+asr",
            "stage": stage,
        })

    @staticmethod
    def _event(ctx, topic: str, payload: dict[str, Any], sequence: int) -> None:
        ctx.emit("event_out", muxiva.EventFrame(
            topic, json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            source="muxiva.sherpa_vad_asr", sequence=sequence,
        ))
        ctx.publish_notification(topic, payload)
