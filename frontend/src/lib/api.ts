export interface Quote {
  phrase: string
  author: string
}

export interface QuotesResponse {
  source: string
  count: number
  updated_at: string | null
  quotes: Quote[]
}

export interface RefreshResponse {
  source: string
  count: number
  added: number
  updated_at: string | null
}

export interface RetrievedQuote extends Quote {
  score: number
  translation?: string | null
}

export interface DebateResponse {
  answer: string
  has_sources: boolean
  quotes: RetrievedQuote[]
}

export interface Spec {
  name: string
  tokenizer: string
  max_tokens_per_request: number
  max_chars_per_request: number | null
  reserve_output: number
  price_per_input_token: number
  price_per_output_token: number
  currency: string
  requests_per_minute: number
  system_prompt_tokens: number
  json_format_overhead: number
  output_ratio: number
  output_base: number
}

export interface BatchReport {
  batch_id: number
  phrase_count: number
  input_tokens: number
  output_tokens: number
  overhead_tokens: number
  total_tokens: number
  utilization: number
  cost: number
}

export interface Receipt {
  spec: Spec
  total_requests: number
  total_input_tokens: number
  total_output_tokens: number
  total_tokens: number
  total_cost: number
  currency: string
  batches: BatchReport[]
}

export interface PhraseReport {
  index: number
  phrase: string
  author: string
  input_tokens: number
  output_tokens: number
  translation: string
  context: string
}

export interface OptimizerResponse {
  receipt: Receipt
  items: PhraseReport[]
}

export interface SpecsResponse {
  default_spec: Spec
  providers: string[]
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const detail =
      body && body.detail ? (typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)) : `Error ${res.status}`
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  quotes: () => request<QuotesResponse>('/api/quotes'),
  refresh: () =>
    request<RefreshResponse>('/api/quotes/refresh', { method: 'POST' }),
  debate: (question: string, language: string, threshold?: number) =>
    request<DebateResponse>('/api/debate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, language, threshold }),
    }),
  specs: () => request<SpecsResponse>('/api/optimizer/specs'),
  preview: (spec: Partial<Spec>, provider: string, limit_phrases?: number) =>
    request<OptimizerResponse>('/api/optimizer/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ spec, provider, limit_phrases }),
    }),
  run: (spec: Partial<Spec>, provider: string, limit_phrases?: number) =>
    request<OptimizerResponse>('/api/optimizer/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ spec, provider, limit_phrases }),
    }),
}
