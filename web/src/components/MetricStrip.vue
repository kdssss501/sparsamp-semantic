<script setup lang="ts">
import { computed } from 'vue'
import type { Metrics } from '../types'

const props = defineProps<{ metrics: Partial<Metrics> | null }>()

const items = computed(() => [
  { label: '嵌入容量', value: format(props.metrics?.bits_per_token, 3), unit: 'bit/token' },
  { label: '嵌入吞吐', value: format(props.metrics?.bits_per_second, 2), unit: 'bit/s' },
  { label: '熵利用率', value: percent(props.metrics?.entropy_utilization), unit: '' },
  {
    label: '可见 Token',
    value: integer(props.metrics?.token_count),
    unit: props.metrics?.tail_token_count ? `含 ${props.metrics.tail_token_count} 尾部` : '',
  },
  {
    label: '累计反向截断 KL',
    value: format(props.metrics?.truncation_kl_nats, 3),
    unit: 'nat',
  },
  {
    label: '累计量化正向 KL',
    value: format(props.metrics?.forward_quantization_kl_nats, 6),
    unit: 'nat',
  },
])

function format(value: number | undefined, digits: number) {
  return value === undefined ? '—' : value.toFixed(digits)
}

function integer(value: number | undefined) {
  return value === undefined ? '—' : Math.round(value).toLocaleString()
}

function percent(value: number | undefined) {
  return value === undefined ? '—' : `${(value * 100).toFixed(1)}%`
}
</script>

<template>
  <div class="metric-strip" aria-label="生成指标">
    <div v-for="item in items" :key="item.label" class="metric-cell">
      <span>{{ item.label }}</span>
      <strong>{{ item.value }}</strong>
      <small>{{ item.unit }}</small>
    </div>
  </div>
</template>
