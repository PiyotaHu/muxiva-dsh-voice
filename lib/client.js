window.__ModuleLoader__.load({
  id: '@muxiva/dsh-voice',
  factory: (require) => {
    const module = { exports: {} }
    const exports = module.exports
    Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' })
    const React = require('react')

    const VERSION = 'muxiva.dsh.voice/v1'
    const DEFAULT_URL = 'ws://127.0.0.1:4390/voice'
    const CSS = `
      .mxv-voice{position:relative;display:inline-flex;align-items:center}
      .mxv-voice__button{position:relative;width:30px;height:30px;border:0;border-radius:999px;color:var(--dsw-alias-label-secondary,#5d6573);background:transparent;display:grid;place-items:center;cursor:pointer;transition:background .16s ease,color .16s ease,transform .16s ease}
      .mxv-voice__button:hover{background:var(--dsw-alias-interactive-bg-hover,rgba(76,87,109,.09));color:var(--dsw-alias-label-primary,#20242c)}
      .mxv-voice__button:active{transform:scale(.94)}
      .mxv-voice__button[data-active=true]{color:#fff;background:linear-gradient(135deg,#4d68ff,#8b5cf6);box-shadow:0 5px 18px rgba(91,80,225,.28)}
      .mxv-voice__button[data-error=true]{color:#fff;background:#d84f4f}
      .mxv-voice__ring{position:absolute;inset:-3px;border:1.5px solid rgba(112,91,255,.45);border-radius:999px;transform:scale(var(--mxv-level,1));opacity:var(--mxv-opacity,0);transition:transform 60ms linear,opacity 120ms ease;pointer-events:none}
      .mxv-voice__dot{position:absolute;right:-1px;bottom:-1px;width:7px;height:7px;border-radius:99px;background:#20b486;border:2px solid var(--dsw-alias-bg-base,#fff)}
      .mxv-voice__tip{position:absolute;left:50%;bottom:38px;z-index:50;transform:translateX(-50%);white-space:nowrap;padding:6px 9px;border-radius:8px;color:#fff;background:rgba(25,28,35,.94);font-size:11px;line-height:16px;box-shadow:0 8px 24px rgba(0,0,0,.18);pointer-events:none}
      @media (prefers-reduced-motion:reduce){.mxv-voice__button,.mxv-voice__ring{transition:none}}
    `

    function installCss() {
      if (document.querySelector('style[data-plugin-css="@muxiva/dsh-voice"]')) return
      const style = document.createElement('style')
      style.dataset.plugin = '@muxiva/dsh-voice'
      style.dataset.pluginCss = '@muxiva/dsh-voice'
      style.textContent = CSS
      document.head.appendChild(style)
    }

    function control(type, payload = {}) {
      return JSON.stringify({ version: VERSION, type, ...payload })
    }

    function decode(raw) {
      const value = JSON.parse(raw)
      if (value?.version !== VERSION || typeof value.type !== 'string') throw new Error('incompatible Muxiva voice bridge')
      return value
    }

    function blocksText(blocks) {
      return Array.isArray(blocks)
        ? blocks.filter(block => block.kind === 'text').map(block => block.text).join('')
        : ''
    }

    function latestAssistant(snapshot) {
      if (snapshot?.partial) return { key: `partial:${snapshot.partial.turn}:${snapshot.partial.step}`, text: blocksText(snapshot.partial.blocks), final: false }
      for (let i = (snapshot?.nodes?.length ?? 0) - 1; i >= 0; i -= 1) {
        const node = snapshot.nodes[i]
        if (node?.kind === 'assistant') return { key: `final:${node.turn}:${node.step}`, text: blocksText(node.blocks), final: true }
      }
      return { key: '', text: '', final: false }
    }

    class SentenceBuffer {
      constructor(send) {
        this.send = send
        this.value = ''
      }
      push(text) {
        this.value += text
        const boundary = /[。！？!?；;：:\n]|\.(?:\s|$)/g
        let end = 0
        let match
        while ((match = boundary.exec(this.value)) !== null) end = match.index + match[0].length
        if (end === 0 && this.value.length < 72) return
        if (end === 0) end = 48
        const ready = this.value.slice(0, end).trim()
        this.value = this.value.slice(end)
        if (ready) this.send('agent.delta', { text: ready })
      }
      flush() {
        const ready = this.value.trim()
        this.value = ''
        if (ready) this.send('agent.final', { text: ready })
      }
      clear() { this.value = '' }
    }

    const WORKLET = `
      class MuxivaMic extends AudioWorkletProcessor {
        constructor(options){super();this.target=16000;this.phase=0;this.pending=[];this.sum=0;this.count=0;this.sourceRate=sampleRate}
        process(inputs){const input=inputs[0]?.[0];if(!input)return true;const ratio=this.sourceRate/this.target;while(this.phase<input.length){const left=Math.floor(this.phase);const right=Math.min(left+1,input.length-1);const mix=this.phase-left;const sample=input[left]*(1-mix)+input[right]*mix;this.pending.push(sample);this.sum+=sample*sample;this.count+=1;this.phase+=ratio;if(this.pending.length>=320)this.emit()}this.phase-=input.length;return true}
        emit(){const pcm=new Int16Array(this.pending.length);for(let i=0;i<this.pending.length;i++){const v=Math.max(-1,Math.min(1,this.pending[i]));pcm[i]=v<0?v*32768:v*32767}const level=Math.sqrt(this.sum/Math.max(1,this.count));this.pending=[];this.sum=0;this.count=0;this.port.postMessage({pcm:pcm.buffer,level},[pcm.buffer])}
      }
      registerProcessor('muxiva-mic',MuxivaMic)
    `

    class VoiceController {
      constructor(ctx) {
        this.ctx = ctx
        this.state = { phase: 'idle', level: 0, partial: '', error: '', connected: false }
        this.listeners = new Set()
        this.socket = null
        this.audio = null
        this.stream = null
        this.micNode = null
        this.sources = new Set()
        this.playAt = 0
        this.sessionId = null
        this.sessionFace = null
        this.unsubSession = null
        this.answerKey = ''
        this.answerText = ''
        this.answerWasFinal = false
        this.sentences = new SentenceBuffer((type, payload) => this.send(type, payload))
      }
      subscribe = (listener) => { this.listeners.add(listener); return () => this.listeners.delete(listener) }
      getSnapshot = () => this.state
      set(patch) { this.state = { ...this.state, ...patch }; for (const listener of [...this.listeners]) listener() }
      send(type, payload = {}) { if (this.socket?.readyState === WebSocket.OPEN) this.socket.send(control(type, payload)) }
      async toggle(sessionId) { return this.state.phase === 'idle' || this.state.phase === 'error' ? this.start(sessionId) : this.stop() }
      async start(sessionId) {
        this.set({ phase: 'connecting', error: '', partial: '' })
        try {
          this.sessionId = sessionId
          this.bindSession(sessionId)
          await this.openAudio()
          await this.openSocket()
          this.set({ phase: 'listening', connected: true })
        } catch (error) {
          await this.stop(false)
          this.set({ phase: 'error', error: error instanceof Error ? error.message : String(error) })
        }
      }
      async openSocket() {
        const url = localStorage.getItem('muxiva.voice.url') || DEFAULT_URL
        const socket = new WebSocket(url)
        socket.binaryType = 'arraybuffer'
        this.socket = socket
        await new Promise((resolve, reject) => {
          const timer = setTimeout(() => reject(new Error(`Muxiva voice pipeline is not reachable at ${url}`)), 4000)
          socket.onopen = () => { clearTimeout(timer); resolve() }
          socket.onerror = () => { clearTimeout(timer); reject(new Error(`cannot connect to ${url}`)) }
        })
        socket.onmessage = event => this.onMessage(event)
        socket.onclose = () => {
          if (this.state.phase !== 'idle') this.set({ phase: 'error', connected: false, error: 'Muxiva voice pipeline disconnected' })
        }
        this.send('client.hello', { sessionId: String(this.sessionId), audio: { encoding: 'pcm_s16le', sampleRateHz: 16000, channels: 1 } })
      }
      async openAudio() {
        this.audio = this.audio || new AudioContext({ latencyHint: 'interactive' })
        await this.audio.resume()
        const url = URL.createObjectURL(new Blob([WORKLET], { type: 'text/javascript' }))
        try { await this.audio.audioWorklet.addModule(url) } finally { URL.revokeObjectURL(url) }
        this.stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true }, video: false })
        const source = this.audio.createMediaStreamSource(this.stream)
        this.micNode = new AudioWorkletNode(this.audio, 'muxiva-mic')
        this.micNode.port.onmessage = event => {
          this.set({ level: Math.min(1, event.data.level * 8) })
          if (this.socket?.readyState === WebSocket.OPEN) this.socket.send(event.data.pcm)
        }
        const silent = this.audio.createGain(); silent.gain.value = 0
        source.connect(this.micNode).connect(silent).connect(this.audio.destination)
      }
      bindSession(sessionId) {
        this.unsubSession?.()
        this.sessionFace = this.ctx.sessions.binding(sessionId)?.session ?? null
        if (!this.sessionFace) throw new Error('open a DSH session before starting voice')
        const pump = () => this.pumpAssistant(this.sessionFace.getSnapshot())
        this.unsubSession = this.sessionFace.subscribe(pump)
        pump()
      }
      pumpAssistant(snapshot) {
        const answer = latestAssistant(snapshot)
        const logicalKey = answer.key.replace(/^final:/, '').replace(/^partial:/, '')
        const priorKey = this.answerKey.replace(/^final:/, '').replace(/^partial:/, '')
        if (logicalKey !== priorKey) {
          this.answerText = ''
          this.answerWasFinal = false
          this.sentences.clear()
        }
        if (answer.text.startsWith(this.answerText)) this.sentences.push(answer.text.slice(this.answerText.length))
        else if (answer.text !== this.answerText) { this.sentences.clear(); this.sentences.push(answer.text) }
        this.answerKey = answer.key
        this.answerText = answer.text
        if (answer.final && !this.answerWasFinal) this.sentences.flush()
        this.answerWasFinal = answer.final
      }
      async onMessage(event) {
        if (event.data instanceof ArrayBuffer) { this.play(event.data); return }
        try {
          const message = decode(event.data)
          if (message.type === 'server.ready') this.set({ connected: true })
          if (message.type === 'speech.started') {
            this.stopPlayback()
            this.sentences.clear()
            this.send('agent.cancel', { reason: 'barge-in' })
            const snapshot = this.sessionFace?.getSnapshot()
            if (snapshot?.running) await this.sessionFace.cancel()
            this.set({ phase: 'hearing', partial: '' })
          }
          if (message.type === 'speech.stopped') this.set({ phase: 'thinking' })
          if (message.type === 'asr.partial') this.set({ phase: 'hearing', partial: String(message.text || '') })
          if (message.type === 'asr.final') {
            const text = String(message.text || '').trim()
            this.set({ phase: 'thinking', partial: text })
            if (text) {
              const mode = this.sessionFace.getSnapshot().running ? 'steer' : 'queue'
              const result = await this.sessionFace.prompt([{ type: 'text', text }], mode)
              if (!result.ok) throw new Error(`${result.error.code}: ${result.error.message}`)
            }
          }
          if (message.type === 'tts.started') this.set({ phase: 'speaking' })
          if (message.type === 'tts.stopped') this.set({ phase: 'listening', partial: '' })
          if (message.type === 'pipeline.error') throw new Error(String(message.message || 'voice pipeline failed'))
        } catch (error) {
          this.set({ phase: 'error', error: error instanceof Error ? error.message : String(error) })
        }
      }
      play(pcm) {
        if (!this.audio || pcm.byteLength % 2) return
        const input = new Int16Array(pcm)
        const buffer = this.audio.createBuffer(1, input.length, 24000)
        const channel = buffer.getChannelData(0)
        for (let i = 0; i < input.length; i += 1) channel[i] = input[i] / 32768
        const source = this.audio.createBufferSource(); source.buffer = buffer; source.connect(this.audio.destination)
        this.sources.add(source); source.onended = () => this.sources.delete(source)
        this.playAt = Math.max(this.audio.currentTime + 0.025, this.playAt)
        source.start(this.playAt); this.playAt += buffer.duration
      }
      stopPlayback() { for (const source of this.sources) { try { source.stop() } catch {} } this.sources.clear(); this.playAt = this.audio?.currentTime ?? 0 }
      async stop(sendStop = true) {
        if (sendStop) this.send('client.stop')
        this.socket?.close(); this.socket = null
        this.stopPlayback(); this.sentences.clear()
        this.unsubSession?.(); this.unsubSession = null; this.sessionFace = null
        this.micNode?.disconnect(); this.micNode = null
        for (const track of this.stream?.getTracks?.() ?? []) track.stop()
        this.stream = null; this.sessionId = null
        this.set({ phase: 'idle', connected: false, partial: '', level: 0, error: '' })
      }
      dispose = () => { this.stop(false) }
    }

    function MicrophoneIcon() {
      return React.createElement('svg', { width: 16, height: 16, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.9, strokeLinecap: 'round' },
        React.createElement('rect', { x: 9, y: 3, width: 6, height: 11, rx: 3 }),
        React.createElement('path', { d: 'M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21M9 21h6' }))
    }

    function VoiceButton({ session, controller }) {
      const state = React.useSyncExternalStore(controller.subscribe, controller.getSnapshot, controller.getSnapshot)
      const [hover, setHover] = React.useState(false)
      const active = !['idle', 'error'].includes(state.phase)
      const labels = { idle: '开始本地语音', connecting: '正在连接 Muxiva…', listening: '正在聆听', hearing: state.partial || '检测到语音', thinking: 'Agent 思考中', speaking: '正在播放', error: state.error }
      return React.createElement('div', { className: 'mxv-voice' },
        React.createElement('span', { className: 'mxv-voice__ring', style: { '--mxv-level': String(1 + state.level * .55), '--mxv-opacity': active ? String(.15 + state.level * .7) : '0' } }),
        React.createElement('button', {
          type: 'button', className: 'mxv-voice__button', 'data-active': active, 'data-error': state.phase === 'error',
          'aria-label': active ? '停止本地语音' : '开始本地语音', 'aria-pressed': active,
          onMouseEnter: () => setHover(true), onMouseLeave: () => setHover(false),
          onClick: () => controller.toggle(session.sessionId),
        }, React.createElement(MicrophoneIcon), state.connected && React.createElement('span', { className: 'mxv-voice__dot' })),
        hover && React.createElement('span', { className: 'mxv-voice__tip', role: state.phase === 'error' ? 'alert' : undefined }, labels[state.phase] || state.phase))
    }

    exports.inject = ['slots', 'sessions']
    exports.apply = function apply(ctx) {
      installCss()
      const controller = new VoiceController(ctx)
      ctx.effect(() => controller.dispose, 'muxiva voice controller')
      ctx.slots.inject('conversation.input.left', () => ctx.slots.register({
        name: 'conversation.input.left', id: 'muxiva-dsh-voice', order: 60,
        inject: () => ({ controller }),
      }, VoiceButton))
    }
    return module.exports
  },
})
