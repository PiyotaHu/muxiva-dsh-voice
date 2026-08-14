# Security model

## Trust boundaries

The DSH page may access the microphone only after a user gesture and browser permission. Audio crosses one loopback WebSocket into Muxiva. Model files execute through ONNX Runtime in the project Python Host. DSH receives committed text, not raw audio.

## Defaults

- loopback bind only;
- one active browser WebSocket client;
- a 256-bit per-launch token on the internal Node-Host bridge;
- 256 KiB maximum WebSocket message;
- 32 KiB maximum microphone chunk;
- bounded ingress, text and egress queues;
- no telemetry and no cloud fallback;
- immutable model revision plus SHA-256;
- no install-time npm scripts;
- project-local Python venv.

## Known alpha limitations

The loopback bridge currently relies on the local-machine trust boundary and single-client admission; it does not yet challenge the DSH page with a per-launch bearer token. Before a stable release, the Muxiva launcher will mint an ephemeral token and the DSH plugin will receive it without placing it in a URL or persistent browser storage.

Never bind the voice bridge to `0.0.0.0`. Do not expose it through a reverse proxy.
