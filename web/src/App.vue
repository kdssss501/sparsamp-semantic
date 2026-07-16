<script setup lang="ts">
import {
  Activity,
  Cpu,
  FlaskConical,
  Menu,
  RadioTower,
  RefreshCw,
  ShieldCheck,
  Waves,
  X,
} from '@lucide/vue'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import OperationBar from './components/OperationBar.vue'
import { useWorkbenchStore } from './stores/workbench'
import DecodeView from './views/DecodeView.vue'
import EncodeView from './views/EncodeView.vue'
import ExperimentsView from './views/ExperimentsView.vue'

type ViewName = 'encode' | 'decode' | 'experiments'

const store = useWorkbenchStore()
const currentView = ref<ViewName>('encode')
const mobileNavOpen = ref(false)
const loadError = ref('')

const navItems = [
  { value: 'encode' as const, label: '生成工作台', icon: Waves },
  { value: 'decode' as const, label: '接收解码', icon: ShieldCheck },
  { value: 'experiments' as const, label: '实验分析', icon: FlaskConical },
]

const gpuUsage = computed(() => {
  const gpu = store.system?.gpu
  if (!gpu) return null
  return ((gpu.total_vram_bytes - gpu.free_vram_bytes) / gpu.total_vram_bytes) * 100
})

function selectView(view: ViewName) {
  currentView.value = view
  mobileNavOpen.value = false
}

async function initialize() {
  try {
    loadError.value = ''
    await store.initialize()
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '无法连接本地 API'
  }
}

async function refresh() {
  await initialize()
  if (!loadError.value) ElMessage.success('状态已刷新')
}

onMounted(initialize)
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar" :class="{ open: mobileNavOpen }">
      <div class="brand-block">
        <div class="brand-mark"><RadioTower :size="22" /></div>
        <div><strong>SparSamp</strong><span>RESEARCH LAB</span></div>
        <button class="mobile-close" aria-label="关闭导航" @click="mobileNavOpen = false"><X :size="20" /></button>
      </div>

      <nav aria-label="工作台导航">
        <button
          v-for="item in navItems"
          :key="item.value"
          :class="{ active: currentView === item.value }"
          @click="selectView(item.value)"
        >
          <component :is="item.icon" :size="19" />
          <span>{{ item.label }}</span>
        </button>
      </nav>

      <div class="sidebar-status">
        <span>RUNTIME</span>
        <div class="runtime-line">
          <Cpu :size="17" />
          <div><strong>{{ store.system?.gpu?.name ?? 'GPU 未连接' }}</strong><small>CUDA {{ store.system?.cuda_available ? 'READY' : 'OFFLINE' }}</small></div>
        </div>
        <el-progress v-if="gpuUsage !== null" :percentage="gpuUsage" :stroke-width="5" :show-text="false" />
        <div class="runtime-line">
          <Activity :size="17" />
          <div><strong>Qwen2.5-1.5B</strong><small>{{ store.system?.model.available ? 'MODEL READY' : 'MODEL MISSING' }}</small></div>
        </div>
      </div>
    </aside>

    <div v-if="mobileNavOpen" class="nav-scrim" @click="mobileNavOpen = false" />

    <div class="app-main">
      <header class="topbar">
        <button class="mobile-menu" aria-label="打开导航" @click="mobileNavOpen = true"><Menu :size="21" /></button>
        <div class="view-title">
          <span>LOCAL / AUTHORIZED RESEARCH</span>
          <strong>{{ navItems.find((item) => item.value === currentView)?.label }}</strong>
        </div>
        <div class="topbar-actions">
          <div class="health-pill" :class="{ healthy: store.system?.cuda_available && store.system?.model.available }">
            <i />{{ store.system?.cuda_available && store.system?.model.available ? '系统就绪' : '环境检查' }}
          </div>
          <el-tooltip content="刷新运行状态">
            <el-button circle @click="refresh"><RefreshCw :size="17" /></el-button>
          </el-tooltip>
        </div>
      </header>

      <OperationBar :operation="store.activeOperation" />

      <el-alert
        v-if="loadError"
        class="connection-alert"
        type="error"
        :title="loadError"
        :closable="false"
        show-icon
      />

      <main class="content-area">
        <EncodeView v-if="currentView === 'encode'" />
        <DecodeView v-else-if="currentView === 'decode'" />
        <ExperimentsView v-else />
      </main>
    </div>
  </div>
</template>
