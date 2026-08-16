# DeepSeek Harness compatibility

Muxiva Voice `0.1.0-alpha.2` uses only the DSH Bundle patch contract, the browser module-loader contract, the conversation slot, and the public Session prompt/cancel face.

| DSH line | Distribution tested | Result |
| --- | --- | --- |
| `0.1.0-rc.6` | public `@deepseek-ai/dsh@0.1.0-rc.6` | clean profile install, composed config, Web boot manifest, and plugin browser artifact passed |
| `0.1.0-rc.5` | official source snapshot whose CLI/client packages declare `0.1.0-rc.5` | clean profile install, composed config, Web boot manifest, and plugin browser artifact passed |

The exact `0.1.0-rc.5` CLI/client packages are not currently present in the public npm version list; the rc.5 compatibility result therefore describes the official source distribution, not the older public `0.0.1-rc.5` line. The release-grade performance report targets the current public rc.6 line.

Peer metadata intentionally declares:

- `@deepseek-ai/cordis`: `^4.0.1`, matching the official DSH package;
- DSH client runtime/conversation: `0.1.0-rc.5 || 0.1.0-rc.6`;
- React: `^18.2.0`.

The DSH peers are optional because the host profile supplies them. This prevents a standalone `npx @muxiva/dsh-voice@alpha ...` command from installing a second copy of the DSH browser runtime.

Compatibility beyond rc.6 is not implied. Every newly supported DSH RC must repeat the clean-profile Web smoke and update this matrix before release.
