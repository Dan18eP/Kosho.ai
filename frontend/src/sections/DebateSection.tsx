import { useState } from 'react'
import { api, type DebateResponse } from '../lib/api'
import { QuotesSource } from '../components/QuotesSource'

export function DebateSection() {
  const [question, setQuestion] = useState('Is imagination more important than knowledge?')
  const [language, setLanguage] = useState('en')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<DebateResponse | null>(null)

  const debate = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      setResult(await api.debate(question, language))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error desconocido')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
      <section className="panel" aria-labelledby="debate-input-title">
        <QuotesSource />
        <p className="kicker mt-4">Debate respaldado</p>
        <h2 id="debate-input-title" className="mt-1 font-display text-2xl font-extrabold">
          問 — Haz tu pregunta
        </h2>
        <div className="mt-4 space-y-4">
          <div>
            <label htmlFor="question" className="label">
              Pregunta filosófica
            </label>
            <textarea
              id="question"
              className="input min-h-28 resize-y"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ej: ¿Es más importante el conocimiento o la imaginación?"
            />
          </div>
          <div>
            <label htmlFor="lang" className="label">
              Idioma del ensayo
            </label>
            <select
              id="lang"
              className="input"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              <option value="en">English</option>
              <option value="es">Español</option>
            </select>
          </div>
          <button
            className="btn-primary w-full"
            onClick={debate}
            disabled={loading || question.trim().length < 2}
          >
            {loading ? 'Buscando evidencia…' : 'Debatir'}
          </button>
          <p className="text-xs text-ink-soft">
            El ensayo usa y cita frases de la base de datos (modelo local, sin claves); en
            español se traduce al idioma elegido. Sin dos voces distintas, lo admite.
          </p>
        </div>
      </section>

      <section className="panel min-h-72" aria-labelledby="debate-result-title" aria-live="polite">
        <p className="kicker">Respuesta</p>
        <h2 id="debate-result-title" className="mt-1 font-display text-2xl font-extrabold">
          答 — El veredicto
        </h2>
        <div className="mt-4">
          {error && <p className="border-2 border-crimson bg-paper p-3 text-sm text-crimson-dark">{error}</p>}
          {loading && (
            <p className="text-sm text-ink-soft" role="status">
              Buscando frases relevantes y redactando el ensayo… (≈10–20 s)
            </p>
          )}
          {!loading && !error && !result && (
            <p className="text-sm text-ink-soft">Formula una pregunta para iniciar el debate.</p>
          )}
          {!loading && result && !result.has_sources && (
            <div className="border-2 border-crimson bg-paper p-4 text-sm shadow-[3px_3px_0_rgba(28,26,23,0.9)]">
              <span className="font-display font-bold text-crimson-dark">Sin fuentes: </span>
              {result.answer}
            </div>
          )}
          {!loading && result && result.has_sources && (
            <div className="space-y-4">
              <p className="whitespace-pre-line text-[15px] leading-relaxed">{result.answer}</p>
              <div className="border-t-2 border-ink/20 pt-3">
                <h3 className="label">Citas utilizadas</h3>
                <ul className="space-y-2">
                  {result.quotes.map((q, i) => (
                    <li key={i} className="border-l-4 border-crimson bg-paper p-3 text-sm">
                      <p className="font-display italic">“{q.phrase}”</p>
                      {q.translation && (
                        <p className="mt-1 text-[13px] text-ink-soft">
                          Traducción: {q.translation}
                        </p>
                      )}
                      <p className="mt-1 text-xs text-ink-soft">
                        — {q.author} · relevancia {q.score}
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
