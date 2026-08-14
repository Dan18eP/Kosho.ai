import { useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import type { BatchReport } from '../lib/api'
import { fmtMoney } from '../lib/format'

interface Props {
  batches: BatchReport[]
  maxTokens: number
}

const MAX_H = 5
const WIDTH = 2.2
const GAP = 3.2
const fmt = (n: number) => n.toLocaleString('en-US')

function utilColor(u: number): THREE.Color {
  const t = Math.min(1, Math.max(0, u))
  const a = new THREE.Color('#e8e0cd')
  const b = new THREE.Color('#c9a227')
  const c = new THREE.Color('#b3261e')
  if (t < 0.5) return a.clone().lerp(b, t * 2)
  return b.clone().lerp(c, (t - 0.5) * 2)
}

function makeLabel(b: BatchReport): THREE.Sprite {
  const canvas = document.createElement('canvas')
  canvas.width = 640
  canvas.height = 288
  const ctx = canvas.getContext('2d')
  if (!ctx) return new THREE.Sprite()
  ctx.fillStyle = 'rgba(244,239,228,0.92)'
  ctx.fillRect(0, 0, 640, 288)
  ctx.strokeStyle = '#1c1a17'
  ctx.lineWidth = 5
  ctx.strokeRect(3, 3, 634, 282)
  ctx.fillStyle = '#1c1a17'
  ctx.font = '700 46px "Shippori Mincho", serif'
  ctx.fillText(`Lote #${b.batch_id} · ${(b.utilization * 100).toFixed(0)}%`, 26, 64)
  ctx.fillStyle = '#4a443c'
  ctx.font = '600 30px Inter, sans-serif'
  ctx.fillText(`${b.phrase_count} frases`, 26, 118)
  ctx.fillText(`tokens ${fmt(b.input_tokens)} → ${fmt(b.output_tokens)}`, 26, 164)
  ctx.fillText(`costo ${fmtMoney(b.cost)}`, 26, 210)
  ctx.fillStyle = '#b3261e'
  ctx.fillRect(26, 232, 300 * Math.min(1, b.utilization), 8)
  const tex = new THREE.CanvasTexture(canvas)
  tex.colorSpace = THREE.SRGBColorSpace
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false })
  const sprite = new THREE.Sprite(mat)
  sprite.scale.set(5.4, 2.43, 1)
  return sprite
}

/** Visualización 3D del empaquetado con métricas por lote, hover y línea límite X. */
export function BatchViz({ batches, maxTokens }: Props) {
  const mountRef = useRef<HTMLDivElement | null>(null)
  const [hovered, setHovered] = useState<BatchReport | null>(null)

  const hoveredBatch = useMemo(
    () => batches.find((b) => b.batch_id === hovered?.batch_id) ?? null,
    [batches, hovered],
  )

  useEffect(() => {
    const mount = mountRef.current
    if (!mount || batches.length === 0) return

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(48, 1, 0.1, 100)
    camera.position.set(0, 6.5, 13)

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    mount.appendChild(renderer.domElement)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.08
    controls.maxPolarAngle = Math.PI / 2.05
    controls.minDistance = 6
    controls.maxDistance = 26

    scene.add(new THREE.AmbientLight(0xffffff, 0.9))
    const dir = new THREE.DirectionalLight(0xffffff, 1.4)
    dir.position.set(6, 10, 6)
    scene.add(dir)

    const grid = new THREE.GridHelper(26, 13, '#1c1a17', '#1c1a17')
    ;(grid.material as THREE.Material).transparent = true
    ;(grid.material as THREE.Material).opacity = 0.35
    grid.position.y = -0.01
    scene.add(grid)

    const group = new THREE.Group()
    const fills: THREE.Mesh[] = []
    const targets = new Map<number, number>()
    const currents = new Map<number, number>()
    const dispose: (() => void)[] = []

    // Línea límite X: marca el tope del contenedor (máx tokens por petición)
    const limitGeo = new THREE.BoxGeometry((batches.length - 1) * GAP + WIDTH, 0.06, 3)
    const limitMat = new THREE.MeshBasicMaterial({
      color: '#e6352c',
      transparent: true,
      opacity: 0.55,
    })
    const limit = new THREE.Mesh(limitGeo, limitMat)
    limit.position.set(0, MAX_H, 0)
    group.add(limit)
    dispose.push(() => {
      limitGeo.dispose()
      limitMat.dispose()
    })

    batches.forEach((b, i) => {
      const x = (i - (batches.length - 1) / 2) * GAP
      const contGeo = new THREE.BoxGeometry(WIDTH, MAX_H, WIDTH)
      contGeo.translate(0, MAX_H / 2, 0)
      const contEdge = new THREE.LineSegments(
        new THREE.EdgesGeometry(contGeo),
        new THREE.LineBasicMaterial({ color: '#2a2622', transparent: true, opacity: 0.75 }),
      )
      contEdge.position.set(x, 0, 0)
      group.add(contEdge)
      dispose.push(() => {
        contGeo.dispose()
        ;(contEdge.material as THREE.Material).dispose()
      })

      // Relleno proporcional a la utilización
      const fillH = Math.max(0.06, b.utilization * MAX_H)
      const fillGeo = new THREE.BoxGeometry(WIDTH * 0.86, fillH, WIDTH * 0.86)
      fillGeo.translate(0, fillH / 2, 0)
      const fillMat = new THREE.MeshStandardMaterial({
        color: utilColor(b.utilization),
        roughness: 0.85,
      })
      const fill = new THREE.Mesh(fillGeo, fillMat)
      fill.position.set(x, 0, 0)
      fill.userData.batchId = b.batch_id
      group.add(fill)
      fills.push(fill)
      targets.set(b.batch_id, 1)
      currents.set(b.batch_id, 0.001)
      dispose.push(() => {
        fillGeo.dispose()
        fillMat.dispose()
      })

      // Etiqueta 3D con métricas del lote
      const label = makeLabel(b)
      label.position.set(x, MAX_H + 1.15, 0)
      group.add(label)
      dispose.push(() => {
        const map = (label.material as THREE.SpriteMaterial).map
        if (map) map.dispose()
        ;(label.material as THREE.SpriteMaterial).dispose()
      })
    })

    scene.add(group)

    const raycaster = new THREE.Raycaster()
    const ndc = new THREE.Vector2()
    let hoveredId: number | null = null

    const onMove = (e: PointerEvent) => {
      const rect = renderer.domElement.getBoundingClientRect()
      ndc.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
      ndc.y = -((e.clientY - rect.top) / rect.height) * 2 + 1
      raycaster.setFromCamera(ndc, camera)
      const hit = raycaster.intersectObjects(fills)
      const id = hit.length ? (hit[0].object.userData.batchId as number) : null
      if (id !== hoveredId) {
        hoveredId = id
        const report = id != null ? batches.find((b) => b.batch_id === id) ?? null : null
        setHovered(report)
      }
      fills.forEach((f) => {
        const m = f.material as THREE.MeshStandardMaterial
        m.emissive.set(id === f.userData.batchId ? '#ff9900' : '#000000')
        m.emissiveIntensity = id === f.userData.batchId ? 0.35 : 0
      })
    }
    renderer.domElement.addEventListener('pointermove', onMove)
    renderer.domElement.addEventListener('pointerleave', () => {
      hoveredId = null
      setHovered(null)
      fills.forEach((f) => {
        ;(f.material as THREE.MeshStandardMaterial).emissive.set('#000000')
      })
    })

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const animate = () => {
      let done = true
      fills.forEach((f) => {
        const id = f.userData.batchId as number
        const t = targets.get(id) ?? 0
        let c = currents.get(id) ?? 0
        c += (t - c) * 0.06
        if (Math.abs(t - c) > 0.001) done = false
        currents.set(id, c)
        f.scale.y = c
      })
      if (done && reduced) renderer.setAnimationLoop(null)
      controls.update()
      renderer.render(scene, camera)
    }
    if (reduced) {
      fills.forEach((f) => (f.scale.y = targets.get(f.userData.batchId) ?? 1))
      renderer.render(scene, camera)
    } else {
      renderer.setAnimationLoop(animate)
    }

    const resize = () => {
      const { clientWidth: w, clientHeight: h } = mount
      renderer.setSize(w, h)
      camera.aspect = w / h
      camera.updateProjectionMatrix()
    }
    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(mount)

    return () => {
      renderer.setAnimationLoop(null)
      controls.dispose()
      ro.disconnect()
      renderer.domElement.removeEventListener('pointermove', onMove)
      renderer.domElement.removeEventListener('pointerleave', onMove)
      group.traverse((obj) => {
        if (obj instanceof THREE.Mesh || obj instanceof THREE.LineSegments) {
          obj.geometry.dispose()
        }
      })
      dispose.forEach((fn) => fn())
      renderer.dispose()
      mount.removeChild(renderer.domElement)
    }
  }, [batches, maxTokens])

  if (batches.length === 0) {
    return (
      <div className="flex h-72 items-center justify-center border-2 border-dashed border-ink/40 text-sm text-ink-soft">
        Ejecuta una simulación para ver el empaquetado 3D.
      </div>
    )
  }

  return (
    <div className="relative">
      <div
        ref={mountRef}
        className="h-80 w-full border-2 border-ink bg-washi/60 shadow-[4px_4px_0_rgba(28,26,23,0.9)]"
        role="img"
        aria-label="Visualización 3D de los lotes: altura = utilización, etiqueta con métricas por lote"
      />
      <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-ink-soft">
        <span className="tag">◼ altura = utilización del lote</span>
        <span className="tag">▁ línea roja = límite X por petición</span>
        <span className="tag">◎ arrastra para rotar · rueda para zoom</span>
      </div>
      {hoveredBatch && (
        <div
          className="pointer-events-none absolute right-2 top-2 w-64 border-2 border-ink bg-paper p-3 shadow-[3px_3px_0_rgba(28,26,23,0.9)]"
          role="status"
        >
          <p className="font-display text-sm font-extrabold">
            Lote #{hoveredBatch.batch_id}
            <span className="float-right text-crimson">{(hoveredBatch.utilization * 100).toFixed(1)}%</span>
          </p>
          <dl className="mt-2 space-y-1 text-xs">
            <div className="flex justify-between"><dt>Frases</dt><dd className="font-semibold">{hoveredBatch.phrase_count}</dd></div>
            <div className="flex justify-between"><dt>Tokens in → out</dt><dd className="font-semibold">{fmt(hoveredBatch.input_tokens)} → {fmt(hoveredBatch.output_tokens)}</dd></div>
            <div className="flex justify-between"><dt>Overhead</dt><dd className="font-semibold">{fmt(hoveredBatch.overhead_tokens)}</dd></div>
            <div className="flex justify-between"><dt>Costo</dt><dd className="font-semibold">{fmtMoney(hoveredBatch.cost)}</dd></div>
          </dl>
        </div>
      )}
    </div>
  )
}

export default BatchViz
