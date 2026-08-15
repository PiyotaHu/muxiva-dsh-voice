"""Cancellable, locally streamed Qwen3-TTS synthesis for Apple Silicon."""

from __future__ import annotations

import json
import queue
import sys
import threading
import gc
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any, Callable

import muxiva


class Qwen3Tts:
    SAMPLE_RATE = 24_000

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        model_loader: Callable[[str], Any] | None = None,
    ) -> None:
        self.config = config or {}
        self.model_loader = model_loader
        self.jobs: queue.Queue[tuple[int, int, str] | None] = queue.Queue(maxsize=64)
        self.results: queue.Queue[tuple[int, int, str, bytes | Exception | None]] = queue.Queue(maxsize=512)
        self.generation = 0
        self.pending = 0
        self.lock = threading.Lock()
        self.closing = threading.Event()
        self.ready = threading.Event()
        self.startup_error = None
        self.worker = None
        self.model_dir = None
        self.np = None

    def on_prepare(self, _ctx=None) -> None:
        try:
            import numpy as np
            if self.model_loader is None:
                from mlx_audio.tts.utils import load_model
                self.model_loader = load_model
        except ImportError as error:
            raise RuntimeError(
                "run `muxiva-dsh-voice doctor --fix` to install MLX-Audio and NumPy"
            ) from error
        try:
            from tqdm import tqdm
            # Project Node Hosts have an explicit lifecycle; tqdm's global
            # daemon monitor can otherwise race Python 3.13 finalization. Its
            # default multiprocessing write lock also leaves a named semaphore
            # behind when the out-of-process Host is terminated.
            tqdm.monitor_interval = 0
            tqdm.set_lock(threading.RLock())
        except ImportError:
            pass

        model_dir = Path(str(self.config.get(
            "model_dir",
            ".models/qwen3-tts-12hz-0.6b-customvoice-8bit",
        ))).resolve()
        if str(getattr(self.model_loader, "__module__", "")).startswith("mlx_audio") and not (model_dir / "config.json").is_file():
            raise RuntimeError(f"Qwen3-TTS model is missing: {model_dir}; run `npm run models`")

        self.np = np
        self.model_dir = model_dir
        self.worker = threading.Thread(target=self._work, name="muxiva-qwen3-tts", daemon=True)
        self.worker.start()
        if not self.ready.wait(timeout=120):
            self._request_stop()
            raise RuntimeError("Qwen3-TTS model loading timed out after 120 seconds")
        if self.startup_error is not None:
            raise RuntimeError(f"Qwen3-TTS model loading failed: {self.startup_error}") from self.startup_error

    def on_process(self, frame, ctx) -> None:
        if frame is not None and hasattr(frame, "text"):
            text = frame.text.strip()
            if text:
                with self.lock:
                    generation = self.generation
                    self.pending += 1
                self.jobs.put((generation, int(frame.sequence), text), timeout=1)
                self._event(ctx, "muxiva.voice.tts.started", {
                    "text_chars": len(text),
                    "engine": "qwen3-tts-mlx",
                    "speaker": str(self.config.get("speaker", "Vivian")),
                }, frame.sequence)
                ctx.schedule_next_tick(10)
            return

        for _ in range(32):
            try:
                item = self.results.get_nowait()
            except queue.Empty:
                break
            generation, sequence, kind, value = item
            if generation != self._current_generation():
                continue
            if kind == "error" and isinstance(value, Exception):
                with self.lock:
                    self.pending = max(0, self.pending - 1)
                raise RuntimeError(f"Qwen3-TTS synthesis failed: {value}") from value
            if kind == "audio" and isinstance(value, bytes):
                ctx.emit("audio_out", self._audio_frame(value, sequence))
            elif kind == "done":
                with self.lock:
                    self.pending = max(0, self.pending - 1)
                    pending = self.pending
                if pending == 0:
                    self._event(ctx, "muxiva.voice.tts.stopped", {
                        "engine": "qwen3-tts-mlx",
                    }, sequence)

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
        model = None
        try:
            # MLX 0.31 uses thread-local streams. Construct, execute and destroy
            # the model on this one worker thread; crossing threads can corrupt
            # C-extension thread state during Python 3.13 shutdown.
            # stdout is reserved for the Project Node Host JSON-RPC protocol.
            with redirect_stdout(sys.stderr):
                model = self.model_loader(str(self.model_dir))
            if not callable(getattr(model, "generate_custom_voice", None)):
                raise RuntimeError("the configured model is not a Qwen3-TTS CustomVoice checkpoint")
        except Exception as error:
            self.startup_error = error
            self.ready.set()
            return
        self.ready.set()

        try:
            while not self.closing.is_set():
                job = self.jobs.get()
                if job is None:
                    return
                generation, sequence, text = job
                if generation != self._current_generation():
                    continue
                try:
                    stream = model.generate_custom_voice(
                        text=text,
                        speaker=str(self.config.get("speaker", "Vivian")),
                        language=str(self.config.get("language", "Auto")),
                        instruct=str(self.config.get("instruct", "自然、温暖、清晰的对话语气。")),
                        stream=True,
                        streaming_interval=float(self.config.get("streaming_interval", 0.32)),
                    )
                    for result in stream:
                        if generation != self._current_generation() or self.closing.is_set():
                            close = getattr(stream, "close", None)
                            if callable(close):
                                close()
                            break
                        sample_rate = int(getattr(result, "sample_rate", self.SAMPLE_RATE))
                        if sample_rate != self.SAMPLE_RATE:
                            raise RuntimeError(
                                f"expected Qwen3-TTS {self.SAMPLE_RATE} Hz audio, received {sample_rate} Hz"
                            )
                        samples = self.np.asarray(result.audio, dtype=self.np.float32).reshape(-1)
                        pcm = (self.np.clip(samples, -1, 1) * 32767).astype(self.np.int16).tobytes()
                        self._queue_pcm(generation, sequence, pcm)
                    if generation == self._current_generation() and not self.closing.is_set():
                        self.results.put((generation, sequence, "done", None))
                except Exception as error:
                    if generation == self._current_generation() and not self.closing.is_set():
                        self.results.put((generation, sequence, "error", error))
        finally:
            model = None
            self._release_model()

    def _queue_pcm(self, generation: int, sequence: int, pcm: bytes) -> None:
        samples_per_chunk = self.SAMPLE_RATE * int(self.config.get("pcm_chunk_ms", 40)) // 1000
        chunk_bytes = samples_per_chunk * 2
        for offset in range(0, len(pcm), chunk_bytes):
            if generation != self._current_generation() or self.closing.is_set():
                return
            chunk = pcm[offset:offset + chunk_bytes]
            if chunk:
                self.results.put((generation, sequence, "audio", chunk))

    def _current_generation(self) -> int:
        with self.lock:
            return self.generation

    def on_finish(self, _ctx=None) -> None:
        self._request_stop()
        if self.worker is not None:
            self.worker.join(timeout=5)
            if self.worker.is_alive():
                raise RuntimeError("Qwen3-TTS worker did not stop within 5 seconds")

    def _request_stop(self) -> None:
        self.closing.set()
        self._drain(self.results)
        try:
            self.jobs.put_nowait(None)
        except queue.Full:
            self._drain(self.jobs)
            self.jobs.put_nowait(None)

    def on_abort(self, _reason, _ctx=None) -> None:
        # The Host exits after this acknowledgement, so the MLX owner thread
        # must finish before Python starts interpreter teardown.
        self._request_stop()
        if self.worker is not None:
            self.worker.join(timeout=5)
            if self.worker.is_alive():
                raise RuntimeError("Qwen3-TTS worker did not stop within 5 seconds")

    def _release_model(self) -> None:
        try:
            import mlx.core as mx
            mx.synchronize()
            mx.clear_cache()
        except (ImportError, RuntimeError):
            pass
        gc.collect()

    @staticmethod
    def _drain(target) -> None:
        while True:
            try:
                target.get_nowait()
            except queue.Empty:
                return

    @staticmethod
    def _audio_frame(pcm, sequence):
        try:
            return muxiva.AudioFrame(
                pcm, 24_000, 1, len(pcm) // 2,
                sample_format_name="i16le", layout="interleaved", sequence=sequence,
            )
        except TypeError:
            return muxiva.AudioFrame(pcm, 24_000, 1, sequence)

    @staticmethod
    def _event(ctx, topic, payload, sequence) -> None:
        ctx.emit("event_out", muxiva.EventFrame(
            topic,
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            source="muxiva.qwen3_tts",
            sequence=sequence,
        ))
        ctx.publish_notification(topic, payload)
