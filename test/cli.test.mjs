import test from 'node:test'
import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
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

test('CLI rejects ambiguous observability flags before environment checks', () => {
  const result = spawnSync(process.execPath, [cli, 'start', '--observe', '--no-observe'], { encoding: 'utf8' })
  assert.equal(result.status, 1)
  assert.match(result.stderr, /only one of --observe or --no-observe/)
  assert.doesNotMatch(result.stdout, /\[PASS\]|\[FAIL\]/)
})
