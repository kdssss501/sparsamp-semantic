<script setup lang="ts">
import * as echarts from 'echarts'
import { BarChart3, RefreshCw } from '@lucide/vue'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useWorkbenchStore } from '../stores/workbench'

const store = useWorkbenchStore()
const chartElement = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

const rows = computed(() => store.gridRows)
const summary = computed(() => {
  if (!rows.value.length) return { best: null, success: 0, mean: 0 }
  const best = [...rows.value].sort((a, b) => b.metrics.bits_per_token - a.metrics.bits_per_token)[0]
  return {
    best,
    success: rows.value.filter((row) => !row.token_ambiguity).length / rows.value.length,
    mean: rows.value.reduce((sum, row) => sum + row.metrics.bits_per_token, 0) / rows.value.length,
  }
})

function renderChart() {
  if (!chartElement.value) return
  chart ??= echarts.init(chartElement.value)
  const ordered = [...rows.value].sort((a, b) => a.codec.block_size - b.codec.block_size)
  chart.setOption({
    animationDuration: 450,
    grid: { left: 54, right: 58, top: 34, bottom: 48 },
    tooltip: { trigger: 'axis' },
    legend: { top: 0, right: 0, textStyle: { color: '#616963' } },
    xAxis: {
      type: 'category',
      name: 'block size',
      data: ordered.map((row) => row.codec.block_size),
      axisLine: { lineStyle: { color: '#ccd2cd' } },
    },
    yAxis: [
      {
        type: 'value',
        name: 'bit/token',
        min: 0,
        axisLine: { show: true, lineStyle: { color: '#ccd2cd' } },
        splitLine: { lineStyle: { color: '#edf0ed' } },
      },
      { type: 'value', name: 'bit/s', splitLine: { show: false } },
    ],
    series: [
      {
        name: '容量',
        type: 'bar',
        data: ordered.map((row) => Number(row.metrics.bits_per_token.toFixed(3))),
        itemStyle: { color: '#087f6b', borderRadius: [3, 3, 0, 0] },
        barMaxWidth: 42,
      },
      {
        name: '吞吐',
        type: 'line',
        yAxisIndex: 1,
        data: ordered.map((row) => Number(row.metrics.bits_per_second.toFixed(2))),
        lineStyle: { color: '#cf6e27', width: 2 },
        itemStyle: { color: '#cf6e27' },
        symbolSize: 7,
      },
    ],
  })
}

function resize() {
  chart?.resize()
}

onMounted(async () => {
  await nextTick()
  renderChart()
  window.addEventListener('resize', resize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
})
watch(rows, () => nextTick(renderChart), { deep: true })
</script>

<template>
  <div class="experiments-view">
    <div class="page-heading">
      <div>
        <span>ANALYSIS</span>
        <h2>实验结果</h2>
      </div>
      <el-tooltip content="刷新实验记录">
        <el-button circle @click="store.initialize"><RefreshCw :size="17" /></el-button>
      </el-tooltip>
    </div>

    <div class="summary-band">
      <div>
        <span>最高容量</span>
        <strong>{{ summary.best?.metrics.bits_per_token.toFixed(3) ?? '—' }}</strong>
        <small>bit/token · block {{ summary.best?.codec.block_size ?? '—' }}</small>
      </div>
      <div>
        <span>平均容量</span>
        <strong>{{ summary.mean ? summary.mean.toFixed(3) : '—' }}</strong>
        <small>{{ rows.length }} 个实验点</small>
      </div>
      <div>
        <span>重分词成功</span>
        <strong>{{ rows.length ? `${(summary.success * 100).toFixed(0)}%` : '—' }}</strong>
        <small>Token Ambiguity</small>
      </div>
    </div>

    <section class="chart-panel">
      <div class="panel-title"><BarChart3 :size="18" /><strong>容量与吞吐</strong><span>Qwen2.5-1.5B · top-p 0.95</span></div>
      <div ref="chartElement" class="experiment-chart" />
    </section>

    <section class="table-panel">
      <el-table :data="rows" height="320" empty-text="暂无网格实验结果">
        <el-table-column prop="codec.block_size" label="Block" width="86" />
        <el-table-column label="bit/token" width="110">
          <template #default="scope">{{ scope.row.metrics.bits_per_token.toFixed(3) }}</template>
        </el-table-column>
        <el-table-column label="bit/s" width="100">
          <template #default="scope">{{ scope.row.metrics.bits_per_second.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="利用率" width="100">
          <template #default="scope">{{ (scope.row.metrics.entropy_utilization * 100).toFixed(1) }}%</template>
        </el-table-column>
        <el-table-column label="累计 KL" width="110">
          <template #default="scope">{{ scope.row.metrics.truncation_kl_nats.toFixed(3) }}</template>
        </el-table-column>
        <el-table-column label="歧义" width="84">
          <template #default="scope">
            <el-tag :type="scope.row.token_ambiguity ? 'danger' : 'success'" size="small" effect="plain">
              {{ scope.row.token_ambiguity ? '有' : '无' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source" label="来源" min-width="210" show-overflow-tooltip />
      </el-table>
    </section>
  </div>
</template>
