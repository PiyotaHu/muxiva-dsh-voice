import assert from 'node:assert/strict'
import test from 'node:test'

test('prosody buffer starts early once and sends the remaining full context once', async () => {
  let definition
  globalThis.window = {
    __ModuleLoader__: {
      load(value) { definition = value },
    },
  }
  process.env.NODE_ENV = 'test'
  await import(`../lib/client.js?prosody-test=${Date.now()}`)
  const plugin = definition.factory(() => ({}))
  const sent = []
  const buffer = new plugin.__testing.SentenceBuffer((type, payload) => sent.push({ type, ...payload }))

  buffer.push('好的。')
  buffer.push('我会保持统一的语速、语调和情绪，')
  assert.deepEqual(sent, [], 'wait for one substantial natural phrase')

  buffer.push('避免每隔两三个字就重新起调，让整段回答听起来更自然、更连贯。')
  assert.equal(sent.length, 1)
  assert.equal(sent[0].type, 'agent.delta')
  assert.ok(sent[0].text.length >= 48)

  buffer.push('后续内容即使包含多个句号，也继续作为同一段完整上下文。')
  buffer.push('这样一轮长回答最多只会调用两次语音生成。')
  assert.equal(sent.length, 1, 'never create a second partial TTS generation')

  buffer.flush()
  assert.equal(sent.length, 2)
  assert.equal(sent[1].type, 'agent.final')
  assert.ok(sent[1].text.includes('最多只会调用两次'))

  delete process.env.NODE_ENV
  delete globalThis.window
})

test('short answers use one complete-context TTS generation', async () => {
  let definition
  globalThis.window = { __ModuleLoader__: { load(value) { definition = value } } }
  process.env.NODE_ENV = 'test'
  await import(`../lib/client.js?short-answer-test=${Date.now()}`)
  const plugin = definition.factory(() => ({}))
  const sent = []
  const buffer = new plugin.__testing.SentenceBuffer((type, payload) => sent.push({ type, ...payload }))
  buffer.push('这是一个短回答。')
  buffer.flush()
  assert.deepEqual(sent, [{ type: 'agent.final', text: '这是一个短回答。' }])
  delete process.env.NODE_ENV
  delete globalThis.window
})
