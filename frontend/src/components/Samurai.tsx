/** Silueta de samurai estilo manga (SVG) recortada sobre el sol. */
export function Samurai() {
  return (
    <svg viewBox="0 0 240 340" className="h-full w-auto" aria-hidden="true">
      {/* estandarte de espalda (sashimono) */}
      <path d="M52 34 h18 v222 h-18 Z" fill="currentColor" opacity="0.9" />
      <rect x="59" y="22" width="4" height="30" fill="currentColor" />
      {/* vaina de katana */}
      <path d="M156 166 L174 188 L200 268 L191 273 L165 194 Z" fill="currentColor" />
      {/* mano en el puño */}
      <circle cx="153" cy="170" r="8" fill="currentColor" />
      {/* pierna trasera (hakama) */}
      <path d="M133 166 h24 l6 86 -8 56 -12 0 8 -54 Z" fill="currentColor" />
      {/* pierna delantera */}
      <path d="M107 166 h25 l7 86 -10 60 -14 0 8 -58 Z" fill="currentColor" />
      {/* torso / armadura (do) */}
      <path d="M103 104 h47 l17 50 -27 30 -46 -26 Z" fill="currentColor" />
      {/* hombrera trasera (sode) */}
      <path d="M95 94 q-16 -2 -14 -16 q2 -12 20 -14 l6 24 Z" fill="currentColor" />
      {/* cuello */}
      <path d="M119 84 h28 v24 h-28 Z" fill="currentColor" />
      {/* casco (kabuto) */}
      <path d="M111 66 a27 27 0 0 1 54 0 l-7 10 q-4 -8 -40 -8 Z" fill="currentColor" />
      {/* ala del casco (fukigaeshi) */}
      <path d="M115 74 l-7 22 12 6 4 -20 Z" fill="currentColor" />
      {/* protector de cuello (shikoro) */}
      <path d="M109 84 q-9 18 -4 32 h38 l8 -32 Z" fill="currentColor" />
      {/* cresta (maedate) */}
      <path d="M120 42 q16 -26 36 -8 l-9 4 q-10 -12 -20 -2 Z" fill="currentColor" />
      {/* rendija de ojos (negativo) */}
      <path d="M138 61 h19 l-3 6 h-13 Z" fill="var(--color-paper)" />
    </svg>
  )
}

export default Samurai
