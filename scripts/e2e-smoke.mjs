#!/usr/bin/env node
import { spawn } from 'node:child_process'
import { createServer } from 'node:net'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const freePort = () => new Promise((resolvePort, reject) => {
  const server = createServer()
  server.once('error', reject)
  server.listen(0, '127.0.0.1', () => {
    const address = server.address()
    const port = typeof address === 'object' && address ? address.port : null
    server.close(error => error ? reject(error) : resolvePort(port))
  })
})
const [publicPort, internalPort, runtimePort] = await Promise.all([freePort(), freePort(), freePort()])
const testEnvironment = {
  ...process.env,
  MUXIVA_DSH_BRIDGE_PUBLIC_PORT: String(publicPort),
  MUXIVA_DSH_BRIDGE_INTERNAL_PORT: String(internalPort),
  MUXIVA_DSH_RUNTIME_PORT: String(runtimePort),
}
const service = spawn(process.execPath, ['scripts/cli.mjs', 'start'], {
  cwd: root,
  stdio: ['ignore', 'pipe', 'pipe'],
  env: testEnvironment,
})

let settled = false
let runtimeLog = ''
const ready = new Promise((resolveReady, reject) => {
  const timer = setTimeout(() => reject(new Error(`voice runtime startup timed out\n${runtimeLog}`)), 60_000)
  const inspect = chunk => {
    const value = chunk.toString()
    process.stderr.write(value)
    runtimeLog = `${runtimeLog}${value}`.slice(-32_000)
    if (!settled && value.includes('[MUXIVA][INFO][runtime.started]')) {
      settled = true
      clearTimeout(timer)
      resolveReady()
    }
  }
  service.stdout.on('data', inspect)
  service.stderr.on('data', inspect)
  service.once('exit', code => {
    if (!settled) {
      clearTimeout(timer)
      reject(new Error(`voice runtime exited during startup with ${code}\n${runtimeLog}`))
    }
  })
  service.once('error', reject)
})

let failure = null
try {
  await ready
  await new Promise((resolveTest, reject) => {
    const test = spawn(resolve(root, '.muxiva/venv/bin/python'), ['test/e2e_smoke.py'], {
      cwd: root,
      stdio: 'inherit',
      env: testEnvironment,
    })
    test.once('error', reject)
    test.once('exit', code => code === 0 ? resolveTest() : reject(new Error(`end-to-end smoke exited with ${code}`)))
  })
} catch (error) {
  failure = error
} finally {
  if (service.exitCode === null) service.kill('SIGTERM')
  const serviceCode = await new Promise(resolveExit => {
    if (service.exitCode !== null) resolveExit(service.exitCode)
    else service.once('exit', resolveExit)
  })
  if (!failure && serviceCode !== 0) failure = new Error(`voice runtime exited with ${serviceCode}`)
  if (!failure && /Fatal Python error|Python runtime state:/.test(runtimeLog)) {
    failure = new Error(`Python Node Host crashed during shutdown\n${runtimeLog}`)
  }
}

if (failure) throw failure
