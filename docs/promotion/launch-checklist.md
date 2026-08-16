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

Record one continuous 45–60 second screen capture:

1. clean `dsh plugin add` and `npx ... start` command already completed;
2. open DSH Web and click the large orb;
3. ask one Chinese question and show the transcript plus calm TTS response;
4. interrupt the answer with meaningful speech;
5. mute, wait, unmute, and ask one English question;
6. briefly switch to Muxiva Studio Observe to show Node latency and Edge queue age.

Use headphones, hide private paths/session names, and do not edit out the interaction latency.
