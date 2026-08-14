import { NavLink } from 'react-router-dom'

const links = [
  { to: '/orador', label: 'Orador' },
  { to: '/optimizador', label: 'Optimizador' },
]

export function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b-2 border-ink bg-paper/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-3">
        <NavLink to="/" className="group flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center border-2 border-ink bg-crimson text-paper shadow-[2px_2px_0_rgba(28,26,23,0.9)]">
            <span className="font-display text-sm font-bold leading-none">虎書</span>
          </span>
          <span className="flex flex-col">
            <span className="font-display text-lg font-extrabold leading-none tracking-tight">
              Kosho<span className="text-crimson">.ai</span>
            </span>
            <span className="text-[10px] font-semibold uppercase tracking-[0.22em] text-ink-soft">
              citas · debate · presupuesto
            </span>
          </span>
        </NavLink>

        <nav aria-label="Secciones" className="ml-auto flex gap-1">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              className={({ isActive }) =>
                `relative px-3 py-2 font-display text-sm font-bold tracking-wide transition ${
                  isActive
                    ? 'text-crimson after:absolute after:inset-x-1 after:bottom-0 after:h-[3px] after:bg-crimson'
                    : 'text-ink hover:text-crimson'
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  )
}
