# Muxiva Voice for DeepSeek Harness

这是一个面向官方 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 的本地优先、可打断、全双工语音插件，底层实时 Pipeline 由 [Muxiva](https://github.com/PiyotaHu/muxiva) 编排。

麦克风、VAD、ASR、分句、TTS、播放和打断链路都留在 Mac 本机；DSH 继续负责有状态 Agent、工具、权限、会话和 Web 聊天记录。

> 当前是 Alpha：公开 npm 安装、源码联调路径与 M1 Pro 无人值守认证已经完成。兼容 DSH rc.5 / rc.6，本轮 alpha.2 以 rc.6 认证；Muxiva 0.1.1 已发布 CPython 3.8–3.14 Wheel（包括 macOS universal2）。

## 一键安装（Apple Silicon）

前置要求：Node.js 22.19+、Python 3.11–3.13、Muxiva 0.1.1 CLI 与官方 DSH CLI。

```bash
dsh plugin --profile web add @muxiva/dsh-voice@alpha
npx @muxiva/dsh-voice@alpha setup
npx @muxiva/dsh-voice@alpha start
```

另开一个终端运行 `dsh --profile web`。公开 npm/npx 安装会把约 2.5 GB 模型、隔离 Python 环境和日志保存在稳定的系统用户数据目录，不会随着 npm 缓存清理而丢失。运行 `npx @muxiva/dsh-voice@alpha home` 可查看目录，也可用 `MUXIVA_DSH_VOICE_HOME` 覆盖。

## 源码开发

前置要求：Apple Silicon Mac、Node.js 22.19+、Python 3.11–3.13、Rust、相邻目录 `../muxiva` 中的 Muxiva 源码、已安装的 `muxiva` CLI 和官方 DSH CLI。

```bash
cd muxiva-dsh-voice
npm run doctor -- --fix
npm run models
dsh plugin --profile web add .
```

然后分别启动：

```bash
# 终端 A：Muxiva 本地语音 Graph
npm start

# 终端 B：DSH Web
dsh --profile web
```

`npm start` 默认是低开销的无界面产品模式，也可以显式运行 `npm run start:headless`。
排障或调优时，把终端 A 换成 `npm run observe`：它会在继续托管认证语音桥的同时打开
同一个 `graph.json` 的 Muxiva Studio。点击 **Run**，再打开 **◎ Observe**，即可查看各
Node 的延迟/吞吐、各 Edge 的速率/队列年龄、Node 内部缓冲、Trace 和热点判断。
两种模式都会把桥与 Runtime 输出追加到 `.muxiva/runtime.log`，无界面运行时可直接
`tail -f .muxiva/runtime.log` 追踪启动失败、ASR/TTS 事件和 Node Host 错误。

进入 DSH 会话后点击输入框上方的大型语音 Orb。光环会跟随输入能量，状态会依次显示“聆听 / 识别 / 思考 / 回答”。再次点击大按钮只会静音/恢复麦克风，WebSocket、AudioWorklet 和 Graph 保持常驻；浏览器不再注入 PCM，Muxiva Audio Source 进入 paused，并在恢复前重置 VAD/ASR 流。右侧小“结束”按钮才会关闭链路。VAD 起点只用于提示；只有非空 ASR Partial 或通过质量门禁的多语 Final 才确认打断、清掉旧播放/TTS 并取消旧 DSH Turn。被拒绝的杂音会回到聆听，不会提示 DSH。

可靠性优先的默认端点等待 2 秒连续静音后产生 ASR Final，使用 `0.75` VAD 阈值与 350 ms 最短语音门控，并在 Silero 切段起点前补回 500 ms 音频，避免 SenseVoice 丢失较轻的开头音节。SenseVoice Final 只允许有有效文字的中英文语音进入 DSH，非语音事件以及杂音产生的日文、韩文和单字符幻觉会被拒绝。展示用 emoji、括号等字符会变成韵律停顿，而不是在删除后把前后文字粘连。TTS 默认使用 Qwen3-TTS 的 `Serena`，固定平静温柔的语速、音区和情绪采样参数。两阶段上下文策略先用一个 48–96 字的自然语义段尽早开口，再把 Agent Final 的全部剩余内容作为一个上下文生成；短回答调用一次，长回答最多两次，同时避免等待完整长回答和逐句反复起调。有界实时 PCM 调度仍会限制浏览器播放队列的提前量。

## 边界

- Muxiva 管实时系统：Frame、Graph、有界队列、背压、Signal、取消和可观测性。
- DSH 管 Agent：模型、Session、Tools、Permissions 和 Web UI。
- 本仓库只管桥：DSH Bundle、Web 控件、版本化本地协议和项目 Node Pack。
- 当前没有修改 Muxiva 或 DSH 上游仓库。

模型下载采用固定 revision，并对 Qwen3-TTS 主权重和语音 tokenizer 执行 SHA-256 校验；npm 包本身不重新分发模型。完整说明见 [DSH 兼容矩阵](docs/guide/compatibility.md)、[模型和许可证](THIRD_PARTY_NOTICES.md)、[协议](docs/reference/protocol.md)和[安全模型](docs/reference/security.md)。

模型安装完成后，可以运行 `npm run test:e2e`。它会启动真实的 8-Node Muxiva Graph，认证“中文文本 → normalizer → Qwen3-TTS 24 kHz PCM → 模拟麦克风 → Silero VAD → SenseVoice Final”的闭环，并另外验证英文识别。默认 TTS 是在 Apple Silicon 上通过 MLX 运行的 Qwen3-TTS 0.6B CustomVoice 8-bit，不包含云端 fallback。

第一台性能认证机器是 16 GB MacBook Pro M1 Pro：130/130 回合、30/30 次打断全部完成，
TTS underrun 为零。完整延迟分布、资源用量、CER/WER 适用范围、复现命令和每个 Release
必须提交的版本化实测报告见[性能与验收](docs/guide/performance.md)。缺少对应性能报告及
文档链接时，npm Release Workflow 会直接失败。
