import { spawnSync } from 'node:child_process'
import { existsSync, mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const cache = mkdtempSync(join(tmpdir(), 'muxiva-dsh-pack-'))
const packed = spawnSync('npm', ['pack', '--json', '--pack-destination', cache], {
  encoding: 'utf8',
  env: { ...process.env, npm_config_cache: cache },
})
if (packed.status !== 0) throw new Error(packed.stderr)
const result = JSON.parse(packed.stdout)[0]
for (const required of ['lib/client.js', 'cordis.patch.yml', 'graph.json', 'models.lock.json']) {
  if (!result.files.some(file => file.path === required)) throw new Error(`tarball missing ${required}`)
}
for (const file of result.files) {
  if (file.path.includes('__pycache__') || /\.py[co]$/.test(file.path) || file.path.includes('/venv') || file.path.startsWith('benchmarks/traces/')) {
    throw new Error(`tarball contains a generated environment artifact: ${file.path}`)
  }
}

const installRoot = mkdtempSync(join(tmpdir(), 'muxiva-dsh-install-'))
const installed = spawnSync('npm', [
  'install', join(cache, result.filename), '--ignore-scripts', '--no-audit', '--no-fund',
], {
  cwd: installRoot,
  encoding: 'utf8',
  env: { ...process.env, npm_config_cache: cache },
})
if (installed.status !== 0) throw new Error(installed.stderr || installed.stdout)
const executable = join(installRoot, 'node_modules/.bin/muxiva-dsh-voice')
if (!existsSync(executable)) throw new Error('installed tarball is missing the muxiva-dsh-voice executable')
const help = spawnSync(executable, ['--help'], { cwd: installRoot, encoding: 'utf8' })
if (help.status !== 0 || !help.stdout.includes('muxiva-dsh-voice')) {
  throw new Error(`installed CLI smoke failed: ${help.stderr || help.stdout}`)
}
const stableHome = mkdtempSync(join(tmpdir(), 'muxiva-dsh-data-'))
const home = spawnSync(executable, ['home'], {
  cwd: installRoot,
  encoding: 'utf8',
  env: { ...process.env, MUXIVA_DSH_VOICE_HOME: stableHome },
})
if (home.status !== 0 || home.stdout.trim() !== stableHome) {
  throw new Error(`installed CLI data-home smoke failed: ${home.stderr || home.stdout}`)
}

console.log(`pack/install smoke passed · ${result.files.length} files · ${result.unpackedSize} bytes unpacked · CLI linked`)
