import { defineStore } from 'pinia'
import { api } from '../api'
import type { ArtifactSummary, GridRow, Operation, SystemStatus } from '../types'

const terminalStates = new Set(['succeeded', 'failed'])

export const useWorkbenchStore = defineStore('workbench', {
  state: () => ({
    system: null as SystemStatus | null,
    activeOperation: null as Operation | null,
    operations: [] as Operation[],
    artifacts: [] as ArtifactSummary[],
    gridRows: [] as GridRow[],
    busy: false,
    lastCoverText: '',
    lastPrompt: '',
  }),
  actions: {
    async initialize() {
      const [system, operations, artifacts, gridRows] = await Promise.all([
        api.systemStatus(),
        api.operations(),
        api.artifacts(),
        api.gridResults(),
      ])
      this.system = system
      this.operations = operations
      this.artifacts = artifacts
      this.gridRows = gridRows
    },
    async submit(payload: Record<string, unknown>) {
      this.busy = true
      try {
        this.activeOperation = await api.createOperation(payload)
        await this.poll(this.activeOperation.id)
        await this.refreshData()
        return this.activeOperation
      } finally {
        this.busy = false
      }
    },
    async poll(id: string) {
      while (true) {
        const operation = await api.operation(id)
        this.activeOperation = operation
        if (terminalStates.has(operation.status)) return
        await new Promise((resolve) => window.setTimeout(resolve, 700))
      }
    },
    async refreshData() {
      const [system, operations, artifacts] = await Promise.all([
        api.systemStatus(),
        api.operations(),
        api.artifacts(),
      ])
      this.system = system
      this.operations = operations
      this.artifacts = artifacts
    },
    async loadArtifact(id: string) {
      return api.artifact(id)
    },
  },
})
