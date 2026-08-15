const install = 'dsh plugin --profile web add @muxiva/dsh-voice'
const toast = document.querySelector('.toast')

function copied(message = '已复制') {
  if (!toast) return
  toast.textContent = message
  toast.classList.add('show')
  setTimeout(() => toast.classList.remove('show'), 1600)
}

for (const button of document.querySelectorAll('[data-copy-install]')) button.addEventListener('click', async () => {
  await navigator.clipboard.writeText(install)
  copied('安装命令已复制')
})

for (const button of document.querySelectorAll('[data-copy-code]')) button.addEventListener('click', async () => {
  await navigator.clipboard.writeText(button.parentElement.querySelector('code').textContent)
  copied()
})

const orb = document.querySelector('.orb')
const demo = document.querySelector('.voice-demo')
const title = document.querySelector('[data-demo-title]')
const subtitle = document.querySelector('[data-demo-subtitle]')
const states = [
  ['listening', '正在聆听', '麦克风音频进入 Muxiva 有界队列'],
  ['hearing', '我听见了', 'Silero VAD · Zipformer ASR partial'],
  ['thinking', 'Agent 思考中', 'DSH Session · Model · Tools'],
  ['speaking', '正在回答', 'Qwen3-TTS · MLX · 24 kHz · 随时可以打断'],
]
let state = -1
let timer

function advance() {
  state = (state + 1) % states.length
  const [name, heading, detail] = states[state]
  demo.dataset.state = name
  title.textContent = heading
  subtitle.textContent = detail
}

orb?.addEventListener('click', () => {
  clearInterval(timer)
  advance()
  timer = setInterval(advance, 1800)
})
