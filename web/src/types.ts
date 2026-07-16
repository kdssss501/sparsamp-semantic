export type OperationKind = 'encode' | 'decode' | 'native'
export type OperationStatus = 'queued' | 'running' | 'succeeded' | 'failed'

export interface SamplingConfig {
  model: string
  revision: string | null
  device: 'auto' | 'cuda' | 'cpu'
  dtype: 'float16' | 'bfloat16' | 'float32'
  load_in_4bit: boolean
  top_p: number
  top_k: number | null
  temperature: number
  seed: number
}

export interface CodecSettings {
  block_size: number
  max_tokens: number
  min_source_mass: number
  probability_quantum: string
  repetitions: number
}

export interface Metrics {
  embedded_bits: number
  padded_bits: number
  token_count: number
  elapsed_seconds: number
  bits_per_token: number
  bits_per_second: number
  entropy_utilization: number
  truncation_kl_nats: number
}

export interface Operation {
  id: string
  kind: OperationKind
  status: OperationStatus
  progress: number
  stage: string
  created_at: string
  started_at: string | null
  finished_at: string | null
  result: Record<string, unknown> | null
  error: { code: string; message: string } | null
}

export interface SystemStatus {
  torch_version: string
  cuda_available: boolean
  gpu: { name: string; free_vram_bytes: number; total_vram_bytes: number } | null
  model: { path: string; available: boolean }
  operation_count: number
}

export interface GridRow {
  timestamp: number
  prompt_index: number
  prompt: string
  codec: { block_size: number }
  token_ambiguity: boolean
  metrics: Metrics
  source: string
  row_index: number
}

export interface ArtifactSummary {
  id: string
  prompt: string
  cover_preview: string
  created_at: number
  model: string
  block_size: number | null
  token_ambiguity: boolean | null
  metrics: Partial<Metrics>
}
