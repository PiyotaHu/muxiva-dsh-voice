#!/usr/bin/env node
import { readFile, readdir } from 'node:fs/promises'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(fileURLToPath(new URL('..', import.meta.url)))
const resultsDirectory = resolve(root, 'benchmarks/results')
const requiredVersionIndex = process.argv.indexOf('--require-version')
const requiredVersion = requiredVersionIndex === -1 ? null : process.argv[requiredVersionIndex + 1]
if (requiredVersionIndex !== -1 && !requiredVersion) throw new Error('--require-version needs a package version')

const distributionNames = [
  'browserCaptureToMuxivaFrame',
  'speechOnsetToBargeIn',
  'speechEndToAsrFinal',
  'firstAgentTextToFirstTtsPcm',
  'audioQueueAhead',
  'staleAudioAfterBargeIn',
]

function requireValue(condition, message) {
  if (!condition) throw new Error(message)
}

function distribution(value, path) {
  requireValue(value && Number.isInteger(value.samples) && value.samples > 0, `${path}.samples must be positive`)
  for (const percentile of ['p50', 'p95', 'p99']) {
    requireValue(Number.isFinite(value[percentile]) && value[percentile] >= 0, `${path}.${percentile} must be non-negative`)
  }
  requireValue(value.p50 <= value.p95 && value.p95 <= value.p99, `${path} percentiles must be ordered`)
}

function validate(report, file) {
  const at = message => `${file}: ${message}`
  requireValue(report.schemaVersion === 1, at('schemaVersion must be 1'))
  requireValue(/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/.test(report.release), at('invalid release'))
  requireValue(!Number.isNaN(Date.parse(report.generatedAt)), at('generatedAt must be ISO-8601'))
  requireValue(report.system?.chip && report.system?.os && report.system?.powerSource, at('system identity is incomplete'))
  requireValue(report.versions?.dshVoice === report.release, at('versions.dshVoice must equal release'))
  requireValue(/^[0-9a-f]{64}$/.test(report.modelLockSha256), at('invalid model lock SHA-256'))
  requireValue(report.workload?.turns >= 100, at('at least 100 turns are required'))
  requireValue(report.workload?.interruptions >= 30, at('at least 30 interruptions are required'))
  requireValue(report.workload?.idleMinutes >= 5, at('at least five idle minutes are required'))
  requireValue(report.workload?.soakMinutes >= 30, at('at least 30 soak minutes are required'))
  for (const name of distributionNames) distribution(report.latencyMs?.[name], at(`latencyMs.${name}`))
  distribution(report.throughput?.asrFinalRealtimeFactor, at('throughput.asrFinalRealtimeFactor'))
  distribution(report.throughput?.ttsRealtimeFactor, at('throughput.ttsRealtimeFactor'))
  for (const name of ['coldStartMs', 'warmStartMs', 'idleCpuPercent', 'activeCpuPercent', 'peakRssMb', 'modelDiskMb']) {
    requireValue(Number.isFinite(report.resources?.[name]) && report.resources[name] >= 0, at(`resources.${name} is required`))
  }
  requireValue(Number.isFinite(report.quality?.mandarinCer), at('quality.mandarinCer is required'))
  requireValue(Number.isFinite(report.quality?.englishWer), at('quality.englishWer is required'))
  requireValue(Number.isInteger(report.quality?.ttsUnderruns), at('quality.ttsUnderruns is required'))
  requireValue(report.stability?.completedTurns >= 100, at('stability.completedTurns must be at least 100'))
  requireValue(report.stability?.unboundedQueues === 0, at('unbounded queues fail certification'))
}

const files = (await readdir(resultsDirectory)).filter(file => file.endsWith('.json')).sort()
for (const file of files) validate(JSON.parse(await readFile(resolve(resultsDirectory, file), 'utf8')), file)

if (requiredVersion) {
  const matching = files.filter(file => file.startsWith(`v${requiredVersion}-`))
  requireValue(matching.length > 0, `no certified benchmark report for v${requiredVersion}`)
  const performanceDocument = await readFile(resolve(root, 'docs/guide/performance.md'), 'utf8')
  for (const file of matching) {
    requireValue(performanceDocument.includes(file), `docs/guide/performance.md does not link ${file}`)
  }
}

console.log(`performance reports verified: ${files.length}${requiredVersion ? `; required=${requiredVersion}` : ''}`)
