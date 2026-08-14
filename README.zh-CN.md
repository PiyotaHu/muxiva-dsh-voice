# Muxiva Voice for DeepSeek Harness

这是一个面向官方 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 的本地优先、可打断、全双工语音插件，底层实时 Pipeline 由 [Muxiva](https://github.com/PiyotaHu/muxiva) 编排。

麦克风、VAD、ASR、分句、TTS、播放和打断链路都留在 Mac 本机；DSH 继续负责有状态 Agent、工具、权限、会话和 Web 聊天记录。

> 当前是 Alpha：源码联调路径已经建立。面向陌生用户的真正一条命令安装，还需要 Muxiva Release 提供 macOS arm64 Python wheel，详见 [RFC-0001](docs/reference/rfc-0001-python-wheel.md)。

## 源码快速开始

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

进入 DSH 会话后点击输入框左侧麦克风。紫色光环显示输入能量，状态会依次显示“聆听 / 识别 / 思考 / 播放”；说话打断时，Muxiva Signal 会立即清掉旧播放和 TTS，浏览器同时取消旧 DSH Turn。

## 边界

- Muxiva 管实时系统：Frame、Graph、有界队列、背压、Signal、取消和可观测性。
- DSH 管 Agent：模型、Session、Tools、Permissions 和 Web UI。
- 本仓库只管桥：DSH Bundle、Web 控件、版本化本地协议和项目 Node Pack。
- 当前没有修改 Muxiva 或 DSH 上游仓库。

模型下载采用固定版本和 SHA-256 校验；npm 包本身不重新分发模型。完整说明见 [模型和许可证](THIRD_PARTY_NOTICES.md)、[协议](docs/reference/protocol.md)和[安全模型](docs/reference/security.md)。

模型安装完成后，可以运行 `npm run test:e2e`。它会启动真实 Muxiva Graph，执行“中文文本 → Kokoro PCM → 模拟麦克风 → Silero VAD → Zipformer ASR”的本地闭环认证。
