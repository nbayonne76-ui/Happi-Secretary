const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    cache: 'no-store',
  })
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`)
  return res.json()
}

export const api = {
  // Clients
  getClients: () => req<Client[]>('/api/clients/'),
  getClient: (id: string) => req<Client>(`/api/clients/${id}`),
  createClient: (data: Partial<Client>) => req<Client>('/api/clients/', { method: 'POST', body: JSON.stringify(data) }),
  updateClient: (id: string, data: Partial<Client>) => req<Client>(`/api/clients/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  // Calls
  getCalls: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : ''
    return req<CallLog[]>(`/api/calls/${qs}`)
  },
  getCall: (id: string) => req<CallLog>(`/api/calls/${id}`),

  // Knowledge
  getKnowledge: (clientId: string) => req<KnowledgeEntry[]>(`/api/knowledge/${clientId}`),
  addFaq: (clientId: string, question: string, answer: string) =>
    req('/api/knowledge/faq', { method: 'POST', body: JSON.stringify({ client_id: clientId, question, answer }) }),
  addManual: (clientId: string, title: string, content: string) =>
    req('/api/knowledge/manual', { method: 'POST', body: JSON.stringify({ client_id: clientId, title, content }) }),
  ingestUrl: (clientId: string, url: string) =>
    req('/api/knowledge/url', { method: 'POST', body: JSON.stringify({ client_id: clientId, url }) }),
  deleteKnowledge: (id: string) => req(`/api/knowledge/${id}`, { method: 'DELETE' }),

  // Analytics
  getStats: (clientId?: string, days = 30) => {
    const qs = new URLSearchParams({ days: String(days), ...(clientId ? { client_id: clientId } : {}) })
    return req<Stats>(`/api/analytics/stats?${qs}`)
  },
  getCallsByDay: (clientId?: string, days = 30) => {
    const qs = new URLSearchParams({ days: String(days), ...(clientId ? { client_id: clientId } : {}) })
    return req<{ day: string; count: number }[]>(`/api/analytics/calls-by-day?${qs}`)
  },
  getIntents: (clientId?: string, days = 30) => {
    const qs = new URLSearchParams({ days: String(days), ...(clientId ? { client_id: clientId } : {}) })
    return req<{ intent: string; count: number }[]>(`/api/analytics/intents?${qs}`)
  },
}

// ---- Types ----
export interface Client {
  id: string
  name: string
  business_type: string
  phone_number: string | null
  vapi_assistant_id: string | null
  assistant_name: string
  voice_id: string
  language: string
  greeting_message: string
  after_hours_message: string
  off_hours_behavior: string
  system_prompt: string | null
  business_hours: Record<string, { open: string; close: string; enabled: boolean }>
  transfer_numbers: Record<string, string>
  escalation_keywords: string[]
  vip_numbers: string[]
  calendar_enabled: boolean
  calcom_event_type_id: number | null
  notification_email: string | null
  notification_sms: string | null
  send_transcript_email: boolean
  send_transcript_sms: boolean
  crm_webhook_url: string | null
  features: Record<string, boolean>
  is_active: boolean
  created_at: string
}

export interface CallLog {
  id: string
  client_id: string
  vapi_call_id: string
  caller_number: string | null
  caller_name: string | null
  is_vip: boolean
  started_at: string | null
  ended_at: string | null
  duration_seconds: number
  status: string
  intent: string | null
  sentiment: string | null
  sentiment_score: number | null
  summary: string | null
  outcome: string | null
  appointment_booked: boolean
  appointment_id: string | null
  transferred_to: string | null
  transcript: string | null
  messages?: any[]
  recording_url: string | null
  created_at: string
}

export interface KnowledgeEntry {
  id: string
  client_id: string
  title: string
  content: string
  source_type: string
  source_url: string | null
  is_active: boolean
  created_at: string
}

export interface Stats {
  period_days: number
  total_calls: number
  avg_duration_seconds: number
  resolution_rate: number
  appointments_booked: number
  calls_transferred: number
  messages_taken: number
  missed_calls: number
  sentiment: { positive: number; negative: number; urgent: number; neutral: number }
}
