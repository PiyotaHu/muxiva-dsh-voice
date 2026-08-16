import { existsSync } from 'node:fs'
import { homedir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

export const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')

const sourceCheckout = existsSync(resolve(packageRoot, '.git'))
const override = process.env.MUXIVA_DSH_VOICE_HOME
const platformDataRoot = process.platform === 'darwin'
  ? join(homedir(), 'Library', 'Application Support', 'Muxiva', 'dsh-voice')
  : process.platform === 'win32'
    ? join(process.env.LOCALAPPDATA || join(homedir(), 'AppData', 'Local'), 'Muxiva', 'dsh-voice')
    : join(process.env.XDG_DATA_HOME || join(homedir(), '.local', 'share'), 'muxiva', 'dsh-voice')

// A checkout already lives outside npm/npx caches and keeps its existing developer layout.
// Published packages use stable user data so cache cleanup never discards models or the venv.
export const packagedLayout = Boolean(override) || !sourceCheckout
export const dataRoot = resolve(override || (sourceCheckout ? packageRoot : platformDataRoot))
export const modelsRoot = packagedLayout ? resolve(dataRoot, 'models') : resolve(packageRoot, '.models')
export const venvRoot = packagedLayout ? resolve(dataRoot, 'venv') : resolve(packageRoot, '.muxiva/venv')
export const runtimeLog = packagedLayout ? resolve(dataRoot, 'runtime.log') : resolve(packageRoot, '.muxiva/runtime.log')

export function dataPath(relative) {
  if (!relative.startsWith('.models/')) return resolve(packageRoot, relative)
  return resolve(modelsRoot, relative.slice('.models/'.length))
}

export function runtimeRoot(version) {
  return packagedLayout ? resolve(dataRoot, 'runtime', version) : packageRoot
}
