import { useEffect, useState } from 'react'
import { api, type QuotesResponse, type RefreshResponse } from '../lib/api'

interface Props {
  onCountChange?: (count: number) => void
}

function fmtUpdated(iso: string | null): string {
  if (!iso) return 'desconocido'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString()
}

/** Fuente de citas + botón "Actualizar" (re-scrapea la web). */
export function QuotesSource({ onCountChange }: Props) {
  const [meta, setMeta] = useState<QuotesResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<RefreshResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.quotes().then(setMeta).catch(() => undefined)
  }, [])

  const refresh = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await api.refresh()
      setResult(res)
      setMeta((prev) =>
        prev
          ? { ...prev, count: res.count, updated_at: res.updated_at }
          : prev,
      )
      onCountChange?.(res.count)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo actualizar')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      <span className="tag">
        源 {meta ? meta.count : '…'} citas · {meta?.source.replace('https://', '')}
      </span>
      <span className="tag">
        act. {fmtUpdated(meta?.updated_at ?? null)}
      </span>
      <button
        className="btn-secondary !px-3 !py-1 !text-xs"
        onClick={refresh}
        disabled={loading}
        aria-live="polite"
      >
        {loading ? 'Actualizando…' : '⤓ Actualizar citas'}
      </button>
      {result && !error && (
        <span className="text-xs font-semibold text-crimson-dark">
          {result.added > 0
            ? `+${result.added} nuevas frases`
            : 'Sin cambios en la web'}
        </span>
      )}
      {error && <span className="text-xs font-semibold text-crimson-dark">{error}</span>}
    </div>
  )
}
