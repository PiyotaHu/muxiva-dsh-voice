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
      .mxv-voice{--mxv-accent:#7c6cff;--mxv-cyan:#4de7ff;position:relative;width:100%;display:grid;place-items:center;padding:8px 0 3px;isolation:isolate}
      .mxv-voice__stage{position:relative;width:min(100%,430px);min-height:118px;display:grid;grid-template-columns:112px minmax(0,1fr);align-items:center;padding:10px 22px 10px 14px;border:1px solid color-mix(in srgb,var(--mxv-accent) 20%,transparent);border-radius:28px;background:radial-gradient(circle at 20% 50%,rgba(100,92,255,.12),transparent 42%),linear-gradient(135deg,color-mix(in srgb,var(--dsw-alias-bg-base,#fff) 94%,#7668ff 6%),color-mix(in srgb,var(--dsw-alias-bg-base,#fff) 98%,transparent));box-shadow:0 16px 48px rgba(33,28,84,.08),inset 0 1px 0 rgba(255,255,255,.42);overflow:hidden}
      .mxv-voice__stage:after{content:"";position:absolute;inset:0;background:linear-gradient(110deg,transparent 20%,rgba(255,255,255,.16) 46%,transparent 68%);transform:translateX(-120%);animation:mxv-scan 7s ease-in-out infinite;pointer-events:none}
      .mxv-voice__orb-wrap{position:relative;width:96px;height:96px;display:grid;place-items:center}
      .mxv-voice__halo{position:absolute;inset:3px;border-radius:50%;background:radial-gradient(circle,rgba(77,231,255,.22),rgba(124,108,255,.1) 52%,transparent 72%);transform:scale(calc(1 + var(--mxv-level,0) * .22));opacity:calc(.35 + var(--mxv-level,0) * .55);transition:transform 70ms linear,opacity 100ms linear}
      .mxv-voice__orbit{position:absolute;inset:6px;border-radius:50%;border:1px solid rgba(124,108,255,.3);border-left-color:rgba(77,231,255,.9);border-right-color:rgba(180,105,255,.72);animation:mxv-orbit 7s linear infinite;pointer-events:none}
      .mxv-voice__button{position:relative;width:76px;height:76px;border:1px solid rgba(255,255,255,.5);border-radius:50%;color:#fff;background:radial-gradient(circle at 34% 24%,#9cf5ff 0,rgba(102,132,255,.96) 25%,#7566ed 55%,#272342 100%);display:grid;place-items:center;cursor:pointer;box-shadow:0 12px 32px rgba(92,77,226,.32),inset 0 1px 8px rgba(255,255,255,.62),inset 0 -10px 22px rgba(22,18,67,.34);transition:transform .18s ease,box-shadow .18s ease,filter .18s ease;z-index:2}
      .mxv-voice__button:hover{transform:scale(1.055);filter:saturate(1.12);box-shadow:0 16px 40px rgba(92,77,226,.42),0 0 32px rgba(77,231,255,.2),inset 0 1px 9px rgba(255,255,255,.7)}
      .mxv-voice__button:active{transform:scale(.96)}
      .mxv-voice__button:focus-visible{outline:3px solid color-mix(in srgb,var(--mxv-cyan) 55%,white);outline-offset:4px}
      .mxv-voice[data-phase=listening] .mxv-voice__button,.mxv-voice[data-phase=hearing] .mxv-voice__button{animation:mxv-breathe 2.2s ease-in-out infinite}
      .mxv-voice[data-phase=thinking] .mxv-voice__orbit{animation-duration:1.4s}
      .mxv-voice[data-phase=speaking] .mxv-voice__button{background:radial-gradient(circle at 34% 24%,#d3a7ff 0,#9a65ff 30%,#5366ee 62%,#252243 100%);animation:mxv-speaking .9s ease-in-out infinite alternate}
      .mxv-voice[data-muted=true] .mxv-voice__button{background:radial-gradient(circle at 34% 24%,#aeb5c3,#596173 52%,#292d38);filter:saturate(.35);box-shadow:0 10px 28px rgba(35,39,52,.24),inset 0 1px 7px rgba(255,255,255,.38)}
      .mxv-voice[data-muted=true] .mxv-voice__orbit{animation-play-state:paused;border-color:rgba(130,137,151,.28)}
      .mxv-voice[data-phase=error]{--mxv-accent:#e45b6b;--mxv-cyan:#ff9d91}
      .mxv-voice[data-phase=error] .mxv-voice__button{background:radial-gradient(circle at 34% 24%,#ffc1b8,#e45b6b 48%,#632f46)}
      .mxv-voice__copy{position:relative;z-index:2;min-width:0;padding-left:4px}
      .mxv-voice__eyebrow{display:flex;align-items:center;gap:7px;color:var(--dsw-alias-label-tertiary,#707889);font-size:10px;font-weight:700;letter-spacing:.14em;text-transform:uppercase}
      .mxv-voice__dot{width:7px;height:7px;border-radius:50%;background:#9ca3af;box-shadow:0 0 0 3px rgba(156,163,175,.12)}
      .mxv-voice[data-active=true] .mxv-voice__dot{background:#48ddb0;box-shadow:0 0 0 3px rgba(72,221,176,.14),0 0 14px rgba(72,221,176,.65)}
      .mxv-voice__status{margin-top:7px;color:var(--dsw-alias-label-primary,#20242c);font-size:15px;font-weight:650;line-height:21px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      .mxv-voice__hint{margin-top:2px;color:var(--dsw-alias-label-tertiary,#707889);font-size:11px;line-height:16px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      .mxv-voice__end{position:absolute;right:13px;top:11px;z-index:3;border:0;background:transparent;color:var(--dsw-alias-label-tertiary,#7c8391);font:600 10px/1.2 inherit;cursor:pointer;padding:5px 7px;border-radius:7px}.mxv-voice__end:hover{background:rgba(110,106,150,.08);color:var(--dsw-alias-label-primary,#252933)}
      @keyframes mxv-orbit{to{transform:rotate(360deg)}}
      @keyframes mxv-breathe{50%{transform:scale(1.035);filter:saturate(1.18) brightness(1.04)}}
      @keyframes mxv-speaking{to{transform:scale(1.045);box-shadow:0 18px 42px rgba(118,80,238,.48),0 0 34px rgba(77,231,255,.18),inset 0 1px 9px rgba(255,255,255,.7)}}
      @keyframes mxv-scan{0%,58%{transform:translateX(-120%)}78%,100%{transform:translateX(120%)}}
      @media (max-width:520px){.mxv-voice__stage{grid-template-columns:94px minmax(0,1fr);padding-left:8px}.mxv-voice__orb-wrap{transform:scale(.88)}}
      @media (prefers-reduced-motion:reduce){.mxv-voice__stage:after,.mxv-voice__orbit,.mxv-voice__button{animation:none!important}.mxv-voice__button,.mxv-voice__halo{transition:none}}
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
        this.state = { phase: 'idle', level: 0, partial: '', error: '', connected: false, muted: false }
        this.listeners = new Set()
        this.socket = null
        this.audio = null
        this.stream = null
        this.micNode = null
        this.sources = new Set()
        this.playAt = 0
        this.playbackTimer = null
        this.synthesisDone = false
        this.sessionId = null
        this.sessionFace = null
        this.unsubSession = null
        this.answerKey = ''
        this.answerText = ''
        this.answerWasFinal = false
        this.bargeInConfirmed = false
        this.sentences = new SentenceBuffer((type, payload) => this.send(type, payload))
      }
      subscribe = (listener) => { this.listeners.add(listener); return () => this.listeners.delete(listener) }
      getSnapshot = () => this.state
      set(patch) { this.state = { ...this.state, ...patch }; for (const listener of [...this.listeners]) listener() }
      send(type, payload = {}) { if (this.socket?.readyState === WebSocket.OPEN) this.socket.send(control(type, payload)) }
      async toggle(sessionId) { return this.state.phase === 'idle' || this.state.phase === 'error' ? this.start(sessionId) : this.toggleMute() }
      toggleMute() {
        const muted = !this.state.muted
        this.send(muted ? 'client.mute' : 'client.unmute')
        this.set({ muted, level: muted ? 0 : this.state.level, partial: muted ? '' : this.state.partial })
      }
      async start(sessionId) {
        this.set({ phase: 'connecting', error: '', partial: '' })
        try {
          this.sessionId = sessionId
          this.bindSession(sessionId)
          await this.openAudio()
          await this.openSocket()
          this.set({ phase: 'listening', connected: true, muted: false })
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
          const muted = this.state.muted
          this.set({ level: muted ? 0 : Math.min(1, event.data.level * 8) })
          if (!muted && this.socket?.readyState === WebSocket.OPEN) this.socket.send(event.data.pcm)
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
            this.bargeInConfirmed = false
            this.set({ phase: 'hearing', partial: '' })
          }
          if (message.type === 'barge.in') await this.confirmBargeIn()
          if (message.type === 'speech.stopped') this.set({ phase: 'hearing' })
          if (message.type === 'asr.partial') this.set({ phase: 'hearing', partial: String(message.text || '') })
          if (message.type === 'asr.final') {
            const text = String(message.text || '').trim()
            this.set({ phase: 'thinking', partial: text })
            if (text) {
              await this.confirmBargeIn()
              const mode = this.sessionFace.getSnapshot().running ? 'steer' : 'queue'
              const result = await this.sessionFace.prompt([{ type: 'text', text }], mode)
              if (!result.ok) throw new Error(`${result.error.code}: ${result.error.message}`)
            }
          }
          if (message.type === 'asr.rejected') {
            this.bargeInConfirmed = false
            this.set({ phase: 'listening', partial: '' })
          }
          if (message.type === 'tts.started') { this.synthesisDone = false; this.set({ phase: 'speaking' }) }
          if (message.type === 'tts.stopped') { this.synthesisDone = true; this.finishPlaybackWhenReady() }
          if (message.type === 'pipeline.error') throw new Error(String(message.message || 'voice pipeline failed'))
        } catch (error) {
          this.set({ phase: 'error', error: error instanceof Error ? error.message : String(error) })
        }
      }
      async confirmBargeIn() {
        if (this.bargeInConfirmed) return
        this.bargeInConfirmed = true
        this.stopPlayback()
        this.sentences.clear()
        const snapshot = this.sessionFace?.getSnapshot()
        if (snapshot?.running) await this.sessionFace.cancel()
        this.set({ phase: 'hearing' })
      }
      play(pcm) {
        if (!this.audio || pcm.byteLength % 2) return
        const input = new Int16Array(pcm)
        const buffer = this.audio.createBuffer(1, input.length, 24000)
        const channel = buffer.getChannelData(0)
        for (let i = 0; i < input.length; i += 1) channel[i] = input[i] / 32768
        const source = this.audio.createBufferSource(); source.buffer = buffer; source.connect(this.audio.destination)
        this.sources.add(source); source.onended = () => { this.sources.delete(source); this.finishPlaybackWhenReady() }
        this.playAt = Math.max(this.audio.currentTime + 0.025, this.playAt)
        source.start(this.playAt); this.playAt += buffer.duration
        this.finishPlaybackWhenReady()
      }
      finishPlaybackWhenReady() {
        if (!this.synthesisDone || !this.audio) return
        clearTimeout(this.playbackTimer)
        const delay = Math.max(120, (this.playAt - this.audio.currentTime) * 1000 + 120)
        this.playbackTimer = setTimeout(() => {
          if (this.synthesisDone && this.sources.size === 0) this.set({ phase: 'listening', partial: '' })
        }, delay)
      }
      stopPlayback() { clearTimeout(this.playbackTimer); this.playbackTimer = null; this.synthesisDone = false; for (const source of this.sources) { try { source.stop() } catch {} } this.sources.clear(); this.playAt = this.audio?.currentTime ?? 0 }
      async stop(sendStop = true) {
        if (sendStop) this.send('client.stop')
        this.socket?.close(); this.socket = null
        this.stopPlayback(); this.sentences.clear()
        this.unsubSession?.(); this.unsubSession = null; this.sessionFace = null
        this.micNode?.disconnect(); this.micNode = null
        for (const track of this.stream?.getTracks?.() ?? []) track.stop()
        this.stream = null; this.sessionId = null; this.bargeInConfirmed = false
        this.set({ phase: 'idle', connected: false, partial: '', level: 0, error: '', muted: false })
      }
      dispose = () => { this.stop(false) }
    }

    function MicrophoneIcon({ muted = false }) {
      return React.createElement('svg', { width: 27, height: 27, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.65, strokeLinecap: 'round' },
        React.createElement('rect', { x: 9, y: 3, width: 6, height: 11, rx: 3 }),
        React.createElement('path', { d: 'M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21M9 21h6' }),
        muted ? React.createElement('path', { d: 'M4 4l16 16', strokeWidth: 2.2 }) : null)
    }

    function VoiceButton({ session, controller }) {
      const state = React.useSyncExternalStore(controller.subscribe, controller.getSnapshot, controller.getSnapshot)
      const active = !['idle', 'error'].includes(state.phase)
      const visualPhase = state.muted ? 'muted' : state.phase
      const labels = { idle: '点击开启本地语音', connecting: '正在连接 Muxiva', listening: '我在听', hearing: state.partial || '正在识别你的声音', thinking: 'Agent 正在思考', speaking: '正在回答', error: state.error || '本地语音连接失败' }
      const hints = { idle: '麦克风 · VAD · ASR · Agent · TTS', connecting: '正在装载本地实时链路…', listening: '随时开口，也可以打断回答', hearing: state.partial ? '实时转写' : '检测到语音', thinking: '答案生成后会自动播放', speaking: '直接说话即可打断', error: '点击重试，并确认 voice runtime 已启动' }
      if (state.muted) { labels.muted = '麦克风已静音'; hints.muted = '实时链路保持连接，再按一次恢复收音' }
      return React.createElement('div', { className: 'mxv-voice', 'data-phase': visualPhase, 'data-active': active && !state.muted, 'data-muted': state.muted },
        React.createElement('div', { className: 'mxv-voice__stage' },
          React.createElement('div', { className: 'mxv-voice__orb-wrap', style: { '--mxv-level': String(state.level) } },
            React.createElement('span', { className: 'mxv-voice__halo' }),
            React.createElement('span', { className: 'mxv-voice__orbit' }),
            React.createElement('button', {
              type: 'button', className: 'mxv-voice__button',
              'aria-label': active ? (state.muted ? '恢复麦克风收音' : '暂时静音麦克风') : '开始本地语音', 'aria-pressed': state.muted,
              onClick: () => controller.toggle(session.sessionId),
            }, React.createElement(MicrophoneIcon, { muted: state.muted }))),
          React.createElement('div', { className: 'mxv-voice__copy', 'aria-live': 'polite' },
            React.createElement('div', { className: 'mxv-voice__eyebrow' }, React.createElement('span', { className: 'mxv-voice__dot' }), 'MUXIVA LOCAL VOICE'),
            React.createElement('div', { className: 'mxv-voice__status', role: state.phase === 'error' ? 'alert' : undefined }, labels[visualPhase] || visualPhase),
            React.createElement('div', { className: 'mxv-voice__hint' }, hints[visualPhase] || '')),
          active ? React.createElement('button', { type: 'button', className: 'mxv-voice__end', onClick: () => controller.stop(), 'aria-label': '结束本地语音连接' }, '结束') : null))
    }

    exports.inject = ['slots', 'sessions']
    exports.apply = function apply(ctx) {
      installCss()
      const controller = new VoiceController(ctx)
      ctx.effect(() => controller.dispose, 'muxiva voice controller')
      ctx.slots.inject('conversation.input.dock', () => ctx.slots.register({
        name: 'conversation.input.dock', id: 'muxiva-dsh-voice', order: 80,
        inject: () => ({ controller }),
      }, VoiceButton))
    }
    return module.exports
  },
})
