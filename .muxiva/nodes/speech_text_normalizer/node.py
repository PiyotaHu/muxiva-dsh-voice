"""Muxiva Node Pack for TTS text normalization."""

from __future__ import annotations

from typing import Any

import muxiva

from muxiva_voice_transport.speech_text import normalize_for_speech


class SpeechTextNormalizer:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    def on_process(self, frame, ctx) -> None:
        if frame is None or not hasattr(frame, "text"):
            return
        text = normalize_for_speech(
            frame.text,
            language=str(self.config.get("language", "auto")),
            code_message=str(self.config.get(
                "code_message",
                "代码已经生成，请在聊天窗口查看。",
            )),
        )
        if text:
            ctx.emit("text_out", muxiva.TextFrame(text, sequence=frame.sequence))
