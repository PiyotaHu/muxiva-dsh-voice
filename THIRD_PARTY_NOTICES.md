# Third-party models and runtimes

Models are downloaded on demand and are not redistributed in the npm tarball.

| Component | Pinned artifact | License | Purpose |
| --- | --- | --- | --- |
| Silero VAD | sherpa-onnx `silero_vad.onnx` | MIT | Speech onset/end and barge-in |
| Zipformer2 CTC zh | `ba19bb0…`, small streaming model | Apache-2.0 | Default Mandarin streaming ASR |
| SenseVoiceSmall int8 | `2024-07-17`, zh/en/ja/ko/yue | FunASR model license | Accurate multilingual ASR final with automatic language detection and ITN |
| Qwen3-TTS 0.6B CustomVoice 8-bit | `mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit@049ef77…` | Apache-2.0 | Local multilingual, cancellable streaming 24 kHz TTS |
| MLX-Audio | `0.4.8` | MIT | Qwen3-TTS inference optimized for Apple Silicon |
| Apple MLX / MLX-LM | `0.31.2` / `0.31.3` | MIT | Metal inference runtime and model utilities |
| sherpa-onnx | `1.13.5` | Apache-2.0 | ONNX speech runtime |
| websockets | `15.0.1` | BSD-3-Clause | Loopback browser transport |
| NumPy | `2.2.6` | BSD-3-Clause | PCM conversion |

The authoritative artifact URLs and SHA-256 values are in `models.lock.json`. Each downloaded archive includes its upstream license where provided. Keep those files when copying models to another machine.

Moonshine, whisper.cpp and FluidAudio are evaluated alternatives, not default dependencies and not downloaded by this release. Piper is deliberately excluded from the default distribution because the current upstream repository is GPL-3.0.
