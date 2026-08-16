# Muxiva Voice for DeepSeek Harness

Local-first, full-duplex voice for the official [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness), orchestrated by [Muxiva](https://github.com/PiyotaHu/muxiva).

Your microphone, VAD, ASR, sentence scheduling, TTS, playback and interruption path stay on the Mac. DSH remains the stateful Agent harness and keeps its tools, sessions and Web transcript.

> Alpha: public npm installation, the integration contract and unattended M1 Pro certification are complete. Muxiva 0.1.1 wheels are published for CPython 3.8–3.14, including macOS universal2. DSH rc.5 and rc.6 are supported; alpha.2 is certified against rc.6.

## What runs where

```text
DSH Web microphone ──PCM16──▶ Muxiva Graph
                              ├─ Silero VAD ──barge-in──┐
                              ├─ Zipformer ──preview─────┤
                              └─ SenseVoice zh/en final─┼─▶ DSH Session / Agent / Tools
DSH assistant deltas ─────────▶ sentence buffer ─▶ speech formatter ─▶ speech normalizer ─▶ Qwen3-TTS / MLX ─▶ browser speaker
```

- **Muxiva owns the real-time pipeline:** typed Frames, bounded queues, backpressure, Signals, cancellation and observability.
- **DSH owns the Agent:** session history, model selection, tools, permissions and Web UI.
- **The plugin owns only the bridge:** additive DSH UI, a versioned loopback protocol and project Node Packs. Neither upstream repository is patched.

## Install the alpha (Apple Silicon)

Prerequisites: macOS arm64, Node.js 22.19+, Python 3.11–3.13, the Muxiva 0.1.1 CLI, and the official DSH CLI.

```bash
dsh plugin --profile web add @muxiva/dsh-voice@alpha
npx @muxiva/dsh-voice@alpha setup
npx @muxiva/dsh-voice@alpha start
```

Run `dsh --profile web` in a second terminal. Models, the isolated Python environment and logs are stored outside the `npx` cache in the stable OS user-data directory. Print it with `npx @muxiva/dsh-voice@alpha home`, or override it with `MUXIVA_DSH_VOICE_HOME`.

## Develop from source

Prerequisites: macOS arm64, Node.js 22.19+, Python 3.11–3.13, Rust, Muxiva source at `../muxiva`, the `muxiva` CLI, and an installed official DSH CLI.

```bash
git clone https://github.com/PiyotaHu/muxiva-dsh-voice.git
cd muxiva-dsh-voice

# Build the project Python environment and fetch revision- and SHA-256-pinned models.
npm run doctor -- --fix
npm run models

# Install this checkout as a DSH Bundle. No prepare script is executed.
dsh plugin --profile web add .
```

Start the two supervised processes. Headless mode is the normal low-overhead product path:

```bash
# Terminal A
npm start

# Terminal B
dsh --profile web
```

For local diagnosis, replace `npm start` with `npm run observe`. It opens the same
`graph.json` in Muxiva Studio while keeping the authenticated DSH loopback bridge supervised.
Select **Run**, then open **◎ Observe** for live per-Node latency and throughput, per-Edge queue
age and rates, Node-owned buffers, traces and hotspot verdicts. `npm run start:headless` is the
explicit non-Studio form; `npm start` remains headless by default.
Both modes append bridge and Runtime output to `.muxiva/runtime.log`; use
`tail -f .muxiva/runtime.log` when diagnosing a headless session.

Open the printed DSH URL, create or open a session, then select the large voice orb above the composer. Its halo follows input energy and the visible status moves through listening, hearing, thinking and speaking. Once connected, the large orb toggles microphone mute without stopping the WebSocket, AudioWorklet or Graph. Muting admits no PCM, explicitly pauses the Muxiva audio Source, and resets VAD/ASR before resume; the small **End** control performs a full shutdown. VAD onset is advisory; only a non-empty ASR partial or an admitted multilingual Final confirms barge-in, cancels old playback and the active Agent turn. Rejected noise returns to listening instead of prompting DSH.

The reliability-first defaults wait for 2 seconds of continuous silence before emitting ASR Final, use a `0.75` VAD threshold with a 350 ms minimum-speech gate, and prepend 500 ms before Silero's segment start so SenseVoice does not lose quiet opening syllables. SenseVoice Finals admit only Chinese and English speech with meaningful text, rejecting non-speech events and Japanese/Korean noise hallucinations. Display-only emoji and brackets become prosodic pauses instead of gluing adjacent words. Qwen3-TTS uses `Serena` with a fixed calm prosody profile and conservative sampling. A two-stage context policy starts one early 48–96-character phrase, then synthesizes the entire remaining Agent Final as one context; short answers use one call and long answers use at most two. This avoids both full-answer startup latency and repeated per-sentence prosody resets. Bounded real-time PCM pacing prevents the playback queue from growing without limit.

The package is a native DSH Bundle (`dsh.bundle`) and a dual-face Web plugin (`dsh.client`). Discovery uses the GitHub [`dsh-plugin`](https://github.com/topics/dsh-plugin) topic; DSH does not currently operate a centralized plugin marketplace.

## Security posture

- The speech bridge binds only to loopback and accepts one active client.
- Model artifacts are pinned by immutable revision/URL; the Qwen3-TTS weights and tokenizer are SHA-256 verified.
- No API key, microphone recording or transcript is uploaded by this plugin.
- Browser echo cancellation, noise suppression and automatic gain control are requested.
- Queue capacities are finite; stale TTS and Agent output are fenced after barge-in.
- The DSH plugin adds UI through a documented slot and uses only `Session.prompt` / `Session.cancel`; it never changes the agent loop.

See the [compatibility matrix](docs/guide/compatibility.md), [security model](docs/reference/security.md), [protocol](docs/reference/protocol.md), [model licenses](THIRD_PARTY_NOTICES.md), and [contribution guide](CONTRIBUTING.md).

## Development

```bash
npm test
npm run pack:smoke
python3 -m compileall -q python .muxiva/nodes

# After setup/models: certifies Qwen3-TTS Chinese loopback and English ASR.
npm run test:e2e

# Deterministic release-grade workload (about 40 minutes on the M1 Pro).
npm run benchmark:certify
```

The first M1 Pro certification completed 130/130 turns and 30/30 interruptions with zero TTS underruns. Latency distributions, resource use, CER/WER scope and reproduction commands live in [Performance](docs/guide/performance.md).

## License

Apache-2.0. Models remain under their own licenses and are downloaded at setup time; they are not redistributed in the npm package.
