#!/usr/bin/env node
import { existsSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(fileURLToPath(new URL('..', import.meta.url)))
const metadata = JSON.parse(await readFile(resolve(root, 'package.json'), 'utf8'))
const markdown = ['README.md', 'README.zh-CN.md', ...[
  'docs/guide/compatibility.md',
  'docs/guide/getting-started.md',
  'docs/guide/performance.md',
  'docs/promotion/dsh-show-your-plugins.md',
  'docs/promotion/discord-launch.md',
  `docs/releases/${metadata.version}.md`,
]]
const publicCommand = 'dsh plugin --profile web add @muxiva/dsh-voice@alpha'

for (const relative of markdown) {
  const path = resolve(root, relative)
  if (!existsSync(path)) throw new Error(`required public document is missing: ${relative}`)
  const text = await readFile(path, 'utf8')
  for (const targetValue of text.matchAll(/\[[^\]]+\]\(([^)]+)\)/g)) {
    const target = targetValue[1].split('#', 1)[0]
    if (!target || target.includes('://')) continue
    if (!existsSync(resolve(dirname(path), target))) throw new Error(`${relative} links missing local file: ${target}`)
  }
}

for (const relative of ['README.md', 'README.zh-CN.md', 'showcase/index.html', 'showcase/docs.html', 'docs/guide/getting-started.md']) {
  const text = await readFile(resolve(root, relative), 'utf8')
  if (!text.includes(publicCommand)) throw new Error(`${relative} is missing the public alpha install command`)
}

const publicSurface = await Promise.all(['README.md', 'README.zh-CN.md', 'showcase/index.html', 'showcase/docs.html'].map(path => readFile(resolve(root, path), 'utf8')))
for (const stale of ['公开一键安装随', '性能数据尚未发布', '公开安装尚未解锁', '非实测值']) {
  if (publicSurface.some(text => text.includes(stale))) throw new Error(`public surface contains stale release copy: ${stale}`)
}

const showcase = await readFile(resolve(root, 'showcase/index.html'), 'utf8')
if (!showcase.includes(`v${metadata.version}`)) throw new Error('Showcase release version is stale')
for (const asset of ['showcase/app.js', 'showcase/styles.css', 'showcase/favicon.svg']) {
  if (!existsSync(resolve(root, asset))) throw new Error(`Showcase asset is missing: ${asset}`)
}

console.log(`public documentation verified for ${metadata.version}`)
