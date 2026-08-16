# Discord launch copy

🎙️ **Muxiva Voice for DeepSeek Harness — local full-duplex voice on Apple Silicon**

I’ve released an open-source DSH Web voice plugin powered by Muxiva. Mic → VAD → Chinese/English ASR → DSH Agent/Tools → Qwen3-TTS → playback stays local on the Mac, with ASR-confirmed barge-in, persistent mute, bounded queues, cancellation, and live Node/Edge observability.

```bash
dsh plugin --profile web add @muxiva/dsh-voice@alpha
npx @muxiva/dsh-voice@alpha setup
npx @muxiva/dsh-voice@alpha start
```

Compatible with DSH rc.5/rc.6 and certified on rc.6 + Muxiva 0.1.1. The M1 Pro release report includes 100+ turns, 30 interruptions, five idle minutes, and a 30-minute soak.

Showcase: https://piyotahu.github.io/muxiva-dsh-voice/
GitHub: https://github.com/PiyotaHu/muxiva-dsh-voice

Feedback on real-room ASR and TTS consistency is very welcome.
