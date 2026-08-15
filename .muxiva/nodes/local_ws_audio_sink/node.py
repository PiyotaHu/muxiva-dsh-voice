from muxiva_voice_transport import client


class LocalWsAudioSink:
    def __init__(self, config=None):
        self.bridge = None

    def on_prepare(self, _ctx=None):
        self.bridge = client("audio-sink")

    def on_process(self, frame, ctx):
        self.bridge.send(bytes(frame.data))
        ctx.increment_counter("egress.audio_frames")

    def on_signal(self, signal, _ctx=None):
        if getattr(signal, "name", "") in {"muxiva.voice.barge_in.confirmed", "muxiva.voice.speech.started"}:
            return

    def on_finish(self, _ctx=None):
        if self.bridge is not None:
            self.bridge.close()
            self.bridge = None

    def on_abort(self, _reason, ctx=None):
        self.on_finish(ctx)
