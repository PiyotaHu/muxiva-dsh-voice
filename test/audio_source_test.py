from __future__ import annotations

import importlib.util
import pathlib
import sys
import types
import unittest


class AudioFrame:
    def __init__(self, data, sample_rate_hz, channels=1, *args, sequence=0, **_kwargs):
        self.data = data
        self.sample_rate_hz = sample_rate_hz
        self.channels = channels
        self.sequence = sequence if sequence else (args[-1] if args else 0)


class EventFrame:
    def __init__(self, topic, payload="", source="", sequence=0, **_kwargs):
        self.topic = topic
        self.payload = payload
        self.source = source
        self.sequence = sequence


muxiva = types.ModuleType("muxiva")
muxiva.AudioFrame = AudioFrame
muxiva.EventFrame = EventFrame
transport = types.ModuleType("muxiva_voice_transport")
transport.client = lambda _role: None
previous_transport = sys.modules.get("muxiva_voice_transport")
sys.modules["muxiva"] = muxiva
sys.modules["muxiva_voice_transport"] = transport

node_path = pathlib.Path(__file__).parents[1] / ".muxiva/nodes/local_ws_audio_source/node.py"
spec = importlib.util.spec_from_file_location("muxiva_local_ws_audio_source_node", node_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
if previous_transport is None:
    del sys.modules["muxiva_voice_transport"]
else:
    sys.modules["muxiva_voice_transport"] = previous_transport


class Bridge:
    def __init__(self, messages):
        self.messages = list(messages)

    def recv(self):
        return self.messages.pop(0) if self.messages else None


class Context:
    def __init__(self):
        self.emissions = []
        self.signals = []
        self.counters = {}
        self.gauges = {}
        self.notifications = []

    def emit(self, port, frame):
        self.emissions.append((port, frame))

    def emit_signal(self, name, payload):
        self.signals.append((name, payload))

    def increment_counter(self, name, value=1):
        self.counters[name] = self.counters.get(name, 0) + value

    def set_gauge(self, name, value):
        self.gauges[name] = value

    def publish_notification(self, topic, payload):
        self.notifications.append((topic, payload))

    def schedule_next_tick(self, _delay_ms):
        pass


class AudioSourceTests(unittest.TestCase):
    def test_benchmark_marker_is_acknowledged_on_the_next_admitted_audio_frame(self):
        node = module.LocalWsAudioSource()
        node.bridge = Bridge([
            '{"type":"benchmark.audio.marker","markerId":"turn-7","capturedNs":123456}',
            b"\x01\x00" * 320,
        ])
        ctx = Context()

        node.on_process(None, ctx)

        audio = [frame for port, frame in ctx.emissions if port == "audio_out"]
        events = [frame for port, frame in ctx.emissions if port == "event_out"]
        self.assertEqual(len(audio), 1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].topic, "muxiva.voice.benchmark.audio_admitted")
        payload = __import__("json").loads(events[0].payload)
        self.assertEqual(payload["markerId"], "turn-7")
        self.assertEqual(payload["capturedNs"], 123456)
        self.assertGreaterEqual(payload["admittedNs"], 123456)
        self.assertEqual(ctx.counters["benchmark.markers_admitted"], 1)

    def test_pause_is_owned_by_source_and_drops_pcm_until_resume(self):
        node = module.LocalWsAudioSource()
        node.bridge = Bridge([
            b"\x01\x00" * 320,
            '{"type":"client.mute"}',
            b"\x02\x00" * 320,
            '{"type":"client.unmute"}',
            b"\x03\x00" * 320,
        ])
        ctx = Context()

        node.on_process(None, ctx)

        audio = [frame for port, frame in ctx.emissions if port == "audio_out"]
        self.assertEqual([frame.data[:2] for frame in audio], [b"\x01\x00", b"\x03\x00"])
        self.assertEqual([name for name, _ in ctx.signals], [
            "muxiva.voice.microphone.muted",
            "muxiva.voice.microphone.unmuted",
        ])
        self.assertFalse(node.paused)
        self.assertEqual(ctx.counters["ingress.audio_frames_dropped_paused"], 1)
        self.assertEqual(ctx.gauges["ingress.paused"], 0)
        self.assertEqual(ctx.notifications, [
            ("muxiva.voice.audio_source.state", {"paused": True}),
            ("muxiva.voice.audio_source.state", {"paused": False}),
        ])


if __name__ == "__main__":
    unittest.main()
