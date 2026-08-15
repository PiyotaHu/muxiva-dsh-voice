import { readFile, readdir } from 'node:fs/promises'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(fileURLToPath(new URL('..', import.meta.url)))
for (const file of ['package.json', 'graph.json', 'models.lock.json', 'benchmarks/schema.json']) JSON.parse(await readFile(resolve(root, file), 'utf8'))
const metadata = JSON.parse(await readFile(resolve(root, 'package.json'), 'utf8'))
if (metadata.publishConfig?.access !== 'public') throw new Error('scoped npm package must publish publicly')
if (metadata.publishConfig?.registry !== 'https://registry.npmjs.org/') throw new Error('npm release registry is not pinned')
const graph = JSON.parse(await readFile(resolve(root, 'graph.json'), 'utf8'))
const modelLock = JSON.parse(await readFile(resolve(root, 'models.lock.json'), 'utf8'))
const graphText = JSON.stringify(graph)
const modelText = JSON.stringify(modelLock)
if (graphText.toLowerCase().includes('kokoro') || modelText.toLowerCase().includes('kokoro')) throw new Error('Kokoro remains in the runtime contract')
if (!graph.nodes.some(node => node.node_type === 'muxiva.qwen3_tts')) throw new Error('Qwen3-TTS Node Pack is not wired into the graph')
if (!modelLock.models.some(model => model.id === 'qwen3-tts-12hz-0.6b-customvoice-8bit')) throw new Error('pinned Qwen3-TTS model is missing')
const nodeDirs = await readdir(resolve(root, '.muxiva/nodes'))
if (nodeDirs.length !== 7) throw new Error(`expected seven project Node Packs, found ${nodeDirs.length}`)
for (const directory of nodeDirs) JSON.parse(await readFile(resolve(root, '.muxiva/nodes', directory, 'muxiva.node.json'), 'utf8'))
const client = await readFile(resolve(root, 'lib/client.js'), 'utf8')
if (!client.startsWith('window.__ModuleLoader__.load({')) throw new Error('DSH browser artifact lacks the module-loader handoff')
if (!client.includes("id: '@muxiva/dsh-voice'")) throw new Error('DSH browser artifact id mismatch')
console.log('package contracts verified')
