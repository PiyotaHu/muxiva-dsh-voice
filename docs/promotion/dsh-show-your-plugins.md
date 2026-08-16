# Show Your Plugins: local, full-duplex voice for DSH, powered by Muxiva

I’m releasing **Muxiva Voice for DeepSeek Harness**: an open-source, local-first voice plugin for DSH Web on Apple Silicon.

It turns a DSH session into a full-duplex voice assistant while keeping the complete speech path on the Mac:

`browser mic → Silero VAD → streaming ASR preview → SenseVoice zh/en final → DSH Agent/Tools → text normalization → Qwen3-TTS/MLX → browser speaker`

What makes it different is the runtime underneath. This is not a callback chain around speech SDKs: Muxiva owns typed audio/text Frames, bounded queues, backpressure, cancellation Signals, generation fences, and live Node/Edge observability. DSH continues to own sessions, models, tools, permissions, and the Web transcript. Neither upstream repository is patched.

The interaction model includes:

- a large DSH Web voice orb with listening/hearing/thinking/speaking states;
- mute/unmute without tearing down Web Audio, WebSocket, Graph, or local models;
- ASR-confirmed barge-in, so random VAD noise does not cancel an answer;
- Chinese/English final recognition with noise and language hallucination gates;
- local Qwen3-TTS with a calm Serena voice and cancellable bounded playback;
- spoken-text cleanup for Markdown, emoji, URLs, decorative punctuation, and Chinese numbers;
- `start --observe` for live Muxiva Node latency, Edge rates/queue age, internal buffers, traces, and hotspot verdicts.

Install the alpha:

```bash
dsh plugin --profile web add @muxiva/dsh-voice@alpha
npx @muxiva/dsh-voice@alpha setup
npx @muxiva/dsh-voice@alpha start
```

Then run `dsh --profile web` in another terminal and click the voice orb above the composer.

Compatibility: Muxiva 0.1.1, DSH rc.5/rc.6 (certified on rc.6), macOS Apple Silicon. The setup downloads about 2.5 GB of pinned local models. Models and the isolated Python environment live in the stable OS user-data directory, not the `npx` cache.

The attached M1 Pro certification completed 130/130 turns and 30/30 interruptions with zero failed turns, TTS underruns, or stale post-interruption audio. The report publishes the full p50/p95/p99 distributions and explicitly includes the two-second conversational endpoint and ASR-confirmed interruption delay.

- Repository: https://github.com/PiyotaHu/muxiva-dsh-voice
- Showcase and docs: https://piyotahu.github.io/muxiva-dsh-voice/
- npm: https://www.npmjs.com/package/@muxiva/dsh-voice
- Performance report: https://github.com/PiyotaHu/muxiva-dsh-voice/blob/main/docs/guide/performance.md

I’d especially value feedback on real-room Chinese/English ASR, perceived TTS consistency, and the DSH plugin integration contract.

---

## 中文同步文案

发布一个面向 DSH Web 的本地全双工语音插件：**Muxiva Voice for DeepSeek Harness**。麦克风、VAD、中英文 ASR、文本清洗、Qwen3-TTS 和播放全部留在 Apple Silicon Mac 本机；DSH 继续负责 Session、模型、工具、权限与聊天记录。

底层不是简单的 SDK 回调串联，而是由 Muxiva 提供类型化 Frame、有界队列、背压、取消 Signal、generation fence 和实时 Node/Edge 可观测性。支持大号语音 Orb、不断链静音、ASR 出字后才确认打断、杂音/语言幻觉过滤、本机 Qwen3-TTS，以及 `start --observe` 的完整诊断视图。

一键体验：

```bash
dsh plugin --profile web add @muxiva/dsh-voice@alpha
npx @muxiva/dsh-voice@alpha setup
npx @muxiva/dsh-voice@alpha start
```

兼容 Muxiva 0.1.1 与 DSH rc.5/rc.6，本轮性能认证以 rc.6 为准。
