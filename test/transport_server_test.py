from __future__ import annotations

import io
import sys
import types
import unittest
from contextlib import redirect_stdout

if "websockets.sync.server" not in sys.modules:
    websockets = types.ModuleType("websockets")
    sync = types.ModuleType("websockets.sync")
    server = types.ModuleType("websockets.sync.server")
    server.serve = lambda *_args, **_kwargs: None
    websockets.sync = sync
    sync.server = server
    sys.modules["websockets"] = websockets
    sys.modules["websockets.sync"] = sync
    sys.modules["websockets.sync.server"] = server

from muxiva_voice_transport.server import Router


class TransportServerTests(unittest.TestCase):
    def test_bridge_logs_event_metadata_without_transcript(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            Router.log_voice_event(
                '{"version":"muxiva.dsh.voice/v1","type":"asr.final",'
                '"text":"private transcript","processing_ms":123}'
            )

        line = output.getvalue()
        self.assertIn("type=asr.final", line)
        self.assertIn('"processing_ms":123', line)
        self.assertNotIn("private transcript", line)


if __name__ == "__main__":
    unittest.main()
