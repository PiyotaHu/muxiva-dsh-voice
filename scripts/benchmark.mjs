#!/usr/bin/env node
import { spawn } from 'node:child_process'
import { createServer } from 'node:net'
import { mkdir, readFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const mode = process.argv[2]
if (!['quick', 'certify'].includes(mode)) throw new Error('usage: benchmark.mjs <quick|certify> [runner options]')
const extra = process.argv.slice(3)
const metadata = JSON.parse(await readFile(resolve(root, 'package.json'), 'utf8'))

const freePort = () => new Promise((resolvePort, reject) => {
  const server = createServer()
  server.once('error', reject)
  server.listen(0, '127.0.0.1', () => {
    const address = server.address()
    const port = typeof address === 'object' && address ? address.port : null
    server.close(error => error ? reject(error) : resolvePort(port))
  })
})

async function startService(label) {
  const [publicPort, internalPort, runtimePort] = await Promise.all([freePort(), freePort(), freePort()])
  const env = {
    ...process.env,
    MUXIVA_DSH_BRIDGE_PUBLIC_PORT: String(publicPort),
    MUXIVA_DSH_BRIDGE_INTERNAL_PORT: String(internalPort),
    MUXIVA_DSH_RUNTIME_PORT: String(runtimePort),
  }
  const started = performance.now()
  const child = spawn(process.execPath, ['scripts/cli.mjs', 'start'], {
    cwd: root, env, stdio: ['ignore', 'pipe', 'pipe'],
  })
  let log = ''
  let ready = false
  const startupMs = await new Promise((resolveReady, reject) => {
    const timer = setTimeout(() => reject(new Error(`${label} startup timed out\n${log}`)), 180_000)
    const inspect = chunk => {
      const value = chunk.toString()
      process.stderr.write(value)
      log = `${log}${value}`.slice(-64_000)
      if (!ready && value.includes('[MUXIVA][INFO][runtime.started]')) {
        ready = true
        clearTimeout(timer)
        resolveReady(performance.now() - started)
      }
    }
    child.stdout.on('data', inspect)
    child.stderr.on('data', inspect)
    child.once('error', error => { clearTimeout(timer); reject(error) })
    child.once('exit', code => {
      if (!ready) {
        clearTimeout(timer)
        reject(new Error(`${label} exited during startup with ${code}\n${log}`))
      }
    })
  })
  return { child, env, publicPort, startupMs, getLog: () => log }
}

async function stopService(service) {
  if (service.child.exitCode === null) service.child.kill('SIGTERM')
  await new Promise(resolveExit => {
    if (service.child.exitCode !== null) resolveExit()
    else {
      const timer = setTimeout(() => {
        if (service.child.exitCode === null) service.child.kill('SIGKILL')
      }, 15_000)
      service.child.once('exit', () => { clearTimeout(timer); resolveExit() })
    }
  })
}

let cold = null
let service = null
let failure = null
try {
  if (mode === 'certify') {
    cold = await startService('process-cold runtime')
    console.log(`[benchmark] process-cold startup ${cold.startupMs.toFixed(1)} ms`)
    await stopService(cold)
  }
  service = await startService(mode === 'certify' ? 'warm runtime' : 'quick runtime')
  const coldStartMs = cold?.startupMs ?? service.startupMs
  const output = mode === 'certify'
    ? resolve(root, `benchmarks/results/v${metadata.version}-m1-pro.json`)
    : resolve(root, '.muxiva/benchmark-quick.json')
  await mkdir(dirname(output), { recursive: true })
  const python = resolve(root, '.muxiva/venv/bin/python')
  const runnerArgs = [
    'benchmarks/certify.py',
    '--mode', mode,
    '--port', String(service.publicPort),
    '--service-pid', String(service.child.pid),
    '--cold-start-ms', String(coldStartMs),
    '--warm-start-ms', String(service.startupMs),
    '--output', output,
    ...extra,
  ]
  await new Promise((resolveRunner, reject) => {
    const runner = spawn(python, runnerArgs, { cwd: root, env: service.env, stdio: 'inherit' })
    runner.once('error', reject)
    runner.once('exit', code => code === 0 ? resolveRunner() : reject(new Error(`benchmark runner exited with ${code}`)))
  })
  console.log(`[benchmark] report written to ${output}`)
} catch (error) {
  failure = error
} finally {
  if (service) await stopService(service)
  if (cold?.child.exitCode === null) await stopService(cold)
}

if (!failure && service && /Fatal Python error|Python runtime state:/.test(service.getLog())) {
  failure = new Error('Python Node Host crashed during benchmark shutdown')
}
if (failure) throw failure
