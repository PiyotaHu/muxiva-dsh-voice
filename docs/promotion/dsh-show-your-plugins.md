# DeepSeek Harness Discussion launch draft

## Recommended title

**Make DeepSeek Harness hear and speak — dsh-voice, a local full-duplex voice agent plugin**

## Post body

I built **dsh-voice**, an open-source plugin that gives DeepSeek Harness Web a voice: speak naturally to your DSH agent, hear its answer, and interrupt it while it is talking.

The complete speech path runs locally on your Mac. DeepSeek Harness still owns the conversation, Agent, tools, permissions, and model selection.

<!-- Drag the short demo recording here. Recommended: 20–30 seconds, with captions. -->

<!-- Add one screenshot here: the large voice orb in its listening or speaking state. -->

### What it feels like

- Click the large voice orb and start talking—no push-to-talk loop.
- See the recognized text in the normal DSH conversation.
- Hear a local Mandarin or English response.
- Start speaking to interrupt playback; noise alone does not interrupt the Agent.
- Mute and unmute the microphone without unloading the audio pipeline or local models.

### Who can run it

The current alpha targets **macOS on Apple Silicon** and supports **DeepSeek Harness rc.5 and rc.6**; the release is certified on rc.6 and a MacBook Pro M1 Pro with 16 GB RAM. Initial setup downloads about **2.5 GB** of pinned models and creates an isolated local Python environment.

Install it directly from npm:

```bash
dsh plugin --profile web add @muxiva/dsh-voice@alpha
npx @muxiva/dsh-voice@alpha setup
npx @muxiva/dsh-voice@alpha start
```

Then start `dsh --profile web` in another terminal and click the voice orb above the composer.

### The local voice pipeline

```text
Browser microphone
  → Silero VAD
  → Zipformer streaming ASR preview
  → SenseVoice Chinese/English ASR final
  → DeepSeek Harness Agent and tools
  → spoken-text normalization
  → Qwen3-TTS 0.6B CustomVoice 8-bit on MLX (Serena)
  → browser speaker
```

The pipeline is orchestrated by **Muxiva**, an open-source real-time multimodal runtime. Muxiva provides typed audio/text Frames, bounded queues, backpressure, cancellation, generation fences, and Node/Edge observability. That is what lets the plugin keep microphone capture, ASR, Agent streaming, interruption, TTS generation, and browser playback synchronized without patching DeepSeek Harness.

For live diagnostics, start it with:

```bash
npx @muxiva/dsh-voice@alpha start --observe
```

### Measured on an M1 Pro

The alpha.2 certification completed **130/130 turns** and **30/30 mid-answer interruptions**, plus five minutes of idle listening and a 30-minute soak. It recorded zero failed turns, zero TTS underruns, and zero stale audio after interruption. The public report includes p50/p95/p99 latency, Mandarin CER, English WER, CPU, memory, model storage, methodology, and the machine-readable result.

### Links

- **Code:** https://github.com/PiyotaHu/muxiva-dsh-voice
- **Showcase and documentation:** https://piyotahu.github.io/muxiva-dsh-voice/
- **Getting started:** https://piyotahu.github.io/muxiva-dsh-voice/docs.html#install
- **Performance report:** https://piyotahu.github.io/muxiva-dsh-voice/docs.html#performance
- **npm:** https://www.npmjs.com/package/@muxiva/dsh-voice
- **alpha.2 release:** https://github.com/PiyotaHu/muxiva-dsh-voice/releases/tag/v0.1.0-alpha.2

This is an alpha, and real-room feedback matters most now. I would especially value reports about Chinese/English recognition, TTS consistency, interruption behavior, and different Apple Silicon machines.

---

## 中文版（可用于国内社区同步）

### 推荐标题

**让你的 DeepSeek Harness 能听会说：dsh-voice 本地全双工语音 Agent 插件**

我做了一个开源的 **dsh-voice** 插件，让 DeepSeek Harness Web 可以直接听你说话、显示识别结果、用语音回答，并且支持在回答途中自然打断。

整条语音链路都在 Mac 本机运行；DeepSeek Harness 继续负责会话、Agent、工具、权限和模型选择。

目前适用于 **Apple Silicon Mac**，兼容 **DSH rc.5 / rc.6**，并已在 16 GB 的 MacBook Pro M1 Pro 和 DSH rc.6 上完成认证。首次安装会下载约 2.5 GB 的固定版本模型。

```bash
dsh plugin --profile web add @muxiva/dsh-voice@alpha
npx @muxiva/dsh-voice@alpha setup
npx @muxiva/dsh-voice@alpha start
```

本地管线为：

```text
浏览器麦克风
  → Silero VAD
  → Zipformer 流式识别预览
  → SenseVoice 中英文最终识别
  → DeepSeek Harness Agent / Tools
  → 口语文本清洗
  → Qwen3-TTS 0.6B 8-bit + MLX（Serena）
  → 浏览器播放
```

底层由实时多模态运行时 **Muxiva** 编排，负责类型化 Frame、有界队列、背压、取消、generation fence，以及 Node/Edge 可观测性。它让麦克风、ASR、Agent 流式输出、语音打断、TTS 和播放保持同步，无需修改 DeepSeek Harness 源码。

alpha.2 在 M1 Pro 上完成了 **130/130 轮对话**、**30/30 次回答中打断**和 30 分钟持续运行，失败轮次、TTS 断流和打断后的残留音频均为 0。完整延迟分布、中英文准确率、CPU、内存、模型空间和复现方法均已公开在性能报告中。

- 代码：https://github.com/PiyotaHu/muxiva-dsh-voice
- Showcase 与文档：https://piyotahu.github.io/muxiva-dsh-voice/
- 性能报告：https://piyotahu.github.io/muxiva-dsh-voice/docs.html#performance
- npm：https://www.npmjs.com/package/@muxiva/dsh-voice
