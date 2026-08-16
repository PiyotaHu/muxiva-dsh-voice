import test from 'node:test'
import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { mkdtempSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(fileURLToPath(new URL('..', import.meta.url)))
const cli = resolve(root, 'scripts/cli.mjs')

test('CLI exposes explicit headless and observable startup modes', async () => {
  const help = spawnSync(process.execPath, [cli, 'help'], { encoding: 'utf8' })
  assert.equal(help.status, 0, help.stderr)
  assert.match(help.stdout, /start \[--no-observe\]/)
  assert.match(help.stdout, /start --observe/)

  const metadata = JSON.parse(await readFile(resolve(root, 'package.json'), 'utf8'))
  assert.equal(metadata.scripts.start, 'node scripts/cli.mjs start')
  assert.equal(metadata.scripts['start:headless'], 'node scripts/cli.mjs start --no-observe')
  assert.equal(metadata.scripts.observe, 'node scripts/cli.mjs start --observe')
})

test('CLI exposes and honors a stable data-home override', () => {
  const home = mkdtempSync(join(tmpdir(), 'muxiva-dsh-voice-home-'))
  const result = spawnSync(process.execPath, [cli, 'home'], {
    encoding: 'utf8',
    env: { ...process.env, MUXIVA_DSH_VOICE_HOME: home },
  })
  assert.equal(result.status, 0, result.stderr)
  assert.equal(result.stdout.trim(), home)
})

test('CLI rejects ambiguous observability flags before environment checks', () => {
  const result = spawnSync(process.execPath, [cli, 'start', '--observe', '--no-observe'], { encoding: 'utf8' })
  assert.equal(result.status, 1)
  assert.match(result.stderr, /only one of --observe or --no-observe/)
  assert.doesNotMatch(result.stdout, /\[PASS\]|\[FAIL\]/)
})
