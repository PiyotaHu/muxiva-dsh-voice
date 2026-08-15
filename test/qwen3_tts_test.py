from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import threading
import time
import types
import unittest
from array import array


class FakeArray(list):
    def reshape(self, *_):
        return self

    def __mul__(self, value):
        return FakeArray(item * value for item in self)

    def astype(self, _dtype):
        return self

    def tobytes(self):
        return array("h", (max(-32768, min(32767, int(item))) for item in self)).tobytes()


fake_numpy = types.ModuleType("numpy")
fake_numpy.float32 = "float32"
fake_numpy.int16 = "int16"
fake_numpy.asarray = lambda values, dtype=None: FakeArray(values)
fake_numpy.clip = lambda values, low, high: FakeArray(max(low, min(high, item)) for item in values)
sys.modules["numpy"] = fake_numpy


class AudioFrame:
    def __init__(self, data, sample_rate_hz, channels=1, sequence=0, *_, **__):
        self.data = data
        self.sample_rate_hz = sample_rate_hz
        self.channels = channels
        self.sequence = sequence


class TextFrame:
    def __init__(self, text, sequence=0):
        self.text = text
        self.sequence = sequence


class EventFrame:
    def __init__(self, topic, payload="", source="", sequence=0, **_):
        self.topic = topic
        self.payload = payload
        self.source = source
        self.sequence = sequence


shim = types.ModuleType("muxiva")
shim.AudioFrame = AudioFrame
shim.TextFrame = TextFrame
shim.EventFrame = EventFrame
sys.modules["muxiva"] = shim

node_path = pathlib.Path(__file__).parents[1] / ".muxiva/nodes/qwen3_tts/node.py"
spec = importlib.util.spec_from_file_location("muxiva_qwen3_tts_node", node_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Result:
    def __init__(self, audio, sample_rate=24_000):
        self.audio = audio
        self.sample_rate = sample_rate


class Context:
    def __init__(self):
        self.emissions = []
        self.notifications = []
        self.scheduled_ticks = []

    def emit(self, port, frame):
        self.emissions.append((port, frame))

    def publish_notification(self, topic, payload):
        self.notifications.append((topic, payload))

    def schedule_next_tick(self, delay_ms):
        self.scheduled_ticks.append(delay_ms)


def wait_until(predicate, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return predicate()


class Qwen3TtsTests(unittest.TestCase):
    def test_streams_pcm_and_emits_qwen_state(self):
        calls = []

        class Model:
            def generate_custom_voice(self, **kwargs):
                calls.append(kwargs)
                yield Result([0.0, 0.5, -0.5, 1.0])
                yield Result([0.25, -0.25])

        node = module.Qwen3Tts({
            "speaker": "Vivian",
            "language": "Chinese",
            "instruct": "自然地说。",
            "streaming_interval": 0.32,
            "pcm_chunk_ms": 20,
        }, lambda _: Model())
        node.on_prepare()
        ctx = Context()
        node.on_process(TextFrame("你好，Muxiva。", sequence=42), ctx)
        self.assertTrue(wait_until(lambda: not node.results.empty()))
        while node.pending or not node.results.empty():
            node.on_process(None, ctx)
            time.sleep(0.005)
        node.on_finish()

        audio = [frame for port, frame in ctx.emissions if port == "audio_out"]
        events = [frame for port, frame in ctx.emissions if port == "event_out"]
        self.assertEqual(len(audio), 2)
        self.assertTrue(all(frame.sample_rate_hz == 24_000 for frame in audio))
        self.assertEqual(audio[0].sequence, 42)
        self.assertEqual([frame.topic for frame in events], [
            "muxiva.voice.tts.started",
            "muxiva.voice.tts.stopped",
        ])
        self.assertEqual(json.loads(events[0].payload)["engine"], "qwen3-tts-mlx")
        self.assertEqual(calls[0], {
            "text": "你好，Muxiva。",
            "speaker": "Vivian",
            "language": "Chinese",
            "instruct": "自然地说。",
            "stream": True,
            "streaming_interval": 0.32,
        })

    def test_barge_in_discards_stale_audio(self):
        first_chunk_ready = threading.Event()
        release = threading.Event()

        class Model:
            def generate_custom_voice(self, **_):
                yield Result([0.2] * 960)
                first_chunk_ready.set()
                release.wait(timeout=1)
                yield Result([0.4] * 960)

        node = module.Qwen3Tts({}, lambda _: Model())
        node.on_prepare()
        ctx = Context()
        node.on_process(TextFrame("旧回答", sequence=7), ctx)
        self.assertTrue(first_chunk_ready.wait(timeout=1))
        node.on_signal(types.SimpleNamespace(name="muxiva.voice.speech.started"))
        release.set()
        self.assertTrue(wait_until(lambda: node.jobs.empty()))
        node.on_process(None, ctx)
        node.on_finish()

        self.assertFalse(any(port == "audio_out" for port, _ in ctx.emissions))
        self.assertEqual(node.pending, 0)

    def test_abort_is_non_blocking_for_out_of_process_host_shutdown(self):
        started = threading.Event()
        release = threading.Event()

        class Model:
            def generate_custom_voice(self, **_):
                started.set()
                release.wait(timeout=0.15)
                yield Result([0.1] * 32)

        node = module.Qwen3Tts({}, lambda _: Model())
        node.on_prepare()
        node.on_process(TextFrame("即将取消", sequence=9), Context())
        self.assertTrue(started.wait(timeout=1))

        before = time.monotonic()
        node.on_abort("runtime shutdown")
        self.assertLess(time.monotonic() - before, 0.5)
        self.assertTrue(node.closing.is_set())
        release.set()
        self.assertFalse(node.worker.is_alive())


if __name__ == "__main__":
    unittest.main()
