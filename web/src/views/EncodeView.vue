<script setup lang="ts">
import { Check, Clipboard, Download, Play, Sparkles } from '@lucide/vue'
import { ElMessage } from 'element-plus'
import { computed, reactive, ref } from 'vue'
import { useWorkbenchStore } from '../stores/workbench'
import type { CodecSettings, Metrics, SamplingConfig } from '../types'
import MetricStrip from '../components/MetricStrip.vue'

const store = useWorkbenchStore()
const form = reactive({
  prompt: '请用自然、清晰的中文解释为什么可复现实验对于人工智能安全研究很重要。',
  message: '实验编号 A-17',
  secretKey: '',
})
const sampling = reactive<SamplingConfig>({
  model: 'models/qwen2.5-1.5b-instruct',
  revision: null,
  device: 'cuda',
  dtype: 'float16',
  load_in_4bit: false,
  top_p: 0.95,
  top_k: null,
  temperature: 0.8,
  seed: 42,
  adaptive_temperature: false,
  entropy_floor_bits: 0.75,
  rescue_temperature: 1.1,
  rescue_patience: 8,
})
const codec = reactive<CodecSettings>({
  block_size: 32,
  max_tokens: 2048,
  min_source_mass: 0,
  probability_quantum: '1e-15',
  repetitions: 1,
  finish_mode: 'punctuation',
  finish_max_tokens: 32,
  finish_min_tokens: 4,
})
const coverText = ref('')
const baselineText = ref('')
const metrics = ref<Partial<Metrics> | null>(null)
const tokenAmbiguity = ref<boolean | null>(null)
const activeOutput = ref<'stego' | 'baseline'>('stego')

const canEncode = computed(
  () => form.prompt.trim() && form.message.trim() && new TextEncoder().encode(form.secretKey).length >= 16,
)

async function encode() {
  try {
    const operation = await store.submit({
      kind: 'encode',
      prompt: form.prompt,
      message: form.message,
      secret_key: form.secretKey,
      sampling: { ...sampling },
      codec: { ...codec },
    })
    if (operation.status !== 'succeeded' || !operation.result) return
    coverText.value = String(operation.result.cover_text ?? '')
    metrics.value = operation.result.metrics as Partial<Metrics>
    tokenAmbiguity.value = Boolean(operation.result.token_ambiguity)
    store.lastCoverText = coverText.value
    store.lastPrompt = form.prompt
    activeOutput.value = 'stego'
    ElMessage.success('隐写文本已生成并保存实验记录')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '编码失败')
  }
}

async function generateBaseline() {
  try {
    const operation = await store.submit({
      kind: 'native',
      prompt: form.prompt,
      tokens: metrics.value?.token_count ?? 256,
      sampling: { ...sampling },
    })
    if (operation.status !== 'succeeded' || !operation.result) return
    baselineText.value = String(operation.result.text ?? '')
    activeOutput.value = 'baseline'
    ElMessage.success('原生基线已生成')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '基线生成失败')
  }
}

async function copyCover() {
  if (!coverText.value) return
  await navigator.clipboard.writeText(coverText.value)
  ElMessage.success('已复制 cover text')
}

function downloadCover() {
  if (!coverText.value) return
  const link = document.createElement('a')
  link.href = URL.createObjectURL(new Blob([coverText.value], { type: 'text/plain;charset=utf-8' }))
  link.download = 'sparsamp-cover.txt'
  link.click()
  URL.revokeObjectURL(link.href)
}
</script>

<template>
  <div class="workspace-grid">
    <section class="control-panel">
      <div class="section-heading">
        <div>
          <span>COMPOSE</span>
          <h2>隐写生成</h2>
        </div>
        <el-tag v-if="tokenAmbiguity !== null" :type="tokenAmbiguity ? 'danger' : 'success'" effect="plain">
          <Check v-if="!tokenAmbiguity" :size="14" />
          {{ tokenAmbiguity ? '分词歧义' : '可重分词' }}
        </el-tag>
      </div>

      <el-form label-position="top">
        <el-form-item label="公开提示词">
          <el-input v-model="form.prompt" type="textarea" :rows="4" resize="vertical" maxlength="8000" show-word-limit />
        </el-form-item>
        <el-form-item label="秘密消息">
          <el-input v-model="form.message" type="textarea" :rows="3" resize="vertical" maxlength="4096" show-word-limit />
        </el-form-item>
        <el-form-item label="共享密钥">
          <el-input v-model="form.secretKey" type="password" show-password autocomplete="off" placeholder="至少 16 bytes" />
        </el-form-item>

        <div class="form-row three">
          <el-form-item label="Block size">
            <el-select v-model="codec.block_size">
              <el-option v-for="value in [8, 16, 32, 64, 128]" :key="value" :value="value" :label="value" />
            </el-select>
          </el-form-item>
          <el-form-item label="Top-p">
            <el-input-number v-model="sampling.top_p" :min="0.1" :max="1" :step="0.05" :precision="2" controls-position="right" />
          </el-form-item>
          <el-form-item label="温度">
            <el-input-number v-model="sampling.temperature" :min="0.1" :max="2" :step="0.1" :precision="1" controls-position="right" />
          </el-form-item>
        </div>

        <el-collapse class="advanced-settings">
          <el-collapse-item title="高级实验参数" name="advanced">
            <div class="form-row two">
              <el-form-item label="最大 tokens">
                <el-input-number v-model="codec.max_tokens" :min="64" :max="8192" :step="64" controls-position="right" />
              </el-form-item>
              <el-form-item label="随机种子">
                <el-input-number v-model="sampling.seed" :min="0" controls-position="right" />
              </el-form-item>
              <el-form-item label="纠错重复数">
                <el-select v-model="codec.repetitions">
                  <el-option v-for="value in [1, 3, 5]" :key="value" :value="value" :label="value" />
                </el-select>
              </el-form-item>
              <el-form-item label="数据类型">
                <el-select v-model="sampling.dtype">
                  <el-option value="float16" label="FP16" />
                  <el-option value="bfloat16" label="BF16" />
                  <el-option value="float32" label="FP32" />
                </el-select>
              </el-form-item>
              <el-form-item label="语义收尾">
                <el-select v-model="codec.finish_mode">
                  <el-option value="none" label="立即停止" />
                  <el-option value="punctuation" label="生成到句末" />
                  <el-option value="fixed" label="固定尾部" />
                </el-select>
              </el-form-item>
              <el-form-item label="收尾 Token 上限">
                <el-input-number
                  v-model="codec.finish_max_tokens"
                  :min="0"
                  :max="256"
                  :step="8"
                  :disabled="codec.finish_mode === 'none'"
                  controls-position="right"
                />
              </el-form-item>
              <el-form-item label="低熵救援">
                <el-switch v-model="sampling.adaptive_temperature" />
              </el-form-item>
              <el-form-item label="救援温度">
                <el-input-number
                  v-model="sampling.rescue_temperature"
                  :min="sampling.temperature"
                  :max="2"
                  :step="0.1"
                  :precision="1"
                  :disabled="!sampling.adaptive_temperature"
                  controls-position="right"
                />
              </el-form-item>
            </div>
          </el-collapse-item>
        </el-collapse>
      </el-form>

      <div class="action-row">
        <el-button type="primary" :disabled="!canEncode" :loading="store.busy" @click="encode">
          <Play :size="17" />生成隐写文本
        </el-button>
        <el-button :disabled="!form.prompt.trim()" :loading="store.busy" @click="generateBaseline">
          <Sparkles :size="17" />原生基线
        </el-button>
      </div>
    </section>

    <section class="result-panel">
      <div class="result-toolbar">
        <el-segmented v-model="activeOutput" :options="[{ label: '隐写文本', value: 'stego' }, { label: '原生基线', value: 'baseline' }]" />
        <div class="icon-actions">
          <el-tooltip content="复制隐写文本">
            <el-button circle :disabled="!coverText" @click="copyCover"><Clipboard :size="17" /></el-button>
          </el-tooltip>
          <el-tooltip content="下载为文本">
            <el-button circle :disabled="!coverText" @click="downloadCover"><Download :size="17" /></el-button>
          </el-tooltip>
        </div>
      </div>
      <div class="text-output" :class="{ empty: !(activeOutput === 'stego' ? coverText : baselineText) }">
        {{ activeOutput === 'stego' ? coverText || '等待隐写生成任务' : baselineText || '等待原生基线任务' }}
      </div>
      <MetricStrip :metrics="metrics" />
    </section>
  </div>
</template>
