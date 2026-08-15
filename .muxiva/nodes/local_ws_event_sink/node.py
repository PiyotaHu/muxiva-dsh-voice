from __future__ import annotations

import json
from muxiva_voice_transport import client


class LocalWsEventSink:
    TOPIC_MAP = {
        "muxiva.voice.speech.started": "speech.started",
        "muxiva.voice.speech.stopped": "speech.stopped",
        "muxiva.voice.barge_in.confirmed": "barge.in",
        "muxiva.voice.transcript.preview": "asr.partial",
        "muxiva.voice.transcript.completed": "asr.final",
        "muxiva.voice.transcript.rejected": "asr.rejected",
        "muxiva.voice.tts.started": "tts.started",
        "muxiva.voice.tts.stopped": "tts.stopped",
    }

    def __init__(self, config=None):
        self.bridge = None

    def on_prepare(self, _ctx=None):
        self.bridge = client("event-sink")

    def on_process(self, frame, ctx):
        topic = getattr(frame, "topic", "")
        kind = self.TOPIC_MAP.get(topic)
        if kind is None:
            return
        try:
            payload = json.loads(getattr(frame, "payload", "{}"))
        except json.JSONDecodeError:
            payload = {}
        self.bridge.send(json.dumps({"version":"muxiva.dsh.voice/v1","type":kind,**payload}, ensure_ascii=False, separators=(",", ":")))
        ctx.increment_counter(f"events.{kind.replace('.', '_')}")

    def on_finish(self, _ctx=None):
        if self.bridge is not None:
            self.bridge.close()
            self.bridge = None

    def on_abort(self, _reason, ctx=None):
        self.on_finish(ctx)
