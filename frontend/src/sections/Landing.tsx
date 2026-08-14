import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Samurai } from '../components/Samurai'
import { api, type QuotesResponse } from '../lib/api'

export function Landing() {
  const [meta, setMeta] = useState<QuotesResponse | null>(null)

  useEffect(() => {
    api.quotes().then(setMeta).catch(() => undefined)
  }, [])

  return (
    <div className="relative">
      {/* HERO */}
      <section className="grid min-h-[72vh] items-center gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="relative z-10">
          <p className="kicker">虎書 — citas · debate · presupuesto</p>
          <h1 className="mt-3 font-display text-5xl font-extrabold leading-[1.05] tracking-tight sm:text-6xl">
            El espíritu del debate,
            <br />
            <span className="text-crimson">respaldado por citas reales.</span>
          </h1>
          <p className="mt-5 max-w-xl text-base leading-relaxed text-ink-soft">
            Kosho.ai desafía tus preguntas filosóficas con un mini-ensayo de dos párrafos
            que cita <strong className="text-ink">textualmente</strong> frases de
            {meta ? ` ${meta.count} autores scrapeados de ${meta.source.replace('https://', '')}` : ' los autores scrapeados'}
            . Y como un buen maestro, mide cada palabra: agrupa las citas en lotes óptimos
            para traducirlas al japonés y arroja un recibo de tokens por lote y por frase.
          </p>
          <div className="mt-7 flex flex-wrap gap-4">
            <Link to="/orador" className="btn-primary">
              Entrar a Kosho.ai →
            </Link>
            <Link to="/optimizador" className="btn-secondary">
              包 Ver el optimizador
            </Link>
          </div>
          <ul className="mt-8 flex flex-wrap gap-2 text-xs">
            <li className="tag">⚔ debate con fuentes</li>
            <li className="tag">日本語 traducción local (CTranslate2)</li>
            <li className="tag">☀ tres.js · manga</li>
          </ul>
        </div>

        {/* Samurai sobre el sol */}
        <div className="relative z-10 mx-auto h-[46vh] min-h-[300px] max-h-[460px] w-auto text-ink">
          <div
            className="absolute left-1/2 top-1/2 h-[70%] aspect-square -translate-x-1/2 -translate-y-1/2 rounded-full"
            style={{
              background:
                'radial-gradient(circle, rgba(230,53,44,0.85) 0%, rgba(230,53,44,0.35) 55%, transparent 72%)',
            }}
            aria-hidden="true"
          />
          <div className="absolute inset-0 flex items-end justify-center pb-2 drop-shadow-[0_6px_10px_rgba(28,26,23,0.45)]">
            <Samurai />
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section className="mt-16 grid gap-6 md:grid-cols-2" aria-label="Funcionalidades">
        <Link to="/orador" className="group panel transition hover:-translate-y-1">
          <p className="kicker">Ejercicio 01 · 問/答</p>
          <h2 className="mt-1 font-display text-2xl font-extrabold">Orador de Debates</h2>
          <p className="mt-2 text-sm text-ink-soft">
            Haz una pregunta filosófica. Recibirás un ensayo de dos párrafos que usa y cita
            frases de la base de datos scrapeada — o admite que no tiene fuentes para debatir.
          </p>
          <span className="mt-4 inline-block text-sm font-bold text-crimson group-hover:underline">
            Iniciar el debate →
          </span>
        </Link>

        <Link to="/optimizador" className="group panel transition hover:-translate-y-1">
          <p className="kicker">Ejercicio 02 · 包/受</p>
          <h2 className="mt-1 font-display text-2xl font-extrabold">Optimizador de Presupuesto</h2>
          <p className="mt-2 text-sm text-ink-soft">
            Empaqueta las citas en lotes que respetan el límite de tokens por petición,
            las traduce al japonés y muestra métricas 3D por lote y por frase con su recibo.
          </p>
          <span className="mt-4 inline-block text-sm font-bold text-crimson group-hover:underline">
            Ver el optimizador →
          </span>
        </Link>
      </section>
    </div>
  )
}

export default Landing
