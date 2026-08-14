#!/usr/bin/env node
import { spawn } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const service = spawn(process.execPath, ['scripts/cli.mjs', 'start'], {
  cwd: root,
  stdio: ['ignore', 'pipe', 'pipe'],
})

let settled = false
let startupLog = ''
const ready = new Promise((resolveReady, reject) => {
  const timer = setTimeout(() => reject(new Error(`voice runtime startup timed out\n${startupLog}`)), 60_000)
  const inspect = chunk => {
    const value = chunk.toString()
    process.stderr.write(value)
    startupLog = `${startupLog}${value}`.slice(-16_000)
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
      reject(new Error(`voice runtime exited during startup with ${code}\n${startupLog}`))
    }
  })
  service.once('error', reject)
})

try {
  await ready
  await new Promise((resolveTest, reject) => {
    const test = spawn(resolve(root, '.muxiva/venv/bin/python'), ['test/e2e_smoke.py'], {
      cwd: root,
      stdio: 'inherit',
    })
    test.once('error', reject)
    test.once('exit', code => code === 0 ? resolveTest() : reject(new Error(`end-to-end smoke exited with ${code}`)))
  })
} finally {
  if (service.exitCode === null) service.kill('SIGTERM')
  await new Promise(resolveExit => {
    if (service.exitCode !== null) resolveExit()
    else service.once('exit', resolveExit)
  })
}
