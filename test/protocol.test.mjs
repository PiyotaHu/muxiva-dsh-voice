import test from 'node:test'
import assert from 'node:assert/strict'
import {
  PROTOCOL_VERSION, assistantText, decodeControl, encodeControl, pcm16ToFloat32, suffixDelta,
} from '../lib/protocol.js'

test('control frames are versioned and direction checked', () => {
  const wire = encodeControl('agent.delta', { text: '你好' })
  assert.deepEqual(decodeControl(wire, 'client'), {
    version: PROTOCOL_VERSION,
    type: 'agent.delta',
    text: '你好',
  })
  assert.throws(() => decodeControl(wire, 'server'), /unexpected server/)
})

test('assistant text prefers the live partial and extracts text blocks only', () => {
  assert.equal(assistantText({ partial: { blocks: [
    { kind: 'reasoning', text: 'hidden' }, { kind: 'text', text: 'hello' },
  ] } }), 'hello')
  assert.equal(assistantText({ nodes: [{ kind: 'assistant', blocks: [{ kind: 'text', text: 'done' }] }] }), 'done')
})

test('suffix delta prevents repeated synthesis', () => {
  assert.equal(suffixDelta('hello', 'hello world'), ' world')
  assert.equal(suffixDelta('old', 'replacement'), 'replacement')
})

test('PCM16 conversion is normalized', () => {
  const pcm = new Int16Array([-32768, 0, 16384]).buffer
  assert.deepEqual([...pcm16ToFloat32(pcm)], [-1, 0, 0.5])
})
