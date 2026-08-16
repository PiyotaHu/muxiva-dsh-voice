# Alpha.2 launch checklist

## Release evidence

- [ ] Git tag `v0.1.0-alpha.2` exists on the tested commit.
- [ ] GitHub Release contains the npm tarball, M1 Pro report, and release notes.
- [ ] npm `alpha` dist-tag resolves to `0.1.0-alpha.2` and provenance is visible.
- [ ] GitHub recognizes `LICENSE` as Apache-2.0.
- [ ] GitHub Pages displays the public npm commands and measured performance link.

## Promotion order

1. Publish the prepared body in DeepSeek Harness **Show Your Plugins!** using `dsh-show-your-plugins.md`.
2. Add the GitHub Release and Showcase links to the Discussion after previewing the rendered code blocks.
3. Post `discord-launch.md` in the DeepSeek Harness Discord plugin/showcase channel.
4. Pin the Discussion link in this repository and collect reproducible feedback as GitHub Issues.

## Demo capture

Prepare these three assets before posting:

1. `dsh-voice-hero.png`: DSH Web with the large voice orb in its cyan listening state, a short recognized Chinese message, and the latest Agent answer. Use this as the first image.
2. `dsh-voice-observe.png`: the Muxiva Observe view showing the active Graph, Node latency, and Edge queue age. Place this after the pipeline section.
3. `dsh-voice-demo.mp4`: one continuous 45–60 second product recording. Place it directly after the opening two paragraphs.

The recording should show:

1. DSH Web already open, then click the large orb;
2. ask one short Chinese question and show the transcript plus calm TTS response;
3. interrupt the answer with meaningful speech;
4. mute for two seconds, unmute, and ask one short English question;
5. briefly switch to Muxiva Observe to show Node latency and Edge queue age.

Record at 1440p or higher, enlarge the browser to keep the orb and transcript readable, use headphones to avoid acoustic echo, hide private paths/session names, and do not edit out the interaction latency. Add Chinese and English captions, but keep the original local TTS audio. Export H.264 MP4; create a short GIF only if the target surface does not autoplay video.
