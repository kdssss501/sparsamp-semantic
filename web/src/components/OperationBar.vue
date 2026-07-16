<script setup lang="ts">
import { CircleCheck, CircleX, Cpu, LoaderCircle } from '@lucide/vue'
import { computed } from 'vue'
import type { Operation } from '../types'

const props = defineProps<{ operation: Operation | null }>()
const active = computed(() => ['queued', 'running'].includes(props.operation?.status ?? ''))
</script>

<template>
  <div v-if="operation" class="operation-bar" :class="`is-${operation.status}`">
    <component
      :is="operation.status === 'succeeded' ? CircleCheck : operation.status === 'failed' ? CircleX : active ? LoaderCircle : Cpu"
      :class="{ spinning: active }"
      :size="18"
    />
    <div class="operation-copy">
      <div>
        <strong>{{ operation.stage }}</strong>
        <span>{{ operation.kind }} · {{ operation.id.slice(0, 8) }}</span>
      </div>
      <el-progress
        :percentage="operation.progress"
        :stroke-width="5"
        :show-text="false"
        :status="operation.status === 'failed' ? 'exception' : operation.status === 'succeeded' ? 'success' : undefined"
      />
      <p v-if="operation.error">{{ operation.error.message }}</p>
    </div>
    <b>{{ operation.progress }}%</b>
  </div>
</template>
