import { lazy, Suspense } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Nav } from './components/Nav'
import { DebateSection } from './sections/DebateSection'
import { Landing } from './sections/Landing'
import { OptimizerSection } from './sections/OptimizerSection'

const Backdrop = lazy(() => import('./three/Backdrop'))

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={null}>
        <Backdrop />
      </Suspense>
      <div className="flex min-h-screen flex-col">
        <Nav />
        <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/orador" element={<DebateSection />} />
            <Route path="/optimizador" element={<OptimizerSection />} />
            <Route path="*" element={<Landing />} />
          </Routes>
        </main>
        <footer className="border-t-2 border-ink/20 py-4 text-center text-xs text-ink-soft">
          <span className="font-display font-bold">Kosho.ai</span> — 虎書 · citas textuales respaldan cada debate · presupuesto por tokens
        </footer>
      </div>
    </BrowserRouter>
  )
}

export default App
