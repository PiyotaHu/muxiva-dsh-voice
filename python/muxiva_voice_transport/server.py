from __future__ import annotations

import json
import os
import signal
import threading
import time
from urllib.parse import parse_qs, urlparse

from websockets.sync.server import serve

VERSION = "muxiva.dsh.voice/v1"
ROLES = {"audio-source", "text-source", "audio-sink", "event-sink"}


class Endpoint:
    def __init__(self, websocket) -> None:
        self.websocket = websocket
        self.lock = threading.Lock()

    def send(self, message: str | bytes) -> bool:
        try:
            with self.lock:
                self.websocket.send(message)
            return True
        except Exception:
            return False


class Router:
    def __init__(self, token: str) -> None:
        self.token = token
        self.lock = threading.Lock()
        self.browser: Endpoint | None = None
        self.nodes: dict[str, Endpoint] = {}

    def handler(self, websocket) -> None:
        request = websocket.request
        parsed = urlparse(request.path)
        if parsed.path == "/voice":
            self.browser_handler(websocket)
            return
        if parsed.path == "/node":
            query = parse_qs(parsed.query)
            role = query.get("role", [""])[0]
            token = query.get("token", [""])[0]
            if role not in ROLES or token != self.token:
                websocket.close(1008, "invalid internal bridge credential")
                return
            self.node_handler(role, websocket)
            return
        websocket.close(1008, "unknown voice bridge path")

    def browser_handler(self, websocket) -> None:
        endpoint = Endpoint(websocket)
        with self.lock:
            if self.browser is not None:
                websocket.close(1013, "only one browser voice session is supported")
                return
            self.browser = endpoint
        endpoint.send(json.dumps({"version": VERSION, "type": "server.ready", "sampleRateHz": 24000}))
        try:
            for message in websocket:
                if isinstance(message, bytes):
                    if message and len(message) <= 32_768 and len(message) % 2 == 0:
                        self.to_node("audio-source", message)
                    continue
                value = json.loads(message)
                if value.get("version") != VERSION or not isinstance(value.get("type"), str):
                    websocket.close(1008, "unsupported voice protocol")
                    return
                if value["type"] in {
                    "agent.delta", "agent.final", "agent.cancel",
                    "client.mute", "client.unmute", "client.stop",
                }:
                    self.to_node("text-source", message)
                if value["type"] in {
                    "client.mute", "client.unmute", "client.stop",
                    "benchmark.audio.marker",
                }:
                    print(f"[MUXIVA][VOICE][source.control] type={value['type']}", flush=True)
                    self.to_node("audio-source", message)
        finally:
            with self.lock:
                if self.browser is endpoint:
                    self.browser = None

    def node_handler(self, role: str, websocket) -> None:
        endpoint = Endpoint(websocket)
        with self.lock:
            previous = self.nodes.get(role)
            if previous is not None:
                websocket.close(1013, f"node role `{role}` is already connected")
                return
            self.nodes[role] = endpoint
        try:
            for message in websocket:
                if role == "audio-sink" and isinstance(message, bytes):
                    self.to_browser(message)
                elif role == "event-sink" and isinstance(message, str):
                    self.log_voice_event(message)
                    self.to_browser(message)
        finally:
            with self.lock:
                if self.nodes.get(role) is endpoint:
                    del self.nodes[role]

    def to_node(self, role: str, message: str | bytes) -> None:
        with self.lock:
            target = self.nodes.get(role)
        if target is not None:
            target.send(message)

    def to_browser(self, message: str | bytes) -> None:
        with self.lock:
            target = self.browser
        if target is not None:
            target.send(message)

    @staticmethod
    def log_voice_event(message: str) -> None:
        try:
            event = json.loads(message)
        except json.JSONDecodeError:
            print("[MUXIVA][VOICE][event.invalid] reason=invalid-json", flush=True)
            return
        diagnostic = {
            key: event[key]
            for key in ("stage", "reason", "processing_ms", "text_chars")
            if key in event
        }
        print(
            f"[MUXIVA][VOICE][event] type={event.get('type', 'unknown')}"
            f" metadata={json.dumps(diagnostic, ensure_ascii=False, separators=(',', ':'))}",
            flush=True,
        )


def main() -> None:
    token = os.environ.get("MUXIVA_DSH_BRIDGE_TOKEN", "")
    if len(token) < 32:
        raise RuntimeError("bridge token must contain at least 32 characters")
    public_port = int(os.environ.get("MUXIVA_DSH_BRIDGE_PUBLIC_PORT", "4390"))
    internal_port = int(os.environ.get("MUXIVA_DSH_BRIDGE_INTERNAL_PORT", "4391"))
    router = Router(token)

    # A detached bridge avoids terminal SIGINT racing Muxiva's ordered shutdown.
    # If the Node supervisor is terminated by a package runner, fail closed with it.
    supervisor_pid = os.getppid()

    def watch_supervisor() -> None:
        while os.getppid() == supervisor_pid:
            time.sleep(0.25)
        os.kill(os.getpid(), signal.SIGTERM)

    threading.Thread(target=watch_supervisor, name="muxiva-voice-supervisor", daemon=True).start()
    try:
        with serve(router.handler, "127.0.0.1", public_port, max_size=262_144, compression=None) as public_server, serve(
            router.handler, "127.0.0.1", internal_port, max_size=262_144, compression=None
        ) as internal_server:
            internal_thread = threading.Thread(target=internal_server.serve_forever, name="muxiva-voice-internal", daemon=True)
            internal_thread.start()
            print(f"[MUXIVA][VOICE][bridge.ready] public=ws://127.0.0.1:{public_port}/voice internal=127.0.0.1:{internal_port}", flush=True)
            public_server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
