#!/usr/bin/env node
import { createHash, randomBytes } from 'node:crypto'
import { createReadStream, createWriteStream, existsSync } from 'node:fs'
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

async function ensureExtracted(model, target) {
  if (!model.extract) return
  const ready = (model.files ?? []).every(path => existsSync(resolve(root, path)))
  if (ready) return
  console.log(`[voice] extract ${model.id}`)
  await run('tar', ['-xjf', target, '-C', resolve(root, model.extract)])
}

async function verifyModel(model) {
  if (model.source === 'huggingface') {
    const modelRoot = resolve(root, model.target)
    if (!(model.files ?? []).every(path => existsSync(resolve(root, path)))) return false
    for (const [relative, expected] of Object.entries(model.sha256 ?? {})) {
      const path = resolve(modelRoot, relative)
      if (!existsSync(path) || await sha256(path) !== expected) return false
    }
    return true
  }
  const target = resolve(root, model.target)
  if (!existsSync(target) || await sha256(target) !== model.sha256) return false
  return (model.files ?? []).every(path => existsSync(resolve(root, path)))
}

async function downloadHuggingFace(model) {
  if (await verifyModel(model)) {
    console.log(`[voice] reuse ${model.id}`)
    return
  }
  const target = resolve(root, model.target)
  await mkdir(target, { recursive: true })
  console.log(`[voice] download ${model.id} from pinned Hugging Face revision`)
  const script = [
    'import os',
    'from huggingface_hub import snapshot_download',
    'snapshot_download(repo_id=os.environ["MUXIVA_HF_REPO"], revision=os.environ["MUXIVA_HF_REVISION"], local_dir=os.environ["MUXIVA_HF_TARGET"])',
  ].join(';')
  await run(pythonPath(), ['-c', script], {
    env: {
      ...process.env,
      MUXIVA_HF_REPO: model.repo_id,
      MUXIVA_HF_REVISION: model.revision,
      MUXIVA_HF_TARGET: target,
    },
  })
  if (!await verifyModel(model)) throw new Error(`${model.id} checksum mismatch after download`)
}

async function download(model) {
  if (model.source === 'huggingface') return downloadHuggingFace(model)
  const target = resolve(root, model.target)
  if (existsSync(target) && await sha256(target) === model.sha256) {
    console.log(`[voice] reuse ${model.id}`)
    await ensureExtracted(model, target)
    return
  }
  await mkdir(dirname(target), { recursive: true })
  const partial = `${target}.partial`
  console.log(`[voice] download ${model.id}`)
  await run('curl', ['--fail', '--location', '--retry', '4', '--continue-at', '-', '--output', partial, model.url])
  const actual = await sha256(partial)
  if (actual !== model.sha256) throw new Error(`${model.id} checksum mismatch: ${actual}`)
  await rename(partial, target)
  await ensureExtracted(model, target)
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
  const imports = python && spawnSync(pythonPath(), ['-c', `import importlib.metadata; import muxiva,numpy,sherpa_onnx,websockets,mlx_audio,muxiva_voice_transport; assert importlib.metadata.version("muxiva") == "${muxivaVersion}"; assert importlib.metadata.version("mlx-audio") == "0.4.8"; assert importlib.metadata.version("mlx") == "0.31.2"; assert importlib.metadata.version("transformers") == "5.14.0"`], {
    cwd: root,
    env: { ...process.env, PYTHONPATH: resolve(root, 'python') },
    stdio: 'ignore',
  }).status === 0
  const lock = JSON.parse(await readFile(resolve(root, 'models.lock.json'), 'utf8'))
  let readyModels = true
  for (const model of lock.models) {
    if (!await verifyModel(model)) readyModels = false
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

function observeMode(argv) {
  const flags = argv.slice(1)
  const unknown = flags.filter(flag => flag !== '--observe' && flag !== '--no-observe')
  if (unknown.length) throw new Error(`unknown start option: ${unknown[0]}`)
  if (flags.includes('--observe') && flags.includes('--no-observe')) {
    throw new Error('start accepts only one of --observe or --no-observe')
  }
  return flags.includes('--observe')
}

function portFromEnvironment(name, fallback) {
  const raw = process.env[name]
  if (raw === undefined) return fallback
  const port = Number(raw)
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error(`${name} must be an integer between 1 and 65535`)
  }
  return port
}

function childExit(child, label) {
  return new Promise((resolveExit, reject) => {
    child.once('error', reject)
    child.once('exit', code => resolveExit({ label, code }))
  })
}

function teeChild(child, label, log) {
  child.stdout.on('data', chunk => {
    process.stdout.write(chunk)
    log.write(`[${label}:stdout] ${chunk}`)
  })
  child.stderr.on('data', chunk => {
    process.stderr.write(chunk)
    log.write(`[${label}:stderr] ${chunk}`)
  })
}

async function start(observe = false) {
  await doctor(false)
  if (process.exitCode) throw new Error('doctor failed; resolve the checks above before start')
  const token = randomBytes(32).toString('hex')
  const env = {
    ...process.env,
    MUXIVA_PYTHON: pythonPath(),
    MUXIVA_DSH_BRIDGE_TOKEN: token,
    PYTHONPATH: [resolve(root, 'python'), process.env.PYTHONPATH].filter(Boolean).join(':'),
  }
  const runtimePort = portFromEnvironment('MUXIVA_DSH_RUNTIME_PORT', 8080)
  const logPath = resolve(root, '.muxiva/runtime.log')
  await mkdir(dirname(logPath), { recursive: true })
  const log = createWriteStream(logPath, { flags: 'a' })
  log.write(`\n[supervisor] ${new Date().toISOString()} start mode=${observe ? 'observe' : 'headless'} runtime_port=${runtimePort}\n`)
  console.log(`[voice] starting supervised loopback bridge and Muxiva ${observe ? 'Studio' : 'headless Runtime'}`)
  console.log(`[voice] persistent runtime log: ${logPath}`)
  if (observe) console.log('[voice] in Studio, select Run and then open ◎ Observe for live Node and Edge telemetry')
  const detached = process.platform !== 'win32'
  const bridge = spawn(pythonPath(), ['-m', 'muxiva_voice_transport.server'], {
    cwd: root, env, stdio: ['inherit', 'pipe', 'pipe'], detached,
  })
  teeChild(bridge, 'bridge', log)
  await new Promise((resolveWait, reject) => {
    const timer = setTimeout(resolveWait, 400)
    bridge.once('error', (error) => { clearTimeout(timer); reject(error) })
    bridge.once('exit', (code) => { clearTimeout(timer); reject(new Error(`voice bridge exited during startup with ${code}`)) })
  })
  const muxivaArgs = observe
    ? ['studio', resolve(root, 'graph.json'), '--host', '127.0.0.1', ...(process.env.MUXIVA_DSH_STUDIO_NO_OPEN === '1' ? ['--no-open'] : [])]
    : ['serve', resolve(root, 'graph.json'), '--host', '127.0.0.1', '--port', String(runtimePort)]
  let runtime = null
  let stopping = false
  const stopChildren = () => {
    if (stopping) return
    stopping = true
    if (runtime?.exitCode === null) runtime.kill('SIGINT')
  }
  process.once('SIGINT', stopChildren)
  process.once('SIGTERM', stopChildren)
  try {
    runtime = spawn('muxiva', muxivaArgs, {
      cwd: root, env, stdio: ['inherit', 'pipe', 'pipe'], detached,
    })
    teeChild(runtime, 'muxiva', log)
    const firstExit = await Promise.race([
      childExit(runtime, 'muxiva'),
      childExit(bridge, 'voice bridge'),
    ])
    if (firstExit.label === 'voice bridge' && !stopping) {
      throw new Error(`voice bridge exited unexpectedly with ${firstExit.code}`)
    }
    if (firstExit.label === 'muxiva' && !stopping && firstExit.code !== 0 && firstExit.code !== null) {
      throw new Error(`muxiva exited with ${firstExit.code}`)
    }
  } finally {
    process.removeListener('SIGINT', stopChildren)
    process.removeListener('SIGTERM', stopChildren)
    if (runtime?.exitCode === null) runtime.kill('SIGINT')
    if (bridge.exitCode === null) bridge.kill('SIGTERM')
    log.write(`[supervisor] ${new Date().toISOString()} stopped\n`)
    log.end()
  }
}

function help() {
  console.log(`muxiva-dsh-voice

  doctor [--fix]  verify Apple Silicon, Muxiva, Python and models
  models          download and SHA-256 verify the pinned local models
  setup           install Python dependencies, build the Muxiva Python binding, and download models
  start [--no-observe]
                  run the local voice Graph headlessly (default)
  start --observe open Muxiva Studio for Run/Stop, live Nodes, Edges and traces

Runtime output is persisted to .muxiva/runtime.log in both modes.

Install the DSH surface separately:
  dsh plugin --profile web add @muxiva/dsh-voice`)
}

try {
  if (command === 'models') await models()
  else if (command === 'doctor') await doctor(args.includes('--fix'))
  else if (command === 'setup') { await doctor(true); await models(); await doctor(false) }
  else if (command === 'start') await start(observeMode(args))
  else if (command === 'help' || command === '--help' || command === '-h') help()
  else throw new Error(`unknown command: ${command}`)
} catch (error) {
  console.error(`[voice] ${error instanceof Error ? error.message : String(error)}`)
  process.exitCode = 1
}
