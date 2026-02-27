import client from './client'
import type { LastUpdated, UpdateProgress } from '../types/chart'

export async function startDbUpdate(): Promise<{ status: string }> {
  const response = await client.post<{ status: string }>('/db/update')
  return response.data
}

export async function fetchLastUpdated(): Promise<LastUpdated> {
  const response = await client.get<LastUpdated>('/db/last-updated')
  return response.data
}

// Subscribe to SSE DB update progress stream.
// Returns an unsubscribe function; call it to close the EventSource.
export function subscribeDbStatus(
  onProgress: (progress: UpdateProgress) => void,
  onError?: (error: Event) => void
): () => void {
  const source = new EventSource('/api/db/status')

  source.onmessage = (event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data as string) as UpdateProgress
      onProgress(data)
    } catch {
      // Ignore malformed SSE frames
    }
  }

  if (onError) {
    source.onerror = onError
  }

  return () => source.close()
}
