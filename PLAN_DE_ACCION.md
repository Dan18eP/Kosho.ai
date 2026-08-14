# PLAN DE ACCIÓN — Kosho.ai (Orador de Debates Respaldado + Optimizador de Presupuesto)

## 0. Objetivo

Entregar una plataforma web con dos secciones navegables que resuelvan el **Ejercicio 1** (debate respaldado por citas scrapeadas) y el **Ejercicio 2** (empaquetado de lotes para traducción al japonés + contexto histórico, con recibo de consumo), construida sobre `scraper.py` existente y siguiendo la [ARQUITECTURA.md](./ARQUITECTURA.md).

## 1. Fases y entregables

### Fase 0 — Preparación y datos
| Tarea | Detalle | Entregable |
|---|---|---|
| 0.1 | Revisar entorno (Python 3.11+, Node 20+), `pip install playwright` ya requerido por scraper. | Entorno verificado |
| 0.2 | Ejecutar `scraper.py` y exportar resultados a `data/quotes.json` (lista `{phrase, author}`). | `data/quotes.json` (~100 frases) |
| 0.3 | Seed data de prueba (subconjunto + casos borde: corpus vacío, frases largas, autores repetidos). | `data/sample.json` |

**Definición de hecho (DoD)**: `data/quotes.json` no vacío; reproducible con un comando documentado.

### Fase 1 — Núcleo Ejercicio 1 (Orador)
| Tarea | Detalle | Entregable |
|---|---|---|
| 1.1 | `backend/app/modules/debate/retrieval.py`: tokenización, stopwords (EN/ES), TF-IDF, similitud coseno, `RelevanceThreshold` (default 0.15), `max_quotes` (default 3). | Motor de relevancia |
| 1.2 | `backend/app/modules/debate/essay_generator.py`: plantilla de 2 párrafos con huecos para citas **textuales** + autor. | Generador de ensayo |
| 1.3 | Respuesta honesta: 0 frases ≥ umbral → "no tengo fuentes para debatir". | Fallback R5 |
| 1.4 | Tests: umbral, orden de scores, falla honesta, citas sin alteración, siempre 2 párrafos. | `tests/test_debate.py` |

**DoD**: función `debate(question, threshold)` devuelve ensayo con citas textuales o respuesta honesta; tests en verde.

### Fase 2 — Núcleo Ejercicio 2 (Packer + Recibo)
| Tarea | Detalle | Entregable |
|---|---|---|
| 2.1 | `backend/app/core/token_counter.py`: contador exacto con `tiktoken o200k_base`, proyector de salida (con `reserve_output`), reconteo post-procesado, fallback heurístico sin tiktoken. | TokenCounter |
| 2.2 | `backend/app/core/provider_spec.py`: dataclass inmutable `ProviderSpec` (X=2000 default, precios in/out, RPM, overhead prompt/JSON). | Spec |
| 2.3 | `backend/app/modules/optimizer/packer.py`: **First-Fit Decreasing** con verificación estricta `prompt + overhead + salida_proyectada ≤ X`; reporta utilización por lote. | Packer |
| 2.4 | `backend/app/modules/optimizer/receipt.py`: recibo con desglose por lote + totales (tokens in/out, costo, nº peticiones). | Recibo |
| 2.5 | Tests de propiedades: nunca rompe X, todas las frases cubiertas, una sola vez, máxima utilización; comparación greedy vs. DP en dataset pequeño. | `tests/test_packer.py` |

**DoD**: `pack(phrases, spec)` → lotes válidos + recibo; tests en verde.

### Fase 3 — Providers de traducción
| Tarea | Detalle | Entregable |
|---|---|---|
| 3.1 | `providers/base.py`: protocolo `TranslatorProvider` (`translate_batch`, `explain_context`). | Contrato |
| 3.2 | `providers/mock.py`: determinista para demo/CI (no requiere red). | MockProvider |
| 3.3 | `providers/deep_translator_provider.py`: `GoogleTranslator`/`MyMemory`/`Libre` para traducción; `ChatGptTranslator` para contexto (key por env var). Modelar chars máx (MyMemory 500). | WebProvider |
| 3.4 | `providers/ctranslate2_provider.py`: NLLB/OPUS-MT convertido para `translate_batch`; LLM decoder-only (Qwen2/Mistral int8) para contexto. Documentar descarga/conversión. | LocalProvider |

**DoD**: los 3 providers implementan el protocolo; Mock usado por default en tests; errores de red capturados.

### Fase 4 — Backend FastAPI
| Tarea | Detalle | Entregable |
|---|---|---|
| 4.1 | `app/main.py`: FastAPI + CORS + routers. | App |
| 4.2 | Endpoints: `GET /api/quotes`, `POST /api/debate`, `GET /api/optimizer/specs`, `POST /api/optimizer/preview`, `POST /api/optimizer/run`. | API |
| 4.3 | `app/data/quotes_repo.py`: carga de `data/quotes.json`. | Repo |
| 4.4 | Contratos Pydantic + errores claros (frase que excede X incluso en lote único). | Schemas |

**DoD**: `uvicorn app.main:app` arranca; endpoints probados con curl/pydoc.

### Fase 5 — Frontend React (Vite + Tailwind + three.js)
| Tarea | Detalle | Entregable |
|---|---|---|
| 5.1 | Scaffold Vite + React + TS; Tailwind config con paleta estilo AWS (azul `#232f3e`, acento `#ff9900`). | Base UI |
| 5.2 | `Nav` + rutas (`/orador`, `/optimizador`, `/datos`). | Navegación |
| 5.3 | `three/OrbBackground` (fondo) y `three/BatchViz` (visualización 3D de lotes). | Visualización |
| 5.4 | `DebateSection`: input de pregunta, botón Debatir, panel del ensayo con citas destacadas + scores + estado "sin fuentes". | Sección 1 |
| 5.5 | `OptimizerSection`: formulario de spec (X, precios, provider), preview de lotes, ejecución, recibo formateado. | Sección 2 |
| 5.6 | `QuotesSection`: listado del dataset. | Sección 3 |

**DoD**: navegación funcional entre las 2 secciones principales; llamadas reales al backend; diseño AWS limpio.

### Fase 6 — Integración, pruebas y QA
| Tarea | Detalle | Entregable |
|---|---|---|
| 6.1 | Integrar frontend ↔ backend (proxy de Vite a FastAPI). | E2E |
| 6.2 | Tests E2E manuales: pregunta con y sin fuentes; spec X=500/2000/8000 → nº de lotes cambia correctamente. | QA |
| 6.3 | Rendimiento/UX: three.js no degrada; carga de datos razonable. | QA |
| 6.4 | README con instrucciones de instalación/ejecución (scraper, backend, frontend). | README.md |

**DoD**: flujo completo de ambos ejercicios funcional desde el frontend.

## 2. Dependencias y orden

```
Fase 0 → Fase 1 ──► Fase 4 (endpoints debate)
       ↘ Fase 2 ──► Fase 3 ─► Fase 4 (endpoints optimizer)
                            └──► Fase 5 ──► Fase 6
```

- Fase 4 depende de Fases 1 y 2/3; Fase 5 depende de Fase 4.
- Fases 1 y 2 son independientes entre sí (paralelizables).

## 3. Riesgos y mitigación

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Scraper bloqueado / web sin frases | Sin datos | Playwright headless, retry; dataset espejo en `data/quotes.json` |
| tiktoken no instalable (offline) | Sin conteo exacto | Fallback heurístico por chars; spec declara tokenizador |
| CTranslate2: descarga/conversión de modelos pesada | Retraso | MockProvider default; NLLB int8; documentar comandos de conversión |
| deep-translator rate-limits web | Fallos en traducción | Retry + backoff; recibo registra reintentos; alternativa MyMemory/Libre |
| three.js degrada rendimiento | UX pobre | Carga lazy, límite de partículas, degradación a estático |
| Proveedor sin LLM para contexto | R5/R6 incompletos | Opción web ChatGptTranslator o LLM local Qwen2 int8 |

## 4. Estimación de esfuerzo (orientativa)

| Fase | Esfuerzo | Prioridad |
|---|---|---|
| F0 Preparación | Bajo | Alta |
| F1 Núcleo Orador | Medio | Alta |
| F2 Núcleo Packer | Medio-Alto | Alta |
| F3 Providers | Medio | Media |
| F4 Backend API | Bajo-Medio | Alta |
| F5 Frontend | Alto | Alta |
| F6 Integración/QA | Medio | Media |

**Prioridades de corte**: si falta tiempo, F3 se reduce a MockProvider + DeepTranslator (omitiendo CTranslate2), y F5.6 se aplaza sin afectar los dos ejercicios.
