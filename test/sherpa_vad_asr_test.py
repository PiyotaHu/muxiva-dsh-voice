from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import types
import unittest
from collections import deque


if "muxiva" not in sys.modules:
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
    shim.TextFrame = TextFrame
    shim.EventFrame = EventFrame
    sys.modules["muxiva"] = shim


node_path = pathlib.Path(__file__).parents[1] / ".muxiva/nodes/sherpa_vad_asr/node.py"
spec = importlib.util.spec_from_file_location("muxiva_sherpa_vad_asr_node", node_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Context:
    def __init__(self):
        self.emissions = []
        self.notifications = []
        self.signals = []
        self.counters = {}
        self.gauges = {}

    def emit(self, port, frame):
        self.emissions.append((port, frame))

    def emit_signal(self, name, payload):
        self.signals.append((name, payload))

    def publish_notification(self, topic, payload):
        self.notifications.append((topic, payload))

    def increment_counter(self, name, value=1):
        self.counters[name] = self.counters.get(name, 0) + value

    def set_gauge(self, name, value):
        self.gauges[name] = value


class Stream:
    def input_finished(self):
        pass


class Recognizer:
    @staticmethod
    def is_ready(_stream):
        return False

    @staticmethod
    def get_result(_stream):
        return ""

    @staticmethod
    def create_stream():
        return Stream()


class Numpy:
    float32 = "float32"

    @staticmethod
    def empty(_size, dtype=None):
        return []

    @staticmethod
    def concatenate(parts):
        output = []
        for part in parts:
            output.extend(part)
        return output

    @staticmethod
    def array(values, dtype=None, copy=False):
        return list(values)


class Vad:
    def __init__(self):
        self.resets = 0

    def reset(self):
        self.resets += 1


class SherpaVadAsrTests(unittest.TestCase):
    def test_final_utterance_recovers_half_second_before_silero_start(self):
        node = module.SherpaVadAsr({"pre_roll_seconds": 0.5})
        node.np = Numpy()
        history = [0.0] * 4_800 + [0.02] * 19_200
        node.audio_history = deque([(0, history)])
        node.audio_history_start = 0
        ctx = Context()

        result = node._prepend_pre_roll(8_000, [0.9, 1.0], ctx)

        self.assertEqual(result[:1_600], [0.0] * 1_600, "retain 100 ms before the weak onset")
        self.assertEqual(result[1_600:4_800], [0.02] * 3_200)
        self.assertEqual(result[-2:], [0.9, 1.0])
        self.assertEqual(len(result), 4_802)
        self.assertEqual(ctx.gauges["asr.pre_roll_candidate_samples"], 8_000)
        self.assertEqual(ctx.gauges["asr.pre_roll_samples"], 4_800)
        self.assertEqual(ctx.gauges["asr.pre_roll_ms"], 300.0)

    def test_pre_roll_respects_trimmed_absolute_history_without_duplication(self):
        node = module.SherpaVadAsr({"pre_roll_seconds": 0.5})
        node.np = Numpy()
        node.audio_history = deque([(15_500, [0.02] * 1_000)])
        node.audio_history_start = 15_500

        result = node._prepend_pre_roll(16_000, [0.7, 0.8])

        self.assertEqual(result[:500], [0.02] * 500)
        self.assertEqual(result[499:502], [0.02, 0.7, 0.8])

    def test_pre_roll_drops_pure_room_silence(self):
        node = module.SherpaVadAsr({"pre_roll_seconds": 0.5})
        node.np = Numpy()
        node.audio_history = deque([(0, [0.001] * 8_000)])

        result = node._prepend_pre_roll(8_000, [0.7, 0.8])

        self.assertEqual(result, [0.7, 0.8])

    def test_microphone_pause_rebuilds_all_streaming_state(self):
        node = module.SherpaVadAsr({})
        node.np = Numpy()
        node.vad = Vad()
        node.recognizer = Recognizer()
        node.stream = object()
        node.vad_buffer = [1, 2, 3]
        node.vad_offset = 99
        node.speaking = True
        node.barge_in_confirmed = True
        node.last_partial = "残留"
        ctx = Context()

        node.on_signal(types.SimpleNamespace(name="muxiva.voice.microphone.muted"), ctx)

        self.assertTrue(node.muted)
        self.assertEqual(node.vad.resets, 1)
        self.assertIsInstance(node.stream, Stream)
        self.assertEqual(node.vad_buffer, [])
        self.assertEqual(node.vad_offset, 0)
        self.assertFalse(node.speaking)
        self.assertFalse(node.barge_in_confirmed)
        self.assertEqual(node.last_partial, "")
        self.assertEqual(ctx.counters["asr.microphone_state_resets"], 1)
        self.assertEqual(ctx.gauges["microphone.muted"], 1)

        node.on_signal(types.SimpleNamespace(name="muxiva.voice.microphone.unmuted"), ctx)
        self.assertFalse(node.muted)
        self.assertEqual(node.vad.resets, 2)
        self.assertEqual(ctx.gauges["microphone.muted"], 0)

    def test_two_asr_characters_confirm_barge_in_once(self):
        node = module.SherpaVadAsr({"barge_in_min_chars": 2})
        ctx = Context()

        node._preview(ctx, 8, "你")
        self.assertEqual(ctx.signals, [])

        node._preview(ctx, 8, "你好")
        self.assertEqual(len(ctx.signals), 1)
        self.assertEqual(ctx.signals[0][0], "muxiva.voice.barge_in.confirmed")
        self.assertEqual(ctx.signals[0][1]["stage"], "partial")
        self.assertEqual(ctx.counters["barge_in.confirmed"], 1)

        node._preview(ctx, 8, "你好啊")
        self.assertEqual(len(ctx.signals), 1, "one utterance must confirm barge-in only once")

    def test_final_quality_gate_rejects_noise_languages_events_and_short_text(self):
        node = module.SherpaVadAsr({
            "accepted_final_languages": ["zh", "en"],
            "min_final_chars": 2,
        })

        def result(language, event):
            return types.SimpleNamespace(lang=f"<|{language}|>", event=f"<|{event}|>")

        self.assertEqual(node._final_rejection(result("ko", "Speech"), "그."), "unsupported_language")
        self.assertEqual(node._final_rejection(result("ja", "Speech"), "はい。"), "unsupported_language")
        self.assertEqual(node._final_rejection(result("en", "BGM"), "music"), "non_speech_event")
        self.assertEqual(node._final_rejection(result("en", "Speech"), "I."), "too_short")
        self.assertIsNone(node._final_rejection(result("zh", "Speech"), "你好。"))
        self.assertIsNone(node._final_rejection(result("en", "Speech"), "Hi."))

    def test_empty_vad_segment_is_rejected_and_returns_to_listening(self):
        node = module.SherpaVadAsr({})
        node.speaking = True
        node.stream = Stream()
        node.recognizer = Recognizer()
        ctx = Context()

        node._commit(ctx, 9, [])

        topics = [frame.topic for port, frame in ctx.emissions if port == "event_out"]
        self.assertEqual(topics, [
            "muxiva.voice.speech.stopped",
            "muxiva.voice.transcript.rejected",
        ])
        rejected = next(frame for port, frame in ctx.emissions if getattr(frame, "topic", "") == "muxiva.voice.transcript.rejected")
        self.assertEqual(json.loads(rejected.payload)["reason"], "no_text")
        self.assertEqual(ctx.signals, [])
        self.assertEqual(ctx.counters["asr.rejected"], 1)


if __name__ == "__main__":
    unittest.main()
