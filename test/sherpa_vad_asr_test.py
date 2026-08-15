from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import types
import unittest


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


class SherpaVadAsrTests(unittest.TestCase):
    def test_vad_candidate_does_not_interrupt_until_asr_has_text(self):
        node = module.SherpaVadAsr({"barge_in_min_chars": 1})
        ctx = Context()

        node._preview(ctx, 8, "")
        self.assertEqual(ctx.signals, [])

        node._preview(ctx, 8, "你")
        self.assertEqual(len(ctx.signals), 1)
        self.assertEqual(ctx.signals[0][0], "muxiva.voice.barge_in.confirmed")
        self.assertEqual(ctx.signals[0][1]["stage"], "partial")
        self.assertEqual(ctx.counters["barge_in.confirmed"], 1)

        node._preview(ctx, 8, "你好")
        self.assertEqual(len(ctx.signals), 1, "one utterance must confirm barge-in only once")

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
