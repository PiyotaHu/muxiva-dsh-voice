# Getting started

## 1. Verify the machine

```bash
npx @muxiva/dsh-voice doctor
```

Every row must pass. `doctor --fix` creates only this project's `.muxiva/venv`; it does not alter system Python.

## 2. Install local inference

```bash
npx @muxiva/dsh-voice setup
```

The downloader verifies every artifact before activation. An interrupted `curl` transfer resumes from its `.partial` file, while the Qwen3-TTS snapshot resumes through the Hugging Face cache. The default download is about 2.5 GB; local model files use about 2.3 GiB and the isolated Python environment about 700 MiB on the M1 Pro certification machine.

## 3. Install the DSH Bundle

```bash
dsh plugin --profile web add @muxiva/dsh-voice
dsh --profile web --dump-config
```

The dump must contain a `# == @muxiva/dsh-voice` layer and the `muxiva-dsh-voice` row.

## 4. Run and speak

Start `muxiva-dsh-voice start`, start `dsh --profile web`, open a session, and select the large voice orb above the composer. Use headphones for the cleanest full-duplex certification run.

The default is a low-overhead headless Runtime. For an observable development run, use
`muxiva-dsh-voice start --observe` (or `npm run observe` from a checkout), select **Run** in
the opened Studio, then open **◎ Observe**. Studio reports per-Node process latency and
throughput, per-Edge rates and queue age, Node-owned buffers, traces and hotspot verdicts.
Use `--no-observe` or `npm run start:headless` when Studio should stay off.
Both modes persist supervisor, bridge, Runtime and Node Host output in
`.muxiva/runtime.log`; use `tail -f .muxiva/runtime.log` for unattended diagnosis.

After connection, selecting the large orb toggles microphone mute/unmute while keeping the
AudioWorklet, WebSocket and Graph alive. Use the small **End** button only when you want to
tear down the local voice session.

Before opening DSH, you can certify the complete local model path without a cloud model or microphone:

```bash
npm run test:e2e
```

The test synthesizes a Chinese sentence, routes all resulting browser PCM back as microphone audio, and requires an exact SenseVoice final. It then sends the upstream English fixture and requires a valid English final.

## 5. Tune

Edit `graph.json` in Muxiva Studio, or override the Node configuration:

- `vad_threshold`: lower hears quieter speech; the false-trigger-resistant default is `0.60`.
- `min_speech_seconds`: candidates shorter than this are rejected; `0.25` is the default.
- `min_silence_seconds`: lower commits faster but may split sentences; `0.40` is the default.
- `barge_in_min_chars`: number of non-space preview characters required to confirm interruption; `1` is the default. VAD alone never cancels playback or the Agent turn.
- `final_language`: `auto` detects Chinese or English; pin `zh` or `en` only for a language-specific deployment.
- `speaker`: `Vivian` is the default Mandarin voice. Other bundled voices are `Serena`, `Uncle_Fu`, `Dylan`, `Eric`, `Ryan`, `Aiden`, `Ono_Anna`, and `Sohee`.
- `language`: keep `Auto` for mixed Chinese and English; use `Chinese` or `English` only for a language-specific deployment.
- `instruct`: controls speaking style. The default asks for a natural, warm and clear conversational delivery.
- `streaming_interval`: `0.32` seconds balances first-audio latency and MLX overhead on the M1 Pro certification target.
- `pcm_chunk_ms`: emits 40 ms PCM16 chunks to the browser scheduler after each model chunk arrives.

`muxiva.speech_text_normalizer` is a project Node Pack between the built-in streaming Markdown formatter and TTS. It removes emoji and residual display syntax, preserves link labels, and speaks Chinese years, integers, decimals and percentages deterministically. It uses the public Node Pack mechanism and requires no Muxiva Runtime change.
