from __future__ import annotations

import os
import time
from urllib.parse import urlencode


class NodeClient:
    """Authenticated client used by one isolated Muxiva Python Node Host."""

    def __init__(self, role: str) -> None:
        from websockets.sync.client import connect

        token = os.environ.get("MUXIVA_DSH_BRIDGE_TOKEN", "")
        if len(token) < 32:
            raise RuntimeError("MUXIVA_DSH_BRIDGE_TOKEN is missing; start through `muxiva-dsh-voice start`")
        host = os.environ.get("MUXIVA_DSH_BRIDGE_INTERNAL_HOST", "127.0.0.1")
        port = int(os.environ.get("MUXIVA_DSH_BRIDGE_INTERNAL_PORT", "4391"))
        query = urlencode({"role": role, "token": token})
        last_error: Exception | None = None
        for _ in range(50):
            try:
                self.socket = connect(f"ws://{host}:{port}/node?{query}", max_size=262_144, compression=None)
                return
            except Exception as error:
                last_error = error
                time.sleep(0.1)
        raise RuntimeError(f"cannot connect Muxiva Node `{role}` to the supervised voice bridge: {last_error}")

    def recv(self) -> str | bytes | None:
        try:
            return self.socket.recv(timeout=0)
        except TimeoutError:
            return None

    def send(self, value: str | bytes) -> None:
        self.socket.send(value)

    def close(self) -> None:
        self.socket.close()


def client(role: str) -> NodeClient:
    return NodeClient(role)
