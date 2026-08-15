from __future__ import annotations

import json
import muxiva
from muxiva_voice_transport import client


class LocalWsTextSource:
    def __init__(self, config=None):
        self.sequence = 0
        self.bridge = None

    def on_prepare(self, _ctx=None):
        self.bridge = client("text-source")

    def on_process(self, _frame, ctx):
        emitted = 0
        while emitted < 16:
            try:
                wire = self.bridge.recv()
            except Exception:
                raise
            if wire is None:
                break
            if not isinstance(wire, str):
                continue
            item = json.loads(wire)
            kind = item.get("type", "")
            text = str(item.get("text", "")).strip()
            self.sequence += 1
            if kind in {"agent.cancel", "client.stop"}:
                ctx.emit_signal("muxiva.voice.barge_in.confirmed", {"source": "dsh-browser", "reason": kind})
            elif kind in {"client.mute", "client.unmute"}:
                muted = kind == "client.mute"
                ctx.publish_notification("muxiva.voice.microphone.state", {"muted": muted})
                ctx.set_gauge("microphone.muted", 1 if muted else 0)
            elif text:
                ctx.emit("text_out", muxiva.TextFrame(text, sequence=self.sequence))
                ctx.emit("event_out", muxiva.EventFrame(
                    "muxiva.agent.text", json.dumps({"final": kind == "agent.final"}),
                    source="muxiva.dsh.local_ws_text_source", sequence=self.sequence,
                ))
            emitted += 1
        ctx.schedule_next_tick(10)

    def on_finish(self, _ctx=None):
        if self.bridge is not None:
            self.bridge.close()
            self.bridge = None

    def on_abort(self, _reason, ctx=None):
        self.on_finish(ctx)
