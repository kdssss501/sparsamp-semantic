<script setup lang="ts">
import { FileInput, KeyRound, RotateCcw } from '@lucide/vue'
import { ElMessage } from 'element-plus'
import { computed, reactive, ref } from 'vue'
import { useWorkbenchStore } from '../stores/workbench'
import type { CodecSettings, SamplingConfig } from '../types'

const store = useWorkbenchStore()
const selectedArtifact = ref('')
const decodeSource = ref<'artifact' | 'text'>('text')
const message = ref('')
const resultSource = ref('')
const form = reactive({
  prompt: store.lastPrompt,
  coverText: store.lastCoverText,
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
})
const codec = reactive<CodecSettings>({
  block_size: 32,
  max_tokens: 2048,
  min_source_mass: 0,
  probability_quantum: '1e-15',
  repetitions: 1,
})
const canDecode = computed(
  () =>
    new TextEncoder().encode(form.secretKey).length >= 16 &&
    (decodeSource.value === 'artifact'
      ? Boolean(selectedArtifact.value)
      : Boolean(form.prompt.trim() && form.coverText.trim())),
)

function useLatest() {
  form.prompt = store.lastPrompt
  form.coverText = store.lastCoverText
  decodeSource.value = 'text'
}

async function loadArtifact() {
  if (!selectedArtifact.value) return
  try {
    const artifact = await store.loadArtifact(selectedArtifact.value)
    form.prompt = String(artifact.prompt ?? '')
    form.coverText = String(artifact.cover_text ?? '')
    const provider = artifact.provider as Record<string, unknown> | undefined
    const settings = artifact.codec as Record<string, unknown> | undefined
    const payload = artifact.payload as Record<string, unknown> | undefined
    if (provider) {
      sampling.model = String(provider.model_name ?? sampling.model)
      sampling.revision = (provider.revision as string | null) ?? null
      sampling.device = (provider.device as SamplingConfig['device']) ?? sampling.device
      sampling.dtype = (provider.dtype as SamplingConfig['dtype']) ?? sampling.dtype
      sampling.load_in_4bit = Boolean(provider.load_in_4bit)
      sampling.top_p = Number(provider.top_p ?? sampling.top_p)
      sampling.top_k = provider.top_k == null ? null : Number(provider.top_k)
      sampling.temperature = Number(provider.temperature ?? sampling.temperature)
      sampling.seed = Number(provider.seed ?? sampling.seed)
    }
    if (settings) {
      codec.block_size = Number(settings.block_size ?? codec.block_size)
      codec.max_tokens = Number(settings.max_tokens ?? codec.max_tokens)
      codec.min_source_mass = Number(settings.min_source_mass ?? codec.min_source_mass)
      codec.probability_quantum = String(settings.probability_quantum ?? codec.probability_quantum)
    }
    codec.repetitions = Number(payload?.repetitions ?? codec.repetitions)
    decodeSource.value = 'artifact'
    ElMessage.success('实验参数已载入')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取实验记录失败')
  }
}

async function decode() {
  message.value = ''
  resultSource.value = ''
  try {
    const payload =
      decodeSource.value === 'artifact'
        ? {
            kind: 'decode',
            artifact_id: selectedArtifact.value,
            secret_key: form.secretKey,
          }
        : {
            kind: 'decode',
            prompt: form.prompt,
            cover_text: form.coverText,
            secret_key: form.secretKey,
            sampling: { ...sampling },
            codec: { ...codec },
          }
    const operation = await store.submit(payload)
    if (operation.status !== 'succeeded' || !operation.result) return
    message.value = String(operation.result.message ?? '')
    resultSource.value = String(operation.result.source ?? '')
    ElMessage.success('载荷认证与恢复成功')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '解码失败')
  }
}
</script>

<template>
  <div class="decode-layout">
    <section class="decode-form">
      <div class="section-heading">
        <div>
          <span>RECEIVE</span>
          <h2>接收与解码</h2>
        </div>
        <el-tooltip content="填入最近一次生成内容">
          <el-button circle @click="useLatest"><RotateCcw :size="17" /></el-button>
        </el-tooltip>
      </div>

      <div class="artifact-picker">
        <el-select v-model="selectedArtifact" filterable clearable placeholder="选择本地实验记录">
          <el-option
            v-for="artifact in store.artifacts"
            :key="artifact.id"
            :label="`${artifact.id} · block ${artifact.block_size ?? '—'}`"
            :value="artifact.id"
          />
        </el-select>
        <el-button :disabled="!selectedArtifact" @click="loadArtifact"><FileInput :size="17" />载入</el-button>
      </div>

      <el-segmented
        v-model="decodeSource"
        class="decode-source"
        :options="[
          { label: '实验 artifact', value: 'artifact' },
          { label: '公开文本', value: 'text' },
        ]"
      />

      <el-form label-position="top">
        <el-form-item label="共享提示词">
          <el-input v-model="form.prompt" type="textarea" :rows="3" resize="vertical" />
        </el-form-item>
        <el-form-item label="Cover text">
          <el-input v-model="form.coverText" type="textarea" :rows="12" resize="vertical" />
        </el-form-item>
        <div class="form-row two">
          <el-form-item label="共享密钥">
            <el-input v-model="form.secretKey" type="password" show-password autocomplete="off" placeholder="至少 16 bytes" />
          </el-form-item>
          <el-form-item label="Block size">
            <el-select v-model="codec.block_size">
              <el-option v-for="value in [8, 16, 32, 64, 128]" :key="value" :value="value" :label="value" />
            </el-select>
          </el-form-item>
        </div>
        <el-collapse class="advanced-settings">
          <el-collapse-item title="解码参数" name="decode-settings">
            <div class="form-row three">
              <el-form-item label="Top-p">
                <el-input-number v-model="sampling.top_p" :min="0.1" :max="1" :step="0.05" :precision="2" controls-position="right" />
              </el-form-item>
              <el-form-item label="温度">
                <el-input-number v-model="sampling.temperature" :min="0.1" :max="2" :step="0.1" :precision="1" controls-position="right" />
              </el-form-item>
              <el-form-item label="纠错重复数">
                <el-select v-model="codec.repetitions">
                  <el-option v-for="value in [1, 3, 5]" :key="value" :value="value" :label="value" />
                </el-select>
              </el-form-item>
            </div>
          </el-collapse-item>
        </el-collapse>
      </el-form>
      <el-button
        type="primary"
        :disabled="!canDecode"
        :loading="store.busy"
        @click="decode"
      >
        <KeyRound :size="17" />认证并恢复
      </el-button>
    </section>

    <section class="decoded-output" :class="{ empty: !message }">
      <span>RECOVERED PAYLOAD</span>
      <div class="decoded-message">{{ message || '等待解码任务' }}</div>
      <div class="integrity-state" :class="{ verified: message }">
        <span class="integrity-dot" />
        {{ message ? `认证通过 · ${resultSource === 'artifact_token_ids' ? 'Token IDs' : 'Cover text'}` : '未认证' }}
      </div>
    </section>
  </div>
</template>
