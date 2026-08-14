import { useEffect, useRef } from 'react'
import * as THREE from 'three'

const SUN_VERT = `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`

const SUN_FRAG = `
uniform vec3 uColor;
uniform float uTime;
varying vec2 vUv;
void main() {
  vec2 centered = vUv - 0.5;
  float dist = length(centered);
  // Patrón de puntos halftone (impresión manga)
  vec2 p = vUv * 42.0;
  vec2 cell = fract(p);
  vec2 id = floor(p);
  float d = distance(cell, vec2(0.5));
  float wave = 0.5 + 0.5 * sin(uTime * 0.5 + id.x * 2.1 + id.y * 1.7);
  float dotR = 0.34 + 0.14 * wave;
  float dot = smoothstep(dotR, dotR - 0.10, d);
  // Halo que difumina los bordes del sol
  float halo = smoothstep(0.5, 0.36, dist);
  float rim = smoothstep(0.16, 0.30, dist);
  float alpha = dot * halo + rim * 0.10;
  if (alpha < 0.02) discard;
  gl_FragColor = vec4(uColor, alpha);
}
`

const PARTICLE_COUNT = 480

/** Fondo Kosho.ai: sol rojo con shader halftone + partículas sumi + parallax. */
export function Backdrop() {
  const mountRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 100)
    camera.position.set(0, 0, 12)

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    mount.appendChild(renderer.domElement)

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    // --- Sol rojo halftone ---
    const sunGeo = new THREE.PlaneGeometry(11, 11)
    const sunMat = new THREE.ShaderMaterial({
      uniforms: { uColor: { value: new THREE.Color('#e6352c') }, uTime: { value: 0 } },
      vertexShader: SUN_VERT,
      fragmentShader: SUN_FRAG,
      transparent: true,
      depthWrite: false,
      side: THREE.DoubleSide,
    })
    const sun = new THREE.Mesh(sunGeo, sunMat)
    sun.position.set(5.2, 3.4, -16)
    scene.add(sun)

    // --- Partículas sumi (tinta) ---
    const pGeo = new THREE.BufferGeometry()
    const positions = new Float32Array(PARTICLE_COUNT * 3)
    const colors = new Float32Array(PARTICLE_COUNT * 3)
    const base = new Float32Array(PARTICLE_COUNT * 3)
    const ink = new THREE.Color('#1c1a17')
    const crimson = new THREE.Color('#b3261e')
    const gold = new THREE.Color('#c9a227')
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const x = (Math.random() - 0.5) * 34
      const y = (Math.random() - 0.5) * 20
      const z = -6 + Math.random() * 12
      base[i * 3] = x
      base[i * 3 + 1] = y
      base[i * 3 + 2] = z
      positions[i * 3] = x
      positions[i * 3 + 1] = y
      positions[i * 3 + 2] = z
      const c = Math.random() > 0.82 ? crimson : Math.random() > 0.9 ? gold : ink
      colors[i * 3] = c.r
      colors[i * 3 + 1] = c.g
      colors[i * 3 + 2] = c.b
    }
    pGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    pGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    const pMat = new THREE.PointsMaterial({
      size: 0.09,
      vertexColors: true,
      transparent: true,
      opacity: 0.85,
      depthWrite: false,
    })
    const points = new THREE.Points(pGeo, pMat)
    scene.add(points)

    const sizes = new Float32Array(PARTICLE_COUNT)
    for (let i = 0; i < PARTICLE_COUNT; i++) sizes[i] = 0.4 + Math.random() * 1.6

    // --- Parallax por mouse ---
    const target = { x: 0, y: 0 }
    const pointer = (e: PointerEvent) => {
      target.x = (e.clientX / window.innerWidth - 0.5) * 1.4
      target.y = (e.clientY / window.innerHeight - 0.5) * 0.9
    }
    window.addEventListener('pointermove', pointer)

    let time = 0
    const animate = () => {
      time += 0.016
      sunMat.uniforms.uTime.value = time
      camera.position.x += (target.x - camera.position.x) * 0.04
      camera.position.y += (-target.y - camera.position.y) * 0.04
      camera.lookAt(0, 0, -4)

      const pos = pGeo.attributes.position as THREE.BufferAttribute
      for (let i = 0; i < PARTICLE_COUNT; i++) {
        const i3 = i * 3
        const s = sizes[i]
        pos.array[i3] = base[i3] + Math.sin(time * 0.22 + i) * s * 0.5
        pos.array[i3 + 1] = base[i3 + 1] + Math.cos(time * 0.18 + i * 0.7) * s * 0.4
      }
      pos.needsUpdate = true
      renderer.render(scene, camera)
    }

    if (reduced) {
      renderer.setAnimationLoop(null)
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
      window.removeEventListener('pointermove', pointer)
      ro.disconnect()
      sunGeo.dispose()
      sunMat.dispose()
      pGeo.dispose()
      pMat.dispose()
      renderer.dispose()
      mount.removeChild(renderer.domElement)
    }
  }, [])

  return (
    <div ref={mountRef} className="pointer-events-none fixed inset-0 -z-10 opacity-80" aria-hidden="true" />
  )
}

export default Backdrop
