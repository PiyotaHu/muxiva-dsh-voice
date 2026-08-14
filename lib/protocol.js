export const PROTOCOL_VERSION = 'muxiva.dsh.voice/v1'
export const DEFAULT_VOICE_URL = 'ws://127.0.0.1:4390/voice'

const CLIENT_TYPES = new Set([
  'client.hello',
  'client.stop',
  'agent.delta',
  'agent.final',
  'agent.cancel',
])

const SERVER_TYPES = new Set([
  'server.ready',
  'speech.started',
  'speech.stopped',
  'asr.partial',
  'asr.final',
  'tts.started',
  'tts.stopped',
  'pipeline.metrics',
  'pipeline.error',
])

export function encodeControl(type, payload = {}) {
  if (!CLIENT_TYPES.has(type) && !SERVER_TYPES.has(type)) {
    throw new TypeError(`unknown voice control type: ${type}`)
  }
  return JSON.stringify({ version: PROTOCOL_VERSION, type, ...payload })
}

export function decodeControl(raw, direction = 'either') {
  const value = JSON.parse(typeof raw === 'string' ? raw : new TextDecoder().decode(raw))
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new TypeError('voice control frame must be an object')
  }
  if (value.version !== PROTOCOL_VERSION) throw new TypeError('unsupported voice protocol version')
  if (typeof value.type !== 'string') throw new TypeError('voice control frame requires type')
  if (direction === 'client' && !CLIENT_TYPES.has(value.type)) throw new TypeError('unexpected client control type')
  if (direction === 'server' && !SERVER_TYPES.has(value.type)) throw new TypeError('unexpected server control type')
  if (direction === 'either' && !CLIENT_TYPES.has(value.type) && !SERVER_TYPES.has(value.type)) {
    throw new TypeError('unknown voice control type')
  }
  return value
}

export function pcm16ToFloat32(buffer) {
  if (!(buffer instanceof ArrayBuffer) || buffer.byteLength % 2 !== 0) {
    throw new TypeError('PCM16 payload must be an even-sized ArrayBuffer')
  }
  const input = new Int16Array(buffer)
  const output = new Float32Array(input.length)
  for (let i = 0; i < input.length; i += 1) output[i] = input[i] / 32768
  return output
}

export function assistantText(snapshot) {
  const blocks = snapshot?.partial?.blocks
  if (Array.isArray(blocks)) return blocks.filter(block => block.kind === 'text').map(block => block.text).join('')
  const nodes = snapshot?.nodes
  if (!Array.isArray(nodes)) return ''
  for (let i = nodes.length - 1; i >= 0; i -= 1) {
    if (nodes[i]?.kind === 'assistant') {
      return nodes[i].blocks.filter(block => block.kind === 'text').map(block => block.text).join('')
    }
  }
  return ''
}

export function suffixDelta(previous, next) {
  if (next.startsWith(previous)) return next.slice(previous.length)
  return next
}
