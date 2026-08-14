"""Cancellable sentence-streamed Kokoro synthesis for Muxiva."""

from __future__ import annotations

import json
import queue
import threading
from pathlib import Path
from typing import Any

import muxiva


class KokoroTts:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.jobs: queue.Queue[tuple[int, int, str] | None] = queue.Queue(maxsize=64)
        self.results: queue.Queue[tuple[int, int, str, bytes | Exception | None]] = queue.Queue(maxsize=512)
        self.generation = 0
        self.pending = 0
        self.lock = threading.Lock()
        self.closing = threading.Event()
        self.worker = None
        self.tts = None

    def on_prepare(self, _ctx=None) -> None:
        try:
            import numpy as np
            import sherpa_onnx
        except ImportError as error:
            raise RuntimeError("run `muxiva-dsh-voice doctor --fix` to install sherpa-onnx and numpy") from error
        root = Path(str(self.config.get("model_dir", ".models/kokoro-multi-lang-v1_1"))).resolve()
        zh_lexicon = self._compatible_zh_lexicon(root)
        kokoro = sherpa_onnx.OfflineTtsKokoroModelConfig(
            model=str(root / "model.onnx"), voices=str(root / "voices.bin"), tokens=str(root / "tokens.txt"),
            data_dir=str(root / "espeak-ng-data"),
            lexicon=f"{root / 'lexicon-us-en.txt'},{zh_lexicon}",
        )
        config = sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
            kokoro=kokoro, num_threads=int(self.config.get("num_threads", 2)), provider="cpu", debug=False,
        ), max_num_sentences=1)
        if not config.validate():
            raise RuntimeError(f"invalid Kokoro model directory: {root}; run `npm run models`")
        self.np = np
        self.tts = sherpa_onnx.OfflineTts(config)
        self.worker = threading.Thread(target=self._work, name="muxiva-kokoro-tts", daemon=True)
        self.worker.start()

    def on_process(self, frame, ctx) -> None:
        if frame is not None and hasattr(frame, "text"):
            text = frame.text.strip()
            if text:
                with self.lock:
                    generation = self.generation
                    self.pending += 1
                self.jobs.put((generation, int(frame.sequence), text), timeout=1)
                self._event(ctx, "muxiva.voice.tts.started", {"text_chars": len(text)}, frame.sequence)
                ctx.schedule_next_tick(10)
            return
        for _ in range(32):
            try:
                item = self.results.get_nowait()
            except queue.Empty:
                break
            generation, sequence, kind, value = item
            if generation != self.generation:
                continue
            if kind == "error" and isinstance(value, Exception):
                with self.lock:
                    self.pending = max(0, self.pending - 1)
                raise RuntimeError(f"Kokoro synthesis failed: {value}") from value
            if kind == "audio" and isinstance(value, bytes):
                ctx.emit("audio_out", self._audio_frame(value, sequence))
            elif kind == "done":
                with self.lock:
                    self.pending = max(0, self.pending - 1)
                    pending = self.pending
                if pending == 0:
                    self._event(ctx, "muxiva.voice.tts.stopped", {}, sequence)
        with self.lock:
            pending = self.pending
        if pending > 0 or not self.results.empty() or not self.jobs.empty():
            ctx.schedule_next_tick(10)

    def on_signal(self, signal, _ctx=None) -> None:
        if getattr(signal, "name", "") == "muxiva.voice.speech.started":
            with self.lock:
                self.generation += 1
                self.pending = 0
            self._drain(self.jobs)
            self._drain(self.results)

    def _work(self) -> None:
        while not self.closing.is_set():
            job = self.jobs.get()
            if job is None:
                return
            generation, sequence, text = job
            if generation != self.generation:
                continue
            try:
                audio = self.tts.generate(text=text, sid=int(self.config.get("speaker_id", 3)), speed=float(self.config.get("speed", 1.0)))
                pcm = (self.np.clip(audio.samples, -1, 1) * 32767).astype(self.np.int16).tobytes()
                chunk_bytes = 960 * 2
                for offset in range(0, len(pcm), chunk_bytes):
                    if generation != self.generation:
                        break
                    self.results.put((generation, sequence, "audio", pcm[offset:offset + chunk_bytes]))
                if generation == self.generation:
                    self.results.put((generation, sequence, "done", None))
            except Exception as error:
                self.results.put((generation, sequence, "error", error))

    def on_finish(self, _ctx=None) -> None:
        self.closing.set()
        self.jobs.put(None)
        if self.worker is not None:
            self.worker.join(timeout=3)

    def on_abort(self, _reason, ctx=None) -> None:
        self.on_finish(ctx)

    @staticmethod
    def _drain(target) -> None:
        while True:
            try:
                target.get_nowait()
            except queue.Empty:
                return

    @staticmethod
    def _compatible_zh_lexicon(root):
        source = root / "lexicon-zh.txt"
        cache = Path(".muxiva/cache/kokoro-lexicon-zh.txt").resolve()
        content = "".join(line for line in source.read_text(encoding="utf-8").splitlines(keepends=True) if "❓" not in line)
        if not cache.is_file() or cache.read_text(encoding="utf-8") != content:
            cache.parent.mkdir(parents=True, exist_ok=True)
            temporary = cache.with_suffix(".tmp")
            temporary.write_text(content, encoding="utf-8")
            temporary.replace(cache)
        return cache

    @staticmethod
    def _audio_frame(pcm, sequence):
        try:
            return muxiva.AudioFrame(
                pcm, 24000, 1, len(pcm) // 2,
                sample_format_name="i16le", layout="interleaved", sequence=sequence,
            )
        except TypeError:
            return muxiva.AudioFrame(pcm, 24000, 1, sequence)

    @staticmethod
    def _event(ctx, topic, payload, sequence) -> None:
        ctx.emit("event_out", muxiva.EventFrame(topic, json.dumps(payload), source="muxiva.kokoro_tts", sequence=sequence))
        ctx.publish_notification(topic, payload)
