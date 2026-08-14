import { lazy, Suspense, useEffect, useState } from 'react'
import { api, type OptimizerResponse, type Spec } from '../lib/api'
import { QuotesSource } from '../components/QuotesSource'
import { fmtMoney, fmtTokenPrice, perMillion } from '../lib/format'

const BatchViz = lazy(() => import('../three/BatchViz'))

const DEFAULT_SPEC: Spec = {
  name: 'MiniTranslate',
  tokenizer: 'o200k_base',
  max_tokens_per_request: 2000,
  max_chars_per_request: null,
  reserve_output: 0.35,
  price_per_input_token: 0.00000015,
  price_per_output_token: 0.0000006,
  currency: 'USD',
  requests_per_minute: 60,
  system_prompt_tokens: 80,
  json_format_overhead: 25,
  output_ratio: 2.0,
  output_base: 40,
}

export function OptimizerSection() {
  const [providers, setProviders] = useState<string[]>(['ctranslate2'])
  const [spec, setSpec] = useState<Spec>(DEFAULT_SPEC)
  const [provider, setProvider] = useState('ctranslate2')
  const [count, setCount] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<OptimizerResponse | null>(null)

  useEffect(() => {
    api.specs().then((s) => {
      setSpec(s.default_spec)
      setProviders(s.providers)
    }).catch(() => undefined)
    api.quotes().then((q) => setCount(q.count)).catch(() => undefined)
  }, [])

  const setNum = (key: keyof Spec, value: string) => {
    setSpec((prev) => ({ ...prev, [key]: Number(value) }))
  }

  const run = async (preview: boolean) => {
    setLoading(true)
    setError(null)
    setData(null)
    try {
      const res = preview
        ? await api.preview(spec, provider)
        : await api.run(spec, provider)
      setData(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error desconocido')
    } finally {
      setLoading(false)
    }
  }

  const fmt = (n: number) => n.toLocaleString('en-US')

  return (
    <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
      <section className="panel" aria-labelledby="opt-config-title">
        <QuotesSource onCountChange={setCount} />
        <p className="kicker mt-4">Empaquetado y presupuesto</p>
        <h2 id="opt-config-title" className="mt-1 font-display text-2xl font-extrabold">
          包 — Proveedor y límites
        </h2>
        <div className="mt-4 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="max-tokens" className="label">
                Máx. tokens por petición (X)
              </label>
              <input
                id="max-tokens"
                type="number"
                min={1}
                className="input"
                value={spec.max_tokens_per_request}
                onChange={(e) => setNum('max_tokens_per_request', e.target.value)}
              />
            </div>
            <div>
              <span className="label">Frases a procesar</span>
              <div className="flex h-[38px] items-center border-2 border-ink bg-washi px-3 text-sm font-semibold">
                {count ?? '…'} <span className="ml-1 font-normal text-ink-soft">citas (se leen de la web)</span>
              </div>
            </div>
          </div>
          <div>
            <label htmlFor="provider" className="label">
              Provider
            </label>
            <select
              id="provider"
              className="input"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
            >
              {providers.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
            <p className="mt-1 text-[11px] text-ink-soft">
              ctranslate2 = local y gratis (NLLB/OPUS-MT) · deep_translator = web gratis · mock = demo
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="p-in" className="label">
                $ por token enviado
              </label>
              <input
                id="p-in"
                type="text"
                inputMode="decimal"
                className="input"
                value={fmtTokenPrice(spec.price_per_input_token)}
                onChange={(e) => setNum('price_per_input_token', e.target.value || '0')}
              />
              <p className="mt-1 text-[11px] text-ink-soft">{perMillion(spec.price_per_input_token)}</p>
            </div>
            <div>
              <label htmlFor="p-out" className="label">
                $ por token recibido
              </label>
              <input
                id="p-out"
                type="text"
                inputMode="decimal"
                className="input"
                value={fmtTokenPrice(spec.price_per_output_token)}
                onChange={(e) => setNum('price_per_output_token', e.target.value || '0')}
              />
              <p className="mt-1 text-[11px] text-ink-soft">{perMillion(spec.price_per_output_token)}</p>
            </div>
          </div>
          <div className="flex gap-3">
            <button className="btn-secondary flex-1" onClick={() => run(true)} disabled={loading}>
              Vista previa
            </button>
            <button className="btn-primary flex-1" onClick={() => run(false)} disabled={loading}>
              {loading ? 'Procesando…' : 'Ejecutar'}
            </button>
          </div>
          {error && <p className="border-2 border-crimson bg-paper p-3 text-sm text-crimson-dark">{error}</p>}
        </div>
      </section>

      <section className="panel min-h-72" aria-labelledby="opt-result-title" aria-live="polite">
        <p className="kicker">Recibo y métricas</p>
        <h2 id="opt-result-title" className="mt-1 font-display text-2xl font-extrabold">
          受 — Resultado
        </h2>
        <div className="mt-4">
          {loading && <p role="status" className="text-sm text-ink-soft">Empaquetando lotes…</p>}
          {!loading && !data && !error && (
            <p className="text-sm text-ink-soft">Configura el proveedor y ejecuta la simulación.</p>
          )}
          {!loading && data && (
            <div className="space-y-5">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Summary label="Peticiones" value={fmt(data.receipt.total_requests)} />
                <Summary label="Tokens enviados" value={fmt(data.receipt.total_input_tokens)} />
                <Summary label="Tokens recibidos" value={fmt(data.receipt.total_output_tokens)} />
                <Summary label="Costo total" value={fmtMoney(data.receipt.total_cost, spec.currency)} />
              </div>

              <div>
                <h3 className="label">Empaquetado 3D — métricas por lote</h3>
                <Suspense fallback={<div className="h-80 w-full animate-pulse border-2 border-ink bg-washi/60" />}>
                  <BatchViz batches={data.receipt.batches} maxTokens={data.receipt.spec.max_tokens_per_request} />
                </Suspense>
              </div>

              <div className="overflow-x-auto border-2 border-ink">
                <table className="w-full text-left text-sm">
                  <thead className="bg-ink text-paper">
                    <tr>
                      <th className="px-3 py-2 font-display">Lote</th>
                      <th className="px-3 py-2 font-display">Frases</th>
                      <th className="px-3 py-2 font-display">Tokens in</th>
                      <th className="px-3 py-2 font-display">Tokens out</th>
                      <th className="px-3 py-2 font-display">Total</th>
                      <th className="px-3 py-2 font-display">Utilización</th>
                      <th className="px-3 py-2 font-display">Costo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.receipt.batches.map((b) => (
                      <tr key={b.batch_id} className="border-t border-ink/30 bg-paper">
                        <td className="px-3 py-2 font-semibold">#{b.batch_id}</td>
                        <td className="px-3 py-2">{b.phrase_count}</td>
                        <td className="px-3 py-2 tabular-nums">{fmt(b.input_tokens)}</td>
                        <td className="px-3 py-2 tabular-nums">{fmt(b.output_tokens)}</td>
                        <td className="px-3 py-2 tabular-nums">{fmt(b.total_tokens)}</td>
                        <td className="px-3 py-2">{(b.utilization * 100).toFixed(1)}%</td>
                        <td className="px-3 py-2 tabular-nums">{fmtMoney(b.cost, spec.currency)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {data.items.length > 0 && (
                <div>
                  <h3 className="label">Detalle por frase (tokens antes → después)</h3>
                  <div className="max-h-[28rem] overflow-auto border-2 border-ink">
                    <table className="w-full text-left text-sm">
                      <thead className="sticky top-0 bg-ink text-paper">
                        <tr>
                          <th className="px-3 py-2 font-display">Frase original</th>
                          <th className="px-3 py-2 font-display">Autor</th>
                          <th className="px-3 py-2 font-display">Traducción (ja)</th>
                          <th className="px-3 py-2 font-display">Contexto histórico</th>
                          <th className="px-3 py-2 font-display text-right">In → Out</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.items.map((item) => (
                          <tr key={item.index} className="border-t border-ink/30 bg-paper align-top">
                            <td className="max-w-xs px-3 py-2 font-display italic">“{item.phrase}”</td>
                            <td className="whitespace-nowrap px-3 py-2">{item.author}</td>
                            <td className="max-w-xs px-3 py-2">{item.translation}</td>
                            <td className="max-w-sm px-3 py-2 text-ink-soft">{item.context}</td>
                            <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
                              {fmt(item.input_tokens)} → {fmt(item.output_tokens)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </section>
    </div>
  )
}

function Summary({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-2 border-ink bg-paper p-3 shadow-[2px_2px_0_rgba(28,26,23,0.9)]">
      <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-ink-soft">{label}</p>
      <p className="mt-1 font-display text-xl font-extrabold">{value}</p>
    </div>
  )
}
