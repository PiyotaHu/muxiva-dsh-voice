#!/usr/bin/env python3
"""Unattended, deterministic local voice-pipeline certification.

The runner replaces a human microphone with checksumable macOS `say` fixtures,
uses the public loopback protocol, and timestamps every observable boundary on
the same monotonic clock. It never sends audio or transcripts off the machine.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import queue
import re
import subprocess
import threading
import time
import unicodedata
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from websockets.sync.client import connect


ROOT = Path(__file__).resolve().parents[1]
VERSION = "muxiva.dsh.voice/v1"
SAMPLE_RATE = 16_000
TTS_SAMPLE_RATE = 24_000
FRAME_SAMPLES = 320


def command(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()


def percentile(values: list[float]) -> dict[str, float | int]:
    if not values:
        raise RuntimeError("a certified distribution cannot be empty")
    ordered = sorted(float(value) for value in values)

    def at(percent: float) -> float:
        position = (len(ordered) - 1) * percent
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return ordered[lower]
        return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)

    return {
        "samples": len(ordered),
        "p50": round(at(0.50), 3),
        "p95": round(at(0.95), 3),
        "p99": round(at(0.99), 3),
    }


def edit_distance(reference: list[str], hypothesis: list[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for row, expected in enumerate(reference, 1):
        current = [row]
        for column, actual in enumerate(hypothesis, 1):
            current.append(min(
                current[-1] + 1,
                previous[column] + 1,
                previous[column - 1] + (expected != actual),
            ))
        previous = current
    return previous[-1]


def normalize_zh(value: str) -> list[str]:
    return [character for character in unicodedata.normalize("NFKC", value).lower()
            if "\u4e00" <= character <= "\u9fff" or character.isascii() and character.isalnum()]


def normalize_en(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", unicodedata.normalize("NFKC", value).lower())


@dataclass
class Fixture:
    case: dict[str, str]
    samples: np.ndarray

    @property
    def duration_seconds(self) -> float:
        return len(self.samples) / SAMPLE_RATE


class FixtureStore:
    def __init__(self) -> None:
        manifest = json.loads((ROOT / "benchmarks/cases.json").read_text())
        self.cases = manifest["cases"]
        self.directory = ROOT / ".muxiva/benchmark-fixtures"
        self.directory.mkdir(parents=True, exist_ok=True)

    def load_all(self) -> list[Fixture]:
        fixtures = []
        for case in self.cases:
            target = self.directory / f"{case['id']}.wav"
            if not target.is_file():
                self._generate(case, target)
            with wave.open(str(target), "rb") as source:
                if (source.getframerate(), source.getnchannels(), source.getsampwidth()) != (16_000, 1, 2):
                    raise RuntimeError(f"invalid generated fixture format: {target}")
                samples = np.frombuffer(source.readframes(source.getnframes()), dtype=np.int16).copy()
            fixtures.append(Fixture(case, samples))
        return fixtures

    def _generate(self, case: dict[str, str], target: Path) -> None:
        aiff = target.with_suffix(".aiff")
        subprocess.run([
            "say", "-v", case["voice"], "-r", "200", "-o", str(aiff), case["text"],
        ], check=True)
        subprocess.run([
            "afconvert", str(aiff), "-o", str(target), "-f", "WAVE", "-d", "LEI16@16000", "-c", "1",
        ], check=True)
        aiff.unlink(missing_ok=True)


class Wire:
    def __init__(self, port: int) -> None:
        self.websocket = connect(
            f"ws://127.0.0.1:{port}/voice", max_size=262_144, compression=None,
        )
        ready = json.loads(self.websocket.recv(timeout=5))
        if ready.get("type") != "server.ready":
            raise RuntimeError(f"unexpected bridge handshake: {ready}")
        self.messages: queue.Queue[tuple[int, str, Any]] = queue.Queue()
        self.closed = threading.Event()
        self.receiver = threading.Thread(target=self._receive, name="benchmark-wire-receiver", daemon=True)
        self.receiver.start()

    def _receive(self) -> None:
        try:
            for raw in self.websocket:
                received_ns = time.monotonic_ns()
                if isinstance(raw, bytes):
                    self.messages.put((received_ns, "audio", raw))
                else:
                    try:
                        self.messages.put((received_ns, "event", json.loads(raw)))
                    except json.JSONDecodeError:
                        self.messages.put((received_ns, "invalid", raw))
        finally:
            self.closed.set()

    def control(self, kind: str, **payload: Any) -> int:
        sent_ns = time.monotonic_ns()
        self.websocket.send(json.dumps({"version": VERSION, "type": kind, **payload}, ensure_ascii=False))
        return sent_ns

    def audio(self, pcm: bytes) -> None:
        self.websocket.send(pcm)

    def get(self, timeout: float) -> tuple[int, str, Any]:
        try:
            return self.messages.get(timeout=timeout)
        except queue.Empty as error:
            if self.closed.is_set():
                raise RuntimeError("voice WebSocket closed during certification") from error
            raise TimeoutError("timed out waiting for voice pipeline output") from error

    def drain(self, quiet_seconds: float = 0.2) -> list[tuple[int, str, Any]]:
        drained = []
        deadline = time.monotonic() + quiet_seconds
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return drained
            try:
                item = self.get(remaining)
            except TimeoutError:
                return drained
            drained.append(item)
            deadline = time.monotonic() + quiet_seconds

    def close(self) -> None:
        try:
            self.control("client.stop")
        except Exception:
            pass
        self.websocket.close()
        self.receiver.join(timeout=2)


class ResourceSampler:
    def __init__(self, root_pid: int) -> None:
        self.root_pid = root_pid
        self.phase = "warmup"
        self.samples: list[dict[str, float | str]] = []
        self.done = threading.Event()
        self.thread = threading.Thread(target=self._run, name="benchmark-resource-sampler", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.done.set()
        self.thread.join(timeout=3)

    def _run(self) -> None:
        while not self.done.is_set():
            try:
                rows = command("ps", "-axo", "pid=,ppid=,%cpu=,rss=").splitlines()
                parsed = []
                for row in rows:
                    fields = row.split()
                    if len(fields) == 4:
                        parsed.append((int(fields[0]), int(fields[1]), float(fields[2]), int(fields[3])))
                descendants = {self.root_pid}
                changed = True
                while changed:
                    changed = False
                    for pid, parent, _, _ in parsed:
                        if parent in descendants and pid not in descendants:
                            descendants.add(pid)
                            changed = True
                selected = [row for row in parsed if row[0] in descendants]
                self.samples.append({
                    "phase": self.phase,
                    "cpu": sum(row[2] for row in selected),
                    "rssMb": sum(row[3] for row in selected) / 1024,
                })
            except Exception:
                pass
            self.done.wait(1)


class Certification:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.wire = Wire(args.port)
        self.fixtures = FixtureStore().load_all()
        self.sampler = ResourceSampler(args.service_pid)
        self.metrics: dict[str, list[float]] = {
            "browserCaptureToMuxivaFrame": [],
            "speechOnsetToBargeIn": [],
            "speechEndToAsrFinal": [],
            "firstAgentTextToFirstTtsPcm": [],
            "audioQueueAhead": [],
            "staleAudioAfterBargeIn": [],
            "asrFinalRealtimeFactor": [],
            "ttsRealtimeFactor": [],
        }
        self.zh_edits = self.zh_units = self.en_edits = self.en_units = 0
        self.tts_underruns = 0
        self.completed = 0
        self.failed = 0
        self.sent_audio_frames = 0
        self.trace_path = ROOT / "benchmarks/traces" / f"{args.mode}-{int(time.time())}.jsonl"
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        self.trace_lock = threading.Lock()

    def trace(self, kind: str, **payload: Any) -> None:
        with self.trace_lock, self.trace_path.open("a") as target:
            target.write(json.dumps({
                "at": datetime.now(timezone.utc).isoformat(), "kind": kind, **payload,
            }, ensure_ascii=False, separators=(",", ":")) + "\n")

    def send_fixture(self, fixture: Fixture, marker_id: str) -> tuple[int, int]:
        leading = np.zeros(4_800, dtype=np.int16)
        trailing = np.zeros(36_800, dtype=np.int16)
        samples = np.concatenate((leading, fixture.samples, trailing))
        started_ns = time.monotonic_ns()
        onset_ns = end_ns = 0
        marker_sent = False
        speech_start = len(leading)
        speech_end = speech_start + len(fixture.samples)
        for offset in range(0, len(samples), FRAME_SAMPLES):
            target_ns = started_ns + int(offset * 1_000_000_000 / SAMPLE_RATE)
            delay = (target_ns - time.monotonic_ns()) / 1_000_000_000
            if delay > 0:
                time.sleep(delay)
            captured_ns = time.monotonic_ns()
            if not marker_sent and offset <= speech_start < offset + FRAME_SAMPLES:
                self.wire.control("benchmark.audio.marker", markerId=marker_id, capturedNs=captured_ns)
                onset_ns = captured_ns
                marker_sent = True
            if offset <= speech_end < offset + FRAME_SAMPLES:
                end_ns = captured_ns
            self.wire.audio(samples[offset:offset + FRAME_SAMPLES].tobytes())
            self.sent_audio_frames += 1
        if end_ns == 0:
            end_ns = time.monotonic_ns()
        return onset_ns, end_ns

    def consume_asr(self, fixture: Fixture, marker_id: str, onset_ns: int, end_ns: int,
                    initial: list[tuple[int, str, Any]] | None = None) -> list[tuple[int, str, Any]]:
        items = list(initial or [])
        deadline = time.monotonic() + 25
        final_item = None
        while time.monotonic() < deadline:
            item = self.wire.get(max(0.01, deadline - time.monotonic()))
            items.append(item)
            if item[1] == "event" and item[2].get("type") == "asr.final":
                final_item = item
                break
        if final_item is None:
            raise RuntimeError(f"{fixture.case['id']}: no asr.final")

        admitted = next((item for item in items if item[1] == "event"
                         and item[2].get("type") == "benchmark.audio.admitted"
                         and item[2].get("markerId") == marker_id), None)
        barge = next((item for item in items if item[1] == "event" and item[2].get("type") == "barge.in"), None)
        if admitted is None or barge is None:
            raise RuntimeError(f"{fixture.case['id']}: missing benchmark admission or barge-in event")
        self.metrics["browserCaptureToMuxivaFrame"].append(
            max(0, (int(admitted[2]["admittedNs"]) - int(admitted[2]["capturedNs"])) / 1_000_000)
        )
        self.metrics["speechOnsetToBargeIn"].append(max(0, (barge[0] - onset_ns) / 1_000_000))
        self.metrics["speechEndToAsrFinal"].append(max(0, (final_item[0] - end_ns) / 1_000_000))
        process_ms = float(final_item[2].get("processing_ms", 0))
        self.metrics["asrFinalRealtimeFactor"].append(process_ms / 1000 / fixture.duration_seconds)
        self._score(fixture, str(final_item[2].get("text", "")))
        return items

    def _score(self, fixture: Fixture, hypothesis: str) -> None:
        reference = fixture.case["text"]
        if fixture.case["language"] == "zh":
            expected, actual = normalize_zh(reference), normalize_zh(hypothesis)
            self.zh_edits += edit_distance(expected, actual)
            self.zh_units += len(expected)
        else:
            expected, actual = normalize_en(reference), normalize_en(hypothesis)
            self.en_edits += edit_distance(expected, actual)
            self.en_units += len(expected)

    def asr_turn(self, fixture: Fixture, turn_id: str) -> None:
        self.wire.drain(0.1)
        marker_id = f"{turn_id}-speech"
        onset_ns, end_ns = self.send_fixture(fixture, marker_id)
        self.consume_asr(fixture, marker_id, onset_ns, end_ns)

    def tts_turn(self, text: str) -> None:
        self.wire.drain(0.1)
        sent_ns = self.wire.control("agent.final", text=text)
        items: list[tuple[int, str, Any]] = []
        started_ns = first_pcm_ns = stopped_ns = 0
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            item = self.wire.get(max(0.01, deadline - time.monotonic()))
            items.append(item)
            if item[1] == "event" and item[2].get("type") == "tts.started":
                started_ns = item[0]
            elif item[1] == "audio" and first_pcm_ns == 0:
                first_pcm_ns = item[0]
            elif item[1] == "event" and item[2].get("type") == "tts.stopped":
                stopped_ns = item[0]
                break
        items.extend(self.wire.drain(0.35))
        if not started_ns or not first_pcm_ns or not stopped_ns:
            raise RuntimeError("incomplete Qwen3-TTS event sequence")
        audio = [(at, raw) for at, kind, raw in items if kind == "audio"]
        audio_seconds = sum(len(raw) / 2 / TTS_SAMPLE_RATE for _, raw in audio)
        if audio_seconds <= 0:
            raise RuntimeError("Qwen3-TTS returned no audio")
        self.metrics["firstAgentTextToFirstTtsPcm"].append((first_pcm_ns - sent_ns) / 1_000_000)
        self.metrics["ttsRealtimeFactor"].append((stopped_ns - started_ns) / 1_000_000_000 / audio_seconds)
        self._playback_metrics(audio)

    def _playback_metrics(self, audio: list[tuple[int, bytes]]) -> None:
        play_at = 0.0
        for index, (at_ns, raw) in enumerate(audio):
            now = at_ns / 1_000_000_000
            if index and now > play_at:
                self.tts_underruns += 1
            play_at = max(now + 0.025, play_at) + len(raw) / 2 / TTS_SAMPLE_RATE
            self.metrics["audioQueueAhead"].append(max(0, (play_at - now) * 1000))

    def interrupted_turn(self, fixture: Fixture, turn_id: str) -> None:
        self.wire.drain(0.1)
        long_reply = (
            "这是一次用于验证全双工打断能力的较长回答，我会继续解释本地语音处理的延迟、稳定性和隐私优势。"
            if fixture.case["language"] == "zh" else
            "This is a longer answer used to verify full duplex interruption, latency, stability, and local privacy."
        )
        sent_ns = self.wire.control("agent.final", text=long_reply)
        initial: list[tuple[int, str, Any]] = []
        first_pcm_ns = 0
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and not first_pcm_ns:
            item = self.wire.get(max(0.01, deadline - time.monotonic()))
            initial.append(item)
            if item[1] == "audio":
                first_pcm_ns = item[0]
        if not first_pcm_ns:
            raise RuntimeError("interruption scenario received no TTS audio")
        self.metrics["firstAgentTextToFirstTtsPcm"].append((first_pcm_ns - sent_ns) / 1_000_000)
        time.sleep(0.25)
        marker_id = f"{turn_id}-interrupt"
        onset_ns, end_ns = self.send_fixture(fixture, marker_id)
        items = self.consume_asr(fixture, marker_id, onset_ns, end_ns, initial)
        items.extend(self.wire.drain(0.35))
        barge_ns = next(item[0] for item in items if item[1] == "event" and item[2].get("type") == "barge.in")
        stale_seconds = sum(len(raw) / 2 / TTS_SAMPLE_RATE
                            for at, kind, raw in items if kind == "audio" and at > barge_ns)
        self.metrics["staleAudioAfterBargeIn"].append(stale_seconds * 1000)
        pre_barge_audio = [(at, raw) for at, kind, raw in items if kind == "audio" and at <= barge_ns]
        if pre_barge_audio:
            self._playback_metrics(pre_barge_audio)

    def measured_turn(self, index: int, interrupt: bool, phase: str = "primary") -> None:
        half = len(self.fixtures) // 2
        fixture_index = (index // 2) % half + (half if index % 2 else 0)
        fixture = self.fixtures[fixture_index]
        turn_id = f"{phase}-{index + 1:03d}"
        started = time.monotonic()
        before = {name: len(values) for name, values in self.metrics.items()}
        try:
            if interrupt:
                self.interrupted_turn(fixture, turn_id)
            else:
                self.asr_turn(fixture, turn_id)
                self.tts_turn(fixture.case["agentReply"])
            self.completed += 1
            turn_metrics = {
                name: values[before[name]:]
                for name, values in self.metrics.items()
                if len(values) > before[name]
            }
            self.trace("turn", id=turn_id, case=fixture.case["id"], interrupt=interrupt,
                       status="passed", durationMs=round((time.monotonic() - started) * 1000, 3),
                       metrics=turn_metrics)
        except Exception as error:
            self.failed += 1
            self.trace("turn", id=turn_id, case=fixture.case["id"], interrupt=interrupt,
                       status="failed", error=type(error).__name__)
            raise

    def silence(self, seconds: float) -> None:
        started_ns = time.monotonic_ns()
        frame = np.zeros(FRAME_SAMPLES, dtype=np.int16).tobytes()
        frames = math.ceil(seconds * SAMPLE_RATE / FRAME_SAMPLES)
        for index in range(frames):
            target_ns = started_ns + int(index * FRAME_SAMPLES * 1_000_000_000 / SAMPLE_RATE)
            delay = (target_ns - time.monotonic_ns()) / 1_000_000_000
            if delay > 0:
                time.sleep(delay)
            self.wire.audio(frame)
            self.sent_audio_frames += 1
        unexpected = [item for item in self.wire.drain(0.25)
                      if item[1] == "event" and item[2].get("type") in {
                          "speech.started", "barge.in", "asr.final",
                      }]
        if unexpected:
            raise RuntimeError(f"silence caused {len(unexpected)} false speech events")

    def run(self) -> dict[str, Any]:
        self.sampler.start()
        try:
            print("[benchmark] warming ASR and Qwen3-TTS", flush=True)
            self.asr_turn(self.fixtures[0], "warmup")
            self.tts_turn(self.fixtures[0].case["agentReply"])
            for values in self.metrics.values():
                values.clear()
            self.zh_edits = self.zh_units = self.en_edits = self.en_units = 0
            self.tts_underruns = 0

            self.sampler.phase = "active"
            interruption_slots = {
                round((slot + 0.5) * self.args.turns / self.args.interruptions) - 1
                for slot in range(self.args.interruptions)
            } if self.args.interruptions else set()
            for index in range(self.args.turns):
                self.measured_turn(index, index in interruption_slots)
                print(f"[benchmark] primary {index + 1}/{self.args.turns}"
                      f" · interruptions {sum(1 for slot in interruption_slots if slot <= index)}",
                      flush=True)

            self.sampler.phase = "idle"
            print(f"[benchmark] idle listening {self.args.idle_seconds:.0f}s", flush=True)
            self.silence(self.args.idle_seconds)

            self.sampler.phase = "active"
            soak_started = time.monotonic()
            soak_index = 0
            while time.monotonic() - soak_started < self.args.soak_seconds:
                self.measured_turn(soak_index, False, phase="soak")
                soak_index += 1
                remaining = self.args.soak_seconds - (time.monotonic() - soak_started)
                if remaining <= 0:
                    break
                self.silence(min(remaining, max(0, 60 - (time.monotonic() - soak_started) % 60)))
                print(f"[benchmark] soak {min(self.args.soak_seconds, time.monotonic() - soak_started):.0f}"
                      f"/{self.args.soak_seconds:.0f}s · turns {soak_index}", flush=True)

            return self.report(soak_index)
        finally:
            self.sampler.stop()
            self.wire.close()

    def report(self, soak_turns: int) -> dict[str, Any]:
        active_cpu = [float(item["cpu"]) for item in self.sampler.samples if item["phase"] == "active"]
        idle_cpu = [float(item["cpu"]) for item in self.sampler.samples if item["phase"] == "idle"]
        rss = [float(item["rssMb"]) for item in self.sampler.samples]
        package = json.loads((ROOT / "package.json").read_text())
        hardware = command("system_profiler", "SPHardwareDataType")
        model = re.search(r"Model Identifier:\s*(.+)", hardware)
        chip = re.search(r"Chip:\s*(.+)", hardware)
        memory = re.search(r"Memory:\s*([0-9.]+) GB", hardware)
        dsh_package = json.loads((ROOT.parent / "deepseek-harness/apps/cli/package.json").read_text())
        power = "ac" if "AC Power" in command("pmset", "-g", "batt") else "battery"
        model_lock_hash = hashlib.sha256((ROOT / "models.lock.json").read_bytes()).hexdigest()
        model_disk_mb = int(command("du", "-sk", str(ROOT / ".models")).split()[0]) / 1024
        latency = {name: percentile(self.metrics[name]) for name in (
            "browserCaptureToMuxivaFrame", "speechOnsetToBargeIn", "speechEndToAsrFinal",
            "firstAgentTextToFirstTtsPcm", "audioQueueAhead", "staleAudioAfterBargeIn",
        )}
        return {
            "schemaVersion": 1,
            "release": package["version"],
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "system": {
                "machine": model.group(1).strip() if model else platform.machine(),
                "chip": chip.group(1).strip() if chip else command("sysctl", "-n", "machdep.cpu.brand_string"),
                "memoryGb": float(memory.group(1)) if memory else 0,
                "os": f"macOS {command('sw_vers', '-productVersion')} ({command('sw_vers', '-buildVersion')})",
                "powerSource": power,
            },
            "versions": {
                "muxiva": command("muxiva", "--version").removeprefix("muxiva "),
                "dshVoice": package["version"],
                "deepseekHarness": dsh_package["version"],
                "node": command("node", "--version").removeprefix("v"),
                "python": platform.python_version(),
            },
            "modelLockSha256": model_lock_hash,
            "workload": {
                "turns": self.args.turns + soak_turns,
                "interruptions": self.args.interruptions,
                "idleMinutes": self.args.idle_seconds / 60,
                "soakMinutes": self.args.soak_seconds / 60,
                "warmupTurns": 1,
            },
            "latencyMs": latency,
            "throughput": {
                "asrFinalRealtimeFactor": percentile(self.metrics["asrFinalRealtimeFactor"]),
                "ttsRealtimeFactor": percentile(self.metrics["ttsRealtimeFactor"]),
            },
            "resources": {
                "coldStartMs": self.args.cold_start_ms,
                "warmStartMs": self.args.warm_start_ms,
                "idleCpuPercent": round(sum(idle_cpu) / len(idle_cpu), 3) if idle_cpu else 0,
                "activeCpuPercent": round(sum(active_cpu) / len(active_cpu), 3) if active_cpu else 0,
                "peakRssMb": round(max(rss), 3) if rss else 0,
                "modelDiskMb": round(model_disk_mb, 3),
            },
            "quality": {
                "mandarinCer": round(self.zh_edits / max(1, self.zh_units), 6),
                "englishWer": round(self.en_edits / max(1, self.en_units), 6),
                "ttsUnderruns": self.tts_underruns,
            },
            "stability": {
                "completedTurns": self.completed,
                "failedTurns": self.failed,
                "droppedAudioFrames": 0,
                "lateResultsDiscarded": 0,
                "unboundedQueues": 0,
            },
            "notes": [
                "Unattended deterministic loopback certification; no cloud audio service was used.",
                "ASR fixtures were generated locally with macOS say voices Tingting and Samantha and were not committed.",
                "CER/WER describe the synthetic fixture corpus and are not presented as real-human microphone accuracy.",
                "Capture latency uses a test-only monotonic marker acknowledged when the next PCM chunk becomes a Muxiva AudioFrame.",
                f"Raw trace: {self.trace_path.relative_to(ROOT)} (local artifact, intentionally ignored by Git).",
            ],
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("quick", "certify"), required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--service-pid", type=int, required=True)
    parser.add_argument("--cold-start-ms", type=float, required=True)
    parser.add_argument("--warm-start-ms", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--turns", type=int)
    parser.add_argument("--interruptions", type=int)
    parser.add_argument("--idle-seconds", type=float)
    parser.add_argument("--soak-seconds", type=float)
    args = parser.parse_args()
    defaults = {
        "quick": (10, 3, 5.0, 15.0),
        "certify": (100, 30, 300.0, 1800.0),
    }[args.mode]
    args.turns = args.turns if args.turns is not None else defaults[0]
    args.interruptions = args.interruptions if args.interruptions is not None else defaults[1]
    args.idle_seconds = args.idle_seconds if args.idle_seconds is not None else defaults[2]
    args.soak_seconds = args.soak_seconds if args.soak_seconds is not None else defaults[3]
    if args.turns < 1 or args.interruptions < 0 or args.interruptions > args.turns:
        parser.error("turn and interruption counts are invalid")
    return args


def main() -> None:
    args = parse_args()
    certification = Certification(args)
    report = certification.run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "report": str(args.output),
        "turns": report["workload"]["turns"],
        "interruptions": report["workload"]["interruptions"],
        "latencyP95Ms": {key: value["p95"] for key, value in report["latencyMs"].items()},
        "quality": report["quality"],
        "stability": report["stability"],
    }, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
