# RULES.md — Convenciones y estándares de desarrollo

Reglas obligatorias para el proyecto. Derivadas de las skills de buenas prácticas instaladas (`backend-architect`, `frontend-specialist`, `ui-ux-designer`, `unit-test-generator`, `integration-test-builder`, `code-reviewer`, `code-commentator`, `git-strategist`) y adaptadas a este stack: **FastAPI + React (Vite) + Tailwind + three.js**.

Prioridad de resolución de conflictos: **seguridad > correctitud > rendimiento > mantenibilidad > estilo** (skill `code-reviewer`).

---

## 1. Stack y herramientas

| Área | Herramienta | Regla |
|---|---|---|
| Backend | FastAPI + Pydantic | Python 3.11+ |
| Frontend | React 18+ + TypeScript + Vite | TS strict mode obligatorio |
| Estilos | Tailwind CSS | Utility-first; design tokens en `tailwind.config.js` |
| UI | shadcn/ui + Radix + lucide-react | Componentes primitivos para a11y |
| Animaciones | framer-motion + three.js | 60fps; soportar `prefers-reduced-motion` |
| Estado | React Query (servidor) + Zustand (cliente) | — |
| Tests | pytest (backend) / Vitest + RTL (frontend) | — |
| Lint/Format | Ruff + Black (Python) / ESLint + Prettier (TS) | Correr antes de cada commit |

## 2. Estándares de código backend (Python)

- **Nombres**: funciones/archivos `snake_case`, clases `PascalCase`, constantes `UPPER_SNAKE_CASE`. Nombres que revelen intención.
- **Tamaño**: funciones < 200 líneas; hacer una sola cosa; complejidad ciclomática < 10.
- **DRY**: tres instancias de código similar justifican extracción; no sobre-abstraer.
- **SOLID**: cada clase una responsabilidad; `ProviderSpec` inmutable (`@dataclass(frozen=True)`); dependencias invertidas (los módulos usan el protocolo `TranslatorProvider`, nunca un provider concreto).
- **Tipado**: anotaciones completas; `dataclasses`/`Protocol` para contratos; sin `Any` a menos que sea inevitable y justificado.
- **Errores**: excepciones con mensajes descriptivos y accionables; distinguir errores para el usuario (API) de errores de desarrollo (logs).

## 3. Estándares de código frontend (TypeScript)

- **TS strict**: `strict: true`; prohibido `any`; tipos explícitos en props y retornos.
- **Componentes**: puros, reutilizables, una responsabilidad; props fuertemente tipadas y con defaults.
- **Rendimiento de render**: `React.memo`/`useMemo`/`useCallback` solo donde aportan (profiles previos); evitar re-renders innecesarios.
- **State**: datos del servidor por React Query; estado de UI local con Zustand; nada de estado global sin necesidad.
- **Estilos**: solo Tailwind; tokens para color/espaciado/tipografía; `@apply` solo para patrones repetidos.

## 4. Arquitectura y límites de capas

- Respetar los límites de la arquitectura (`ARQUITECTURA.md`): `core` → `modules` → `api`; nunca acoplar capas en dirección inversa.
- Los módulos de negocio (debate, optimizer) **no dependen de FastAPI** ni del frontend.
- El empaquetador y el contador de tokens **no dependen del provider** (interfaz `TranslatorProvider`).
- La API solo serializa/valida (Pydantic) y delega; la lógica vive en los módulos.
- No esconder lógica en archivos de ruta; `main.py` solo monta routers.

## 5. Diseño de API (backend-architect)

- REST semántico: verbos correctos (`GET` lee, `POST` crea/ejecuta), códigos de estado HTTP correctos (200/201/400/404/422/500).
- Contratos **siempre con Pydantic** (request/response); nunca dicts sueltos en respuestas.
- Errores estructurados: `{detail: {code, message}}`; mensajes distinguibles usuario vs. desarrollador.
- Validación de entrada en todos los endpoints (trust boundary).
- Documentación automática: FastAPI genera OpenAPI; no duplicar docs a mano.
- Endpoints con efectos de red/IA (optimizer) exponer también un modo `preview` sin ejecutar.

## 6. UI/UX (ui-ux-designer + frontend-specialist)

- **WCAG 2.1 AA** mínimo: contraste de color, navegación por teclado, HTML semántico, `aria-label` en controles, `role="status"`/live regions para resultados asíncronos.
- Dark mode como tema principal, light como secundario (estilo AWS: azul `#232f3e`, acento `#ff9900`).
- Estados obligatorios en cada pantalla: **carga** (skeleton), **vacío**, **error** (diseñado, no default del navegador).
- Micro-interacciones y animaciones a 60fps; respetar `prefers-reduced-motion`.
- Mobile-first responsive; foco visible siempre.
- three.js: carga lazy; degradar a fondo estático si el dispositivo no lo soporta.

## 7. Seguridad (code-reviewer + backend-architect)

- **Secrets en variables de entorno, jamás en el código ni en commits** (claves de deep-translator/ChatGPT, etc.).
- El frontend nunca recibe claves de API.
- Validar y sanitizar toda entrada de usuario (preguntas, umbrales, specs) antes de procesarla.
- Escapar cualquier contenido dinámico renderizado en React (evitar XSS).
- No registrar datos sensibles ni citas completas en logs si no es necesario.
- Lista blanca de orígenes CORS, no `*` en producción.
- Auditoría de dependencias (`npm audit`, `pip-audit`/`uv` check) antes de cada release.

## 8. Testing (unit-test-generator + integration-test-builder)

- **Unit (pytest / Vitest+RTL)**:
  - Patrón **AAA** (Arrange–Act–Assert); nombres descriptivos (`test_packer_no_rompe_el_limite`).
  - Mocks para dependencias externas (red, tiktoken descarga, providers).
  - Happy path + edge cases + errores; pruebas **parametrizadas** para variaciones.
  - Aislamiento y determinismo: sin estado compartido entre tests.
  - Propiedades críticas del Packer: nunca excede `X`, todas las frases cubiertas una vez, utilización máxima.
  - Retrieval: umbral, orden de scores, falla honesta, citas textuales sin alteración.
- **Integración (pytest + httpx/TestClient)**:
  - Probar flujos completos de API (`/api/debate`, `/api/optimizer/run`) con TestClient.
  - Verificar contratos (schemas de respuesta) y escenarios de error (422/400).
  - Datos de prueba aislados (fixtures); sin depender de red real en CI (MockProvider).
- **Cobertura**: caminos felices + bordes obligatorios; no solo cantidad, sino calidad (el test debe probar comportamiento, no implementación).
- Sin código específico de tests en archivos de producción.

## 9. Documentación y comentarios (code-commentator)

- El código debe ser **auto-documentado** con buenos nombres; los comentarios explican **por qué**, no **qué**.
- Documentar algoritmos (retrieval, bin-packing, proyección de tokens) con contexto y edge cases.
- Docstrings en Python (numpydoc) en funciones públicas de `core` y `modules`; JSDoc/TSDoc para props y componentes reutilizables.
- Documentar la **`ProviderSpec`** (campos, unidades, defaults) junto a su definición.
- Los comentarios se actualizan junto con el código (un comentario desactualizado es un bug).
- Sin bloques de comentarios estilo "historial"; git es el historial.

## 10. Git y commits (git-strategist)

- **Conventional Commits**: `type(scope): description`
  - `feat(optimizer)` / `fix(packer)` / `docs(rules)` / `refactor` / `test` / `perf` / `build` / `ci` / `chore`.
  - `BREAKING CHANGE` o `!` para cambios incompatibles.
- **Branching**: GitHub Flow — rama por feature desde `main`; PR con revisión; merge a `main` = potencialmente desplegable.
- Nombre de ramas: `feat/orador-debates`, `fix/limite-tokens`, `chore/deps`.
- **PR**: descripción clara (contexto, qué, cómo probar), checklist, mínimo 1 review aprobado; PR pequeños y enfocados.
- **Nunca commitear secrets**. Verificar `git status`/`git diff` antes de stagear.
- Mensajes de commit en imperativo, línea de asunto < 72 chars.

## 11. Code review (code-reviewer)

Proceso por PR:
1. Leer contexto: descripción del PR, issue relacionado, alcance.
2. Revisar arquitectura: ¿encaja en capas? ¿respeta patrones existentes?
3. Seguridad: OWASP (inyección, secrets, validación en trust boundaries).
4. Rendimiento: N+1, re-renders innecesarios, ops bloqueantes.
5. Errores y edge cases: null/empty, degradación de dependencias externas (rate limits).
6. Cobertura de tests: happy path, errores, integración para cambios de API.
7. Feedback accionable y clasificado: **blocking** (debe arreglarse), **suggestion** (mejoraría), **nitpick** (opcional). Incluir ejemplos de código.

Checklist mínimo del reviewer: no `any`, sin secrets, validación de inputs, tipos correctos, tests presentes, límites de capas respetados.

## 12. Definición de hecho (DoD) por tarea

- [ ] Lint y format en verde (`ruff check . && ruff format --check .` / `eslint && prettier --check`).
- [ ] Typecheck en verde (`tsc --noEmit`).
- [ ] Tests unitarios + integración nuevos y existentes en verde (`pytest` / `vitest run`).
- [ ] Sin secrets ni datos sensibles en el diff.
- [ ] Cumple capas, convenciones y convenciones de commit.
- [ ] UI: estados carga/vacío/error cubiertos; accesibilidad mínima WCAG AA.
- [ ] Documentación del código ("por qué") donde haya lógica compleja.
