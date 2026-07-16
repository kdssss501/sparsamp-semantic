import fs from 'node:fs/promises'
import path from 'node:path'
import { chromium } from 'playwright-core'

const baseUrl = process.env.SPARSAMP_WEB_URL ?? 'http://127.0.0.1:8000'
const outputDir = process.env.SCREENSHOT_DIR ?? path.resolve('../outputs/screenshots')
const edgePath = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'

await fs.mkdir(outputDir, { recursive: true })
const browser = await chromium.launch({ headless: true, executablePath: edgePath })

for (const viewport of [
  { name: 'desktop', width: 1440, height: 1000 },
  { name: 'mobile', width: 390, height: 844 },
]) {
  const page = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height } })
  const errors = []
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text())
  })
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto(baseUrl, { waitUntil: 'networkidle' })
  await page.getByText('隐写生成', { exact: true }).waitFor()

  if (viewport.name === 'desktop') {
    await page.getByRole('button', { name: '实验分析' }).click()
    await page.getByText('实验结果', { exact: true }).waitFor()
    const canvas = page.locator('canvas').first()
    await canvas.waitFor()
    const box = await canvas.boundingBox()
    if (!box || box.width < 300 || box.height < 200) throw new Error('experiment chart is not visible')
  } else {
    await page.getByRole('button', { name: '打开导航' }).click()
    await page.getByRole('button', { name: '接收解码' }).click()
    await page.getByText('接收与解码', { exact: true }).waitFor()
    await page.waitForTimeout(350)
  }

  const layout = await page.evaluate(() => ({
    width: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }))
  if (layout.scrollWidth > layout.width + 1) throw new Error(`horizontal overflow: ${JSON.stringify(layout)}`)
  if (errors.length) throw new Error(`browser errors: ${JSON.stringify(errors)}`)
  await page.screenshot({ path: path.join(outputDir, `sparsamp-${viewport.name}.png`), fullPage: true })
  await page.close()
}

await browser.close()
console.log(`visual checks passed: ${outputDir}`)
