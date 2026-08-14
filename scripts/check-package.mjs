import { readFile, readdir } from 'node:fs/promises'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(fileURLToPath(new URL('..', import.meta.url)))
for (const file of ['package.json', 'graph.json', 'models.lock.json']) JSON.parse(await readFile(resolve(root, file), 'utf8'))
const nodeDirs = await readdir(resolve(root, '.muxiva/nodes'))
if (nodeDirs.length !== 6) throw new Error(`expected six project Node Packs, found ${nodeDirs.length}`)
for (const directory of nodeDirs) JSON.parse(await readFile(resolve(root, '.muxiva/nodes', directory, 'muxiva.node.json'), 'utf8'))
const client = await readFile(resolve(root, 'lib/client.js'), 'utf8')
if (!client.startsWith('window.__ModuleLoader__.load({')) throw new Error('DSH browser artifact lacks the module-loader handoff')
if (!client.includes("id: '@muxiva/dsh-voice'")) throw new Error('DSH browser artifact id mismatch')
console.log('package contracts verified')
