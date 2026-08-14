#!/usr/bin/env node
import { createHash, randomBytes } from 'node:crypto'
import { createReadStream, existsSync } from 'node:fs'
import { mkdir, readFile, rename, stat } from 'node:fs/promises'
import { spawn, spawnSync } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const args = process.argv.slice(2)
const command = args[0] ?? 'help'
const packageMetadata = JSON.parse(await readFile(resolve(root, 'package.json'), 'utf8'))
const muxivaVersion = packageMetadata.muxivaVoice.muxivaVersion

function run(program, argv, options = {}) {
  return new Promise((resolveRun, reject) => {
    const child = spawn(program, argv, { cwd: root, stdio: 'inherit', ...options })
    child.on('error', reject)
    child.on('exit', code => code === 0 ? resolveRun() : reject(new Error(`${program} exited with ${code}`)))
  })
}

function available(program, argv = ['--version']) {
  return spawnSync(program, argv, { stdio: 'ignore' }).status === 0
}

async function sha256(path) {
  const hash = createHash('sha256')
  for await (const chunk of createReadStream(path)) hash.update(chunk)
  return hash.digest('hex')
}

async function download(model) {
  const target = resolve(root, model.target)
  if (existsSync(target) && await sha256(target) === model.sha256) {
    console.log(`[voice] reuse ${model.id}`)
    return
  }
  await mkdir(dirname(target), { recursive: true })
  const partial = `${target}.partial`
  console.log(`[voice] download ${model.id}`)
  await run('curl', ['--fail', '--location', '--retry', '4', '--continue-at', '-', '--output', partial, model.url])
  const actual = await sha256(partial)
  if (actual !== model.sha256) throw new Error(`${model.id} checksum mismatch: ${actual}`)
  await rename(partial, target)
  if (model.extract) {
    await run('tar', ['-xjf', target, '-C', resolve(root, model.extract)])
  }
}

async function models() {
  const lock = JSON.parse(await readFile(resolve(root, 'models.lock.json'), 'utf8'))
  for (const model of lock.models) await download(model)
  console.log('[voice] models ready')
}

function pythonPath() {
  return resolve(root, '.muxiva/venv/bin/python')
}

function pythonVersion(program) {
  const result = spawnSync(program, ['-c', 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'], { encoding: 'utf8' })
  return result.status === 0 ? result.stdout.trim() : ''
}

function supportedPython(program) {
  return ['3.11', '3.12', '3.13'].includes(pythonVersion(program))
}

function basePython() {
  for (const program of ['python3.13', 'python3.12', 'python3.11', 'python3']) {
    if (supportedPython(program)) return program
  }
  throw new Error('Python 3.11, 3.12 or 3.13 is required; no supported interpreter was found')
}

function sourceRoot() {
  const candidate = process.env.MUXIVA_SOURCE_ROOT || resolve(root, '../muxiva')
  return existsSync(resolve(candidate, 'crates/muxiva-python/Cargo.toml')) ? candidate : null
}

function report(label, ok, detail) {
  console.log(`[${ok ? 'PASS' : 'FAIL'}] ${label}${detail ? ` · ${detail}` : ''}`)
  return ok
}

async function doctor(fix = false) {
  process.exitCode = 0
  if (fix) {
    if (existsSync(pythonPath()) && !supportedPython(pythonPath())) {
      const backup = resolve(root, `.muxiva/venv-unsupported-${pythonVersion(pythonPath()).replace('.', '-')}-${Date.now()}`)
      await rename(resolve(root, '.muxiva/venv'), backup)
      console.log(`[voice] preserved unsupported venv at ${backup}`)
    }
    if (!existsSync(pythonPath())) await run(basePython(), ['-m', 'venv', resolve(root, '.muxiva/venv')])
    await run(pythonPath(), ['-m', 'pip', 'install', '--disable-pip-version-check', '-r', resolve(root, 'requirements-macos.txt')])
    const source = sourceRoot()
    if (source) {
      await run(pythonPath(), ['-m', 'pip', 'install', '--disable-pip-version-check', 'maturin==1.9.4'])
      await run(pythonPath(), ['-m', 'maturin', 'develop', '--release', '--manifest-path', resolve(source, 'crates/muxiva-python/Cargo.toml')], {
        env: { ...process.env, VIRTUAL_ENV: resolve(root, '.muxiva/venv') },
      })
    } else {
      await run(pythonPath(), ['-m', 'pip', 'install', '--disable-pip-version-check', `muxiva==${muxivaVersion}`])
    }
  }
  const macArm = process.platform === 'darwin' && process.arch === 'arm64'
  const muxivaResult = spawnSync('muxiva', ['--version'], { encoding: 'utf8' })
  const muxiva = muxivaResult.status === 0 && muxivaResult.stdout.trim() === `muxiva ${muxivaVersion}`
  const python = existsSync(pythonPath()) && supportedPython(pythonPath())
  const imports = python && spawnSync(pythonPath(), ['-c', `import importlib.metadata; import muxiva,numpy,sherpa_onnx,websockets,muxiva_voice_transport; assert importlib.metadata.version("muxiva") == "${muxivaVersion}"`], {
    cwd: root,
    env: { ...process.env, PYTHONPATH: resolve(root, 'python') },
    stdio: 'ignore',
  }).status === 0
  const lock = JSON.parse(await readFile(resolve(root, 'models.lock.json'), 'utf8'))
  let readyModels = true
  for (const model of lock.models) {
    const target = resolve(root, model.target)
    if (!existsSync(target) || await sha256(target) !== model.sha256) readyModels = false
  }
  const results = [
    report('macOS Apple Silicon', macArm, `${process.platform}/${process.arch}`),
    report('Node.js >= 22.19', Number(process.versions.node.split('.')[0]) >= 22, process.version),
    report(`Muxiva CLI ${muxivaVersion}`, muxiva, muxiva ? 'exact version available' : `install Muxiva ${muxivaVersion}`),
    report('project Python 3.11–3.13 environment', imports, imports ? 'dependencies ready' : (python ? 'dependency import failed' : 'run doctor --fix')),
    report('pinned local models', readyModels, readyModels ? 'checksums verified' : 'run models'),
  ]
  process.exitCode = results.every(Boolean) ? 0 : 1
}

async function start() {
  await doctor(false)
  if (process.exitCode) throw new Error('doctor failed; resolve the checks above before start')
  const token = randomBytes(32).toString('hex')
  const env = {
    ...process.env,
    MUXIVA_PYTHON: pythonPath(),
    MUXIVA_DSH_BRIDGE_TOKEN: token,
    PYTHONPATH: [resolve(root, 'python'), process.env.PYTHONPATH].filter(Boolean).join(':'),
  }
  console.log('[voice] starting supervised loopback bridge and Muxiva graph')
  const detached = process.platform !== 'win32'
  const bridge = spawn(pythonPath(), ['-m', 'muxiva_voice_transport.server'], {
    cwd: root, env, stdio: 'inherit', detached,
  })
  await new Promise((resolveWait, reject) => {
    const timer = setTimeout(resolveWait, 400)
    bridge.once('error', (error) => { clearTimeout(timer); reject(error) })
    bridge.once('exit', (code) => { clearTimeout(timer); reject(new Error(`voice bridge exited during startup with ${code}`)) })
  })
  const runtime = spawn('muxiva', ['serve', resolve(root, 'graph.json'), '--host', '127.0.0.1', '--port', '8080'], {
    cwd: root, env, stdio: 'inherit', detached,
  })
  let stopping = false
  const stopChildren = () => {
    if (stopping) return
    stopping = true
    runtime.kill('SIGINT')
  }
  process.once('SIGINT', stopChildren)
  process.once('SIGTERM', stopChildren)
  const code = await new Promise((resolveExit, reject) => {
    runtime.once('error', reject)
    runtime.once('exit', resolveExit)
  })
  bridge.kill('SIGTERM')
  if (!stopping && code !== 0 && code !== null) throw new Error(`muxiva exited with ${code}`)
}

function help() {
  console.log(`muxiva-dsh-voice

  doctor [--fix]  verify Apple Silicon, Muxiva, Python and models
  models          download and SHA-256 verify the pinned local models
  setup           install Python dependencies, build the Muxiva Python binding, and download models
  start           run the local Muxiva voice Graph

Install the DSH surface separately:
  dsh plugin --profile web add @muxiva/dsh-voice`)
}

try {
  if (command === 'models') await models()
  else if (command === 'doctor') await doctor(args.includes('--fix'))
  else if (command === 'setup') { await doctor(true); await models(); await doctor(false) }
  else if (command === 'start') await start()
  else if (command === 'help' || command === '--help' || command === '-h') help()
  else throw new Error(`unknown command: ${command}`)
} catch (error) {
  console.error(`[voice] ${error instanceof Error ? error.message : String(error)}`)
  process.exitCode = 1
}
