import type { ArtifactSummary, GridRow, Operation, SystemStatus } from './types'

interface Envelope<T> {
  data: T
}

interface PageEnvelope<T> {
  data: T[]
  page: { limit: number; next_cursor: string | null }
}

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public requestId?: string,
  ) {
    super(message)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  const body = await response.json()
  if (!response.ok) {
    throw new ApiError(
      body.error?.code ?? 'REQUEST_FAILED',
      body.error?.message ?? '请求失败',
      body.error?.request_id,
    )
  }
  return body as T
}

export const api = {
  async systemStatus(): Promise<SystemStatus> {
    return (await request<Envelope<SystemStatus>>('/api/v1/system/status')).data
  },
  async createOperation(payload: Record<string, unknown>): Promise<Operation> {
    return (
      await request<Envelope<Operation>>('/api/v1/operations', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
    ).data
  },
  async operation(id: string): Promise<Operation> {
    return (await request<Envelope<Operation>>(`/api/v1/operations/${id}`)).data
  },
  async operations(): Promise<Operation[]> {
    return (await request<Envelope<Operation[]>>('/api/v1/operations?limit=20')).data
  },
  async artifacts(): Promise<ArtifactSummary[]> {
    return (await request<PageEnvelope<ArtifactSummary>>('/api/v1/artifacts?limit=30')).data
  },
  async artifact(id: string): Promise<Record<string, unknown>> {
    return (await request<Envelope<Record<string, unknown>>>(`/api/v1/artifacts/${id}`)).data
  },
  async gridResults(): Promise<GridRow[]> {
    return (await request<PageEnvelope<GridRow>>('/api/v1/grid-results?limit=200')).data
  },
}
