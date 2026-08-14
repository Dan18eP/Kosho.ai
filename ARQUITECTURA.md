# ARQUITECTURA — Kosho.ai (Orador de Debates + Optimizador de Presupuesto)

## 1. Resumen del proyecto

**Kosho.ai** (虎書) es una plataforma web con **dos secciones** navegables que resuelven
dos ejercicios, construida sobre el scraper existente (`scraper.py`) que extrae citas
textuales de `quotes.toscrape.com`. La UI es una interpretación **manga japonés**
(papel, tinta, sol rojo halftone) con visualizaciones three.js con métricas reales.

| Sección | Ejercicio | Propósito |
|---|---|---|
| **Orador de Debates** | Ejercicio 1 | Responde preguntas filosóficas con un mini-ensayo de 2 párrafos citando textualmente frases de la base de datos scrapeada. |
| **Optimizador** | Ejercicio 2 | Agrupa las frases en lotes óptimos para traducir al japonés + explicar contexto histórico, respetando un límite de fragmentos por petición, y arroja un recibo de consumo con métricas por lote y por frase. |

Fuente de datos actual: `scraper.py:1` — Playwright async, extrae `phrase` + `author` por página hasta que no hay más `.quote` (páginas de `quotes.toscrape.com/page/{n}/`). El dataset resultante (~100 frases) es la entrada de ambos ejercicios.

## 2. Stack tecnológico

| Capa | Tecnología | Justificación |
|---|---|---|
| Backend | **FastAPI** (Python 3.11+) | API síncrona simple, Pydantic para contratos, sirve los módulos de ambos ejercicios. |
| Frontend | **React + Vite + TypeScript** | SPA rápida, secciones navegables por rutas/tabs. |
| Estilos | **Tailwind CSS** | Tema manga: papel/tinta/sol rojo, tipografía *Shippori Mincho*, halftone y grano de papel. |
| 3D / visualización | **three.js** | `Backdrop` (sol halftone con shader + partículas sumi + parallax) y `BatchViz` (empaquetado 3D con métricas por lote, labels, hover y línea límite X). |
| Contador de tokens | **tiktoken** (`o200k_base`) | Conteo BPE exacto y reversible, consistente con facturación real por tokens. |
| Traducción (motor principal, Optimizador) | **CTranslate2** (OPUS-MT en→ja int8, local) | Modelo `en-jap/opus-2020-01-08` convertido; 100% local y gratis. Tokenización con SentencePiece real. Setup: `scripts/setup_ct2.py --pair en-ja`. |
| Traducción (ensayos es, Orador) | **CTranslate2** (OPUS-MT en→es int8, local) | Modelo `eng-spa/opus-2021-02-19` (SentencePiece `spm32k`) convertido en `models/enes_ct2`. Convierte el ensayo del LLM a español monolingüe. Fallback: deep-translator → texto original. |
| Traducción (web, alternativa) | **deep-translator** | GoogleTranslator / LibreTranslate / MyMemory gratuitos, con reintento entre backends. |
| LLM local (ensayos) | **Ollama** + `llama3.2:3b` | Escribe el mini-ensayo único (en inglés) con verificación anti-alucinación; sin él se degrada a plantilla determinista. |
| LLM local (contextos) | **Ollama** + `llama3.2:1b` | Pre-genera contextos históricos en `data/contexts.json` (una sola vez, por script). |
| Búsqueda semántica (Orador) | **Ollama** + `bge-m3` | Embeddings multilingües + coseno (`EmbeddingRetrievalEngine`); matchea preguntas en español contra citas en inglés. Vectores pre-generados en `data/embeddings.json`. |
| Contexto histórico | **ContextService** + `ContextEngine` | Lee `data/contexts.json` (pre-generado en español, runtime 0 ms); `ContextEngine` local determinista como fallback. |
| Datos | `data/quotes.json` · `data/contexts.json` · `data/embeddings.json` | Export del scraper como fuente canónica + contextos y vectores pre-generados. |

## 3. Requerimientos

### 3.1 Ejercicio 1 — El Orador de Debates Respaldado

**Funcionales**
- R1: Recibir pregunta filosófica/compleja en lenguaje natural.
- R2: Buscar en la base de citas las frases relacionadas con la pregunta (no inventar respuestas).
- R3: Redactar un mini-ensayo de exactamente 2 párrafos.
- R4: Usar y citar **textualmente** las frases encontradas para respaldar los argumentos (cita con autor).
- R5: Si no hay información relevante, **admitir** que no tiene fuentes para debatir.

**Implícitos (resueltos en el diseño)**
- Medición de relevancia: TF-IDF + similitud coseno con umbral configurable.
- Estructura argumentativa del ensayo con huecos para citas textuales.
- Falla honesta determinista si ninguna frase supera el umbral.

### 3.2 Ejercicio 2 — El Optimizador de Presupuesto y Empaquetado

**Funcionales**
- R6: Traducir al japonés y explicar el contexto histórico de las ~100 frases scrapeadas.
- R7: Proveedor cobra por cada fragmento de palabra (token) **enviado y recibido**.
- R8: Límite estricto: máximo "X" fragmentos por petición.
- R9: Calcular el tamaño exacto del texto **antes** de enviar.
- R10: Meter la mayor cantidad de frases por lote sin romper el límite (empaquetado dinámico).
- R11: Recibo final: total de unidades consumidas y número de peticiones necesarias.

**Implícitos (resueltos en el diseño)**
- Distinción entre tokens de entrada (exactos) y de salida (proyectados antes / reales después).
- Overhead de formato JSON + system prompt consumen presupuesto.
- Proveedor simulado con spec configurable (límite X y costo).

## 4. Arquitectura general (capas)

```
┌──────────────────────────────────────────────────────────────┐
│ FRONTEND (React + Vite + Tailwind + three.js)                │
│  ┌─────────────┐   ┌────────────────────────────┐            │
│  │ Sección 1   │   │ Sección 2                  │            │
│  │ Orador      │   │ Optimizador                │            │
│  │ Debates     │   │ (config X, precio, recibo) │            │
│  └──────┬──────┘   └────────────┬───────────────┘            │
└─────────┼───────────────────────┼────────────────────────────┘
          │ HTTP JSON             │ HTTP JSON
┌─────────▼───────────────────────▼────────────────────────────┐
│ BACKEND (FastAPI)                                            │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ /api/debate      │   /api/optimizer/run               │  │
│  │ /api/quotes      │   /api/optimizer/preview           │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ MÓDULO DEBATE                     MÓDULO OPTIMIZADOR    │  │
│  │ RetrievalEngine ──► EssayGenerator │  TokenCounter       │  │
│  │   (TF-IDF+coseno)                  │  Packer (bin-pack)  │  │
│  │                                    │  ReceiptBuilder     │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ PROVIDERS (abstracción común)                          │  │
│  │ MockProvider │ CTranslate2Provider │ DeepTranslatorP.  │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ DATA: data/quotes.json  |  ProviderSpec (config)       │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## 5. Módulo Ejercicio 1 — Orador de Debates Respaldado

### 5.1 Pipeline

```
pregunta ──► RetrievalEngine ──► [frases relevantes + score]
              │                      │
              │ sin frases >= umbral  │ con frases >= umbral
              ▼                      ▼
      Respuesta honesta      EssayGenerator (2 párrafos)
      "No tengo fuentes"     con citas textuales
```

### 5.2 Recuperación híbrida (embeddings semánticos + TF-IDF)

**Motor principal — `EmbeddingRetrievalEngine`** (semántico):
- Embeddings de oraciones con **bge-m3** (Ollama, multilingüe, local) + similitud coseno.
- Captura sinónimos y reformulaciones; al ser multilingüe, **una pregunta en español
  matchea directamente** las citas en inglés (no necesita traducción previa).
- Vectores del corpus pre-generados en `data/embeddings.json`
  (`scripts/setup_embeddings.py`); en runtime solo se embedde la pregunta del usuario (~1 s).
- Umbral propio `embed_threshold` (default 0.50), calibrado para que preguntas sin
  evidencia ("Which pet should I adopt?") no produzcan "fuentes" de ruido semántico.
  En este motor **no se relaja** el umbral: bajar 0.50 → 0.30 reintroduciría ruido.

**Fallback — `RetrievalEngine` (TF-IDF + coseno)**:
- Si Ollama no está, el modelo de embeddings falta o falla, se degrada a TF-IDF
  (determinista, sin red) con `threshold` 0.15 y reintento **relajado (×0.6)**.
- Para el motor léxico se traduce la consulta es→en (best-effort) cuando corresponde
  (la detección de idioma usa `_looks_non_english`); la pasada relajada solo aplica aquí.
- `_distinct`: deduplica a máx. 3 citas distintas (por frase normalizada); el ensayo
  exige **2 voces distintas** para no repetir la misma cita en ambos párrafos.
- Determinista y sin dependencias de red cuando usa el fallback.

### 5.3 EssayGenerator (LLM estricto + plantilla)

Pipeline por prioridad de tiempo y honestidad:

1. **llama3.2:3b (Ollama)** escribe un mini-ensayo de 2 párrafos (< 170 palabras) con
   system-prompt que fuerza el uso **solo** de las citas dadas, verbatim y con autor.
2. **Verificación**: `_contains_quotes` normaliza (sin no-alfanuméricos) y exige que
   ambas citas estén textualmente. Si el LLM parafraseó alguna, `_ensure_verbatim_quotes`
   la **anexa verbatim con su autor** (se conserva el texto único sin deshonestidad).
3. Si el idioma elegido es `es`, el ensayo ENTERO se traduce con `EsTranslator`
   (CTranslate2 en→es → deep-translator → original), quedando monolíngüe. Las citas
   conservan su traducción aparte para la vista (`RetrievedQuote.translation`).
4. Si el LLM no está disponible, falla o no cumple → **plantilla determinista** en
   EN/ES con ambas citas; jamás se inventa contenido.
5. Con 0 citas → respuesta honesta bilingüe (`HONEST_RESPONSE`); con 1 sola voz →
   `HONEST_ONE_VOICE` indicando que se necesitan 2 voces.

### 5.4 Respuesta honesta (R5)

- Si `RetrievalEngine` devuelve 0 frases ≥ umbral → respuesta tipo:
  > "No tengo frases en mi base de datos que respalden un debate sobre esta pregunta."
- No se inventa contenido ni se fabrican citas.

## 6. Módulo Ejercicio 2 — Optimizador de Presupuesto y Empaquetado

### 6.1 Concepto de "fragmento" y proveedor

La unidad de facturación es el **token**. El proveedor se define por una **`ProviderSpec`** inmutable:

```python
@dataclass(frozen=True)
class ProviderSpec:
    name: str = "MiniTranslate"
    tokenizer: str = "o200k_base"          # tiktoken
    max_tokens_per_request: int = 2000     # límite X (enviados + recibidos)
    max_chars_per_request: int | None = None  # proveedores char-based (MyMemory: 500)
    reserve_output: float = 0.35           # % del presupuesto reservado a completion
    price_per_input_token: float = 0.00000015   # $0.15 / 1M
    price_per_output_token: float = 0.00000060  # $0.60 / 1M
    currency: str = "USD"
    requests_per_minute: int = 60
    system_prompt_tokens: int = 80         # overhead fijo del prompt
    json_format_overhead: int = 25         # overhead por lote
```

**Justificación de valores**: límite `2000` forzará ~4-8 lotes con el dataset de 100 frases (demuestra el empaquetado); precios asimétricos entrada/salida copian el mercado real (GPT-4o-mini, Gemini Flash). Todo es configurable desde el frontend.

### 6.2 TokenCounter (precisión tiktoken + proyección)

- **Exacto (entrada)**: `tiktoken.get_encoding("o200k_base").encode(texto)` → cuenta real del prompt.
- **Proyección (salida)**: estimador heurístico conservador (`estimación = max(estimación_provided, chars/ratio)`) y margen reservado `reserve_output`. Nunca se envía un lote cuya `prompt + overhead + salida_proyectada > X`.
- **Reconteo (post)**: tras procesar cada lote se re-cuenta la completion real con tiktoken → el recibo reporta **reales**, no proyecciones.
- **Fallback**: si tiktoken no está disponible (offline), heurística `tokens ≈ chars / 3.5` (inglés) / `tokens ≈ chars / 2` (japonés). La spec declara qué tokenizador usó el recibo.
- El tokenizador es **pluggable**: tiktoken `o200k_base` por defecto; `sentencepiece` si el motor local es NLLB (el recibo es exacto contra el tokenizador que define el proveedor).

### 6.3 Packer (bin packing greedy)

Por cada frase se calcula `costo_item = tokens_prompt(frase) + salida_proyectada(frase)`.

```
items = ordenar frases por costo desc      # First-Fit Decreasing
lotes = []
for frase in items:
    colocar en el primer lote con espacio suficiente
    o abrir un nuevo lote si prompt+overhead+salida > X
Nunca romper el límite: verificación estricta antes de añadir
```

- Objetivo: **maximizar frases por lote** sin exceder `X`.
- Métrica de calidad: `utilización = tokens_efectivos / (X × nº_lotes)`.
- Comparación opcional: greedy vs. fuerza bruta/DP en dataset pequeño para demostrar optimalidad (tabla de eficiencia).

### 6.4 Providers (interfaz común)

```python
@dataclass(frozen=True)
class PhraseRef:
    phrase: str
    author: str

class TranslatorProvider(Protocol):
    name: str
    def process_batch(self, refs: list[PhraseRef]) -> BatchResult: ...
```

Todos los providers son **gratuitos y sin API keys**. El contexto histórico viene de
`ContextService`: lee `data/contexts.json` (pre-generado en español por
`scripts/setup_contexts.py` con llama3.2:1b y traducido en→es), con `ContextEngine`
(determinista) como fallback en runtime — a costo 0 ms. Ningún provider depende de
OpenAI. Ante fallos de red/rate-limit se lanza `ProviderError` → HTTP 503 con mensaje
claro (nunca un 500).

| Provider | Traducción | Contexto histórico | Costo | Tokenizador |
|---|---|---|---|---|
| `CTranslate2Provider` (local, **motor principal**) | OPUS-MT en→ja int8 (`models/enja_ct2`), SentencePiece real + `clean_japanese` | `ContextService` → `data/contexts.json` (es) | 0$ (simulado con spec) | sentencepiece |
| `DeepTranslatorProvider` (web, alternativa) | GoogleTranslator / LibreTranslate / MyMemory (reintento entre backends) | `ContextService` → `data/contexts.json` (es) | free / rate-limited | tiktoken |
| `MockProvider` (solo CI/demo) | determinista | `ContextService` → `data/contexts.json` (es) | 0$ | tiktoken |

- El **Packer no depende del provider**: recibe `ProviderSpec` y calcula lotes; el provider ejecuta.
- Las restricciones por proveedor (chars de MyMemory, RPM) se modelan en la spec.
- Cada provider recibe `PhraseRef` (frase + autor) para poder generar contexto con conocimiento del autor.
- Setup del modelo local: `python scripts/setup_ct2.py` (descarga `en-jap/opus-2020-01-08.zip` y convierte a CTranslate2 int8 en `models/enja_ct2`). Si falta, `CTranslate2Provider` responde HTTP 503 con instrucciones.

### 6.5 Recibo (ReceiptBuilder)

Desglose por lote y totales:

```json
{
  "spec": {...},
  "total_requests": 5,
  "total_input_tokens": 1750,
  "total_output_tokens": 8120,
  "total_tokens": 9870,
  "total_cost_usd": 0.0051,
  "batches": [
    {
      "batch_id": 1,
      "phrase_count": 21,
      "input_tokens": 360,
      "output_tokens": 1610,
      "cost_usd": 0.00102,
      "utilization": 0.98
    }
  ]
}
```

### 6.6 Reporte por frase (PhraseReport)

Además del recibo agregado, `POST /api/optimizer/run` devuelve `items` con el detalle
de **cada frase**: tokens antes (entrada, contados con tiktoken) y después (salida,
re-contada tras procesar), junto con la traducción al japonés y el contexto histórico
asociado, para que el usuario identifique cada cita aunque no conozca el idioma.

```json
{
  "index": 2,
  "phrase": "Knowledge is power.",
  "author": "Francis Bacon",
  "input_tokens": 5,
  "output_tokens": 37,
  "translation": "知識は力です。",
  "context": "Esta cita se atribuye a Francis Bacon…"
}
```

## 7. Backend (FastAPI)

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/quotes` | GET | `{source, count, updated_at, quotes}` — citas actuales. |
| `/api/quotes/refresh` | POST | Re-scrapea `quotes.toscrape.com`, guarda `data/quotes.json` atómicamente, invalida la caché y devuelve `{count, added}` (diff de frases nuevas). Error de red → 502. |
| `/api/debate` | POST | `{question, threshold?, language?}` → ensayo 2 párrafos o respuesta honesta; cada cita incluye `score` y `translation` (cuando `language=es`). |
| `/api/optimizer/specs` | GET | Specs de proveedores disponibles. |
| `/api/optimizer/preview` | POST | `{spec, provider?}` → lotes planificados sin ejecutar (vista previa). |
| `/api/optimizer/run` | POST | `{spec, provider?}` → recibo + `items` (tokens por frase y resultados). |

- Contratos con **Pydantic**; errores con mensajes claros (ej. "frase excede el límite X incluso en lote único"; `ProviderError` → HTTP 503).
- CORS habilitado para el frontend de Vite.
- El refresh es síncrono (corre en el threadpool de FastAPI); `scripts/setup_ct2.py` y `scripts/export_quotes.py` siguen disponibles.

## 8. Frontend (React + Vite + Tailwind + three.js) — Kosho.ai

### 8.1 Tema manga japonés (ui-ux-designer)
- Paleta: papel (`#f4efe4`), tinta (`#1c1a17`), sol rojo (`#e6352c`), oro (`#c9a227`); bordes gruesos, sombras duras de sello y esquinas rectas.
- Tipografía: **Shippori Mincho** (display, estilo impresión japonesa) + Inter (cuerpo).
- Textura: halftone (puntos) y grano de papel vía SVG noise; sello con kanji 虎書 en el logo.
- Estados de carga/vacío/error diseñados; `prefers-reduced-motion` respetado.

### 8.2 three.js — Backdrop (sol + tinta)
- **Sol rojo halftone**: `ShaderMaterial` que aplica dithering de puntos (impresión manga) y halo; pulso sutil.
- **Partículas sumi**: tinta dispersándose con deriva por ruido (tinta/rojo/oro).
- **Parallax por mouse** con damping de cámara.
- Carga lazy (chunk separado) y limpieza completa de recursos.

### 8.3 three.js — BatchViz con métricas por lote
- Columnas 3D por lote: altura = **utilización**, color semántico papel→oro→rojo; contenedor wireframe = capacidad total (límite X).
- **Línea roja límite X** que cruza todos los contenedores.
- **Etiquetas 3D por lote** (canvas sprites): lote #, utilización %, frases, tokens in→out, costo, barra de utilización.
- **Hover (raycast)** → tooltip con métricas completas del lote; animación de llenado (grow) al cargar.
- OrbitControls con damping; raycasting con `InstancedMesh`-like (meshes agrupados).

### 8.4 Secciones navegables (react-router)
- **`/`** → **Landing** (vista de presentación): hero a pantalla parcial con el Backdrop
  three.js (sol halftone + partículas sumi) visible, **samurai en SVG** recortado sobre
  el sol, descripción del proyecto y CTA **"Entrar a Kosho.ai →"**; abajo, tarjetas de
  las dos funcionalidades.
- **`/orador`** → Orador: pregunta, idioma, ensayo 2 párrafos con citas destacadas y score; panel "sin fuentes" si aplica. Incluye el componente `QuotesSource` (fuente + **Actualizar citas**).
- **`/optimizador`** → Optimizador: spec (X, precio in/out, provider = ctranslate2 default), **"Frases a procesar" = cantidad de solo lectura** (siempre desde la web), vista previa, ejecución, **BatchViz 3D con métricas**, tabla de lotes y detalle por frase.
- `QuotesSource`: muestra `N citas · quotes.toscrape.com · act. …` y el botón **Actualizar citas** (POST `/api/quotes/refresh`, spinner, resultado "+N nuevas" / "Sin cambios"). Las frases no son editables.
- Navegación superior manga (subrayado rojo en la sección activa).

## 9. Estructura de archivos propuesta

```
ia-exercise-2/
├── scraper.py                  # existente
├── data/
│   ├── quotes.json             # export del scraper (fuente canónica)
│   ├── contexts.json           # contextos pre-generados (es), 0 LLM en runtime
│   └── embeddings.json         # vectores bge-m3 del Orador (semántica)
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # FastAPI + CORS + routers
│       ├── core/
│       │   ├── provider_spec.py
│       │   ├── token_counter.py
│       │   ├── translators.py   # EsTranslator (en→es) y WebTranslator
│       │   └── llm.py           # OllamaClient (ensayos y contextos)
│       ├── modules/
│       │   ├── debate/
│       │   │   ├── retrieval.py          # TF-IDF + EmbeddingRetrievalEngine
│       │   │   ├── essay_generator.py
│       │   │   └── service.py   # DebateService (híbrido, idioma, distinct)
│       │   └── optimizer/
│       │       ├── packer.py
│       │       ├── receipt.py
│       │       ├── context_service.py  # data/contexts.json + fallback ContextEngine
│       │       └── providers/
│       │           ├── base.py
│       │           ├── mock.py
│       │           ├── ctranslate2_provider.py
│       │           └── deep_translator_provider.py
│       └── data/
│           ├── quotes_repo.py
│           └── embedding_cache.py  # lee/escribe data/embeddings.json
├── models/
│   ├── enja_ct2/                # OPUS-MT en→ja (CTranslate2 int8)
│   └── enes_ct2/                # OPUS-MT en→es (CTranslate2 int8)
```
> `models/` se excluye del control de versiones: se regenera con
> `scripts/setup_ct2.py --all`.
├── scripts/
│   ├── setup_ct2.py             # --pair en-ja|en-es · --all
│   ├── setup_contexts.py        # pre-genera data/contexts.json (--workers/--force)
│   └── setup_embeddings.py      # pre-genera data/embeddings.json (bge-m3)
├── frontend/
│   ├── package.json
│   ├── tailwind.config.js
│   └── src/
│       ├── App.tsx
│       ├── components/         # Nav, Panel, StatusBadge, ...
│       ├── three/              # OrbBackground, BatchViz
│       └── sections/
│           ├── DebateSection.tsx
│           └── OptimizerSection.tsx
└── ARQUITECTURA.md
└── PLAN_DE_ACCION.md
```

## 10. Consideraciones de seguridad y calidad

- No exponer claves de API en el frontend; el backend las lee de variables de entorno.
- `deep-translator` web puede rate-limitearse: el recibo incluye fallos de petición y reintentos.
- Citas mostradas **textualmente** desde el dataset (evita alucinación e inyección de citas falsas).
- Tests unitarios del Packer (propiedades: nunca romper X, todas las frases cubiertas, máxima utilización) y del RetrievalEngine (umbral, falla honesta).
