import assert from 'node:assert/strict'
import test from 'node:test'

test('prosody buffer combines tiny sentences before starting TTS', async () => {
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
  assert.deepEqual(sent, [], 'tiny clauses must remain buffered')

  buffer.push('避免每隔两三个字就重新起调，让整段回答听起来更自然。')
  assert.equal(sent.length, 1)
  assert.equal(sent[0].type, 'agent.delta')
  assert.ok(sent[0].text.startsWith('好的。'))
  assert.ok(sent[0].text.length >= 36)

  buffer.push('明白。')
  buffer.flush()
  assert.equal(sent.at(-1).type, 'agent.final')
  assert.equal(sent.at(-1).text, '明白。')

  delete process.env.NODE_ENV
  delete globalThis.window
})
