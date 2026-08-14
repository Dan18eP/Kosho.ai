# Kosho.ai — Orador de Debates Respaldado + Optimizador de Presupuesto y Empaquetado

Plataforma web (虎書) con dos secciones navegables que resuelven dos ejercicios sobre el
dataset scrapeado de `quotes.toscrape.com` (100 citas con autor). UI inspirada en manga
japonés con visualizaciones three.js que muestran métricas reales.

| Sección | Ejercicio | Qué hace |
|---|---|---|
| **Orador de Debates** | 1 | Responde preguntas filosóficas con un mini-ensayo de 2 párrafos que cita textualmente frases relevantes de la base de datos (embeddings semánticos bge-m3 con fallback TF-IDF). Si no hay fuentes, lo admite. |
| **Optimizador** | 2 | Agrupa las frases en lotes óptimos para traducirlas al japonés + explicar su contexto histórico, respetando el límite `X` de tokens por petición, y arroja un recibo con métricas por lote y por frase. |

## Estructura

```
backend/          FastAPI + módulos (debate, optimizer) + tests (pytest)
frontend/         React + Vite + Tailwind + three.js (Kosho.ai, manga UI)
models/enja_ct2   Modelo OPUS-MT en→ja convertido a CTranslate2 (int8)
models/enes_ct2   Modelo OPUS-MT en→es convertido a CTranslate2 (int8)
data/quotes.json  Dataset scrapeado (fuente canónica)
data/contexts.json  Contextos históricos pre-generados (español) para el Optimizador
data/embeddings.json  Vectores bge-m3 pre-generados para búsqueda semántica del Orador
scripts/          export_quotes.py · setup_ct2.py · setup_contexts.py · setup_embeddings.py
ARQUITECTURA.md   Diseño de la solución
PLAN_DE_ACCION.md Plan de implementación
RULES.md          Convenciones y estándares
```

> `models/` **no se versiona** (pesa ~700 MB): se regenera con
> `scripts/setup_ct2.py --all`. `data/sample.json` (seed local) tampoco se sube.

## Instalación

### Backend (Python 3.11+)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt   # incluye fastapi, tiktoken, playwright
pip install ctranslate2 sentencepiece   # motores locales de traducción (en→ja, en→es)
cd ..
.venv\Scripts\python scripts\export_quotes.py   # re-scrapea data/quotes.json
.venv\Scripts\python scripts\setup_ct2.py --all # modelos OPUS-MT en→ja y en→es (CTranslate2)
.venv\Scripts\python scripts\setup_contexts.py --workers 4  # pre-genera data/contexts.json
.venv\Scripts\python scripts\setup_embeddings.py  # pre-genera data/embeddings.json (bge-m3)
```

### Ollama (modelos locales de lenguaje para el Orador)

El ensayo se genera con **llama3.2:3b** (Ollama), los contextos del Optimizador con
**llama3.2:1b** y la búsqueda semántica de citas usa **bge-m3** (embeddings
multilingües). Si el modelo del ensayo no está disponible, el Orador cae a una
plantilla determinista; si bge-m3 falla, la recuperación cae a TF-IDF.

```bash
ollama pull llama3.2:3b   # ensayos del Orador de Debates
ollama pull llama3.2:1b   # generación de contextos (script setup_contexts.py)
ollama pull bge-m3        # embeddings para búsqueda semántica (script setup_embeddings.py)
```

### Frontend (Node 20+)

```bash
cd frontend
npm install
```

## Motores de traducción y LLM (todos gratuitos, sin API keys)

- **ctranslate2 (principal)** — local y offline: modelos Marian OPUS-MT convertidos a
  CTranslate2 int8 — `en→ja` (`models/enja_ct2`, frases del Optimizador) y `en→es`
  (`models/enes_ct2`, ensayos del Orador en español). Tokenización real con
  SentencePiece. Si el modelo no está, el API responde 503 con instrucciones.
- **deep_translator (alternativa web)** — Google/LibreTranslate/MyMemory con reintento
  automático entre backends ante rate-limit; también se usa como fallback de `en→es`.
- **mock** — solo para demo/CI.
- **Ollama** — `llama3.2:3b` escribe el ensayo del Orador (en inglés) y se traduce a
  español con CTranslate2 `en→es` si el idioma elegido es `es`; `llama3.2:1b` genera
  los contextos históricos del Optimizador en una pre-generación por script.
- **Embeddings (búsqueda semántica del Orador)** — `bge-m3` vía Ollama + similitud
  coseno; multilingüe, matchea preguntas en español contra citas en inglés sin
  traducir. Vectores pre-generados en `data/embeddings.json`; si falla, cae a TF-IDF.

El contexto histórico del Optimizador se genera **una vez** (`scripts/setup_contexts.py`)
y se guarda en `data/contexts.json` (español); en runtime se lee sin LLM, con un
`ContextEngine` local como fallback para autores no pre-generados. Ningún provider
depende de OpenAI.

## Ejecución

```bash
# Terminal 1 — backend (puerto 8000)
cd backend
.venv\Scripts\python -m uvicorn app.main:app --reload

# Terminal 2 — frontend (puerto 5173, proxy /api → backend)
cd frontend
npm run dev
```

Abrir http://localhost:5173 — la landing (`/`) muestra el samurai sobre el sol con
partículas three.js y el CTA **"Entrar a Kosho.ai"**. En **Orador** y **Optimizador**
hay un botón **"Actualizar citas"** que re-scrapea la web (puede tardar ~15s, el botón
muestra spinner). El Optimizador muestra "Frases a procesar" como cantidad de solo
lectura, siempre desde `data/quotes.json` actualizado.

## API

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/quotes` | GET | `{source, count, updated_at, quotes}` — citas actuales scrapeadas |
| `/api/quotes/refresh` | POST | Re-scrapea la web, guarda `data/quotes.json` y devuelve `{count, added}` |
| `/api/debate` | POST | `{question, language?, threshold?}` → ensayo 2 párrafos + citas con `translation` (es) o respuesta honesta |
| `/api/optimizer/specs` | GET | Spec default y providers disponibles |
| `/api/optimizer/preview` | POST | `{spec?, provider?}` → lotes sin ejecutar |
| `/api/optimizer/run` | POST | Ejecuta traducción+contexto y devuelve recibo + `items` (tokens por frase, traducción y contexto) |

Docs interactivas (Swagger): http://localhost:8000/docs

## Tests

```bash
cd backend
.venv\Scripts\python -m pytest tests -q      # 71 tests (unit + integración API)
.venv\Scripts\python -m ruff check app tests  # lint
cd ../frontend
npm run lint                                  # lint (oxlint)
npm run build                                 # typecheck + build
```

## Configuración del proveedor (Ejercicio 2)

La `ProviderSpec` define el proveedor ficticio: límite `X` (`max_tokens_per_request`,
default 2000), precios asimétricos por token enviado/recibido, overhead de formato y
la proyección de salida. El recibo reporta tokens **reales** re-contados con
`tiktoken` (`o200k_base`) tras procesar cada lote. Todo es editable desde el frontend,
y el BatchViz 3D muestra métricas por lote (utilización, tokens in→out, costo) y por
frase (antes → después).

## Documentación

- [ARQUITECTURA.md](./ARQUITECTURA.md) — diseño por capas y decisiones.
- [PLAN_DE_ACCION.md](./PLAN_DE_ACCION.md) — fases, entregables y DoD.
- [RULES.md](./RULES.md) — convenciones y estándares de desarrollo.
