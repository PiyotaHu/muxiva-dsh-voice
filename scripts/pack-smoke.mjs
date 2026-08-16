import { spawnSync } from 'node:child_process'
import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const cache = mkdtempSync(join(tmpdir(), 'muxiva-dsh-pack-'))
const packed = spawnSync('npm', ['pack', '--dry-run', '--json'], {
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
console.log(`pack smoke passed · ${result.files.length} files · ${result.unpackedSize} bytes unpacked`)
