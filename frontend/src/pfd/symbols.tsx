import type { ReactElement } from 'react'

/** Engineering symbols, drawn in a 120 x 72 box and rendered at 140 x 84; the process line runs at y = 36 (FEHE hot side at y = 54). */
const S = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinejoin: 'round', strokeLinecap: 'round' } as const
const stub = (x1: number, x2: number, y = 36) => <line x1={x1} x2={x2} y1={y} y2={y} {...S} strokeWidth={1.2} />

const symbols: Record<string, () => ReactElement> = {
  pump: () => (
    <g>
      {stub(0, 36)}{stub(84, 120)}
      <circle cx="60" cy="36" r="24" {...S} />
      <path d="M 60 12 L 84 24 L 84 36" {...S} />
      <path d="M 44 36 L 60 28 L 60 44 Z" {...S} fill="currentColor" fillOpacity={0.25} />
    </g>
  ),
  heater: () => (
    <g>
      {stub(0, 36)}{stub(84, 120)}
      <circle cx="60" cy="36" r="24" {...S} />
      <polyline points="40,44 50,28 60,44 70,28 80,44" {...S} stroke="var(--c-heat)" />
    </g>
  ),
  cooler: () => (
    <g>
      {stub(0, 36)}{stub(84, 120)}
      <circle cx="60" cy="36" r="24" {...S} />
      <polyline points="40,44 50,28 60,44 70,28 80,44" {...S} stroke="var(--c-cold)" />
    </g>
  ),
  exchanger: () => (
    <g>
      {/* shell and tube: tube side (cold) straight through at y=36, shell side (hot) counter-current at y=54 */}
      <rect x="22" y="10" width="76" height="52" rx="12" {...S} />
      <line x1="46" x2="46" y1="10" y2="62" {...S} strokeWidth={1} strokeDasharray="3 3" />
      <line x1="74" x2="74" y1="10" y2="62" {...S} strokeWidth={1} strokeDasharray="3 3" />
      <line x1="0" x2="120" y1="36" y2="36" {...S} stroke="var(--c-cold)" />
      <line x1="0" x2="120" y1="54" y2="54" {...S} stroke="var(--c-heat)" />
      <polygon points="108,32 100,36 108,40" fill="var(--c-cold)" />
      <polygon points="20,50 12,54 20,58" fill="var(--c-heat)" />
    </g>
  ),
  furnace: () => (
    <g>
      {stub(0, 28)}{stub(92, 120)}
      <path d="M 28 66 L 28 28 L 60 8 L 92 28 L 92 66 Z" {...S} />
      <polyline points="40,34 80,34 40,44 80,44 40,54 80,54" {...S} strokeWidth={1.4} stroke="var(--c-heat)" />
      <path d="M 44 66 Q 48 58 52 66 M 58 66 Q 62 56 66 66 M 72 66 Q 76 58 80 66" {...S} strokeWidth={1.2} stroke="var(--accent)" />
    </g>
  ),
  reactor: () => (
    <g>
      {stub(0, 40)}{stub(80, 120)}
      <path d="M 40 14 Q 40 4 60 4 Q 80 4 80 14 L 80 58 Q 80 68 60 68 Q 40 68 40 58 Z" {...S} />
      <path d="M 44 22 L 76 22 M 44 52 L 76 52" {...S} strokeWidth={1} />
      {/* packed catalyst bed */}
      {[0, 1, 2, 3, 4].map((r) => [0, 1, 2, 3, 4, 5].map((c) => (
        <circle key={`${r}-${c}`} cx={47 + c * 5.2 + (r % 2) * 2.6} cy={26 + r * 5.2} r={1.3} fill="currentColor" fillOpacity={0.7} />
      )))}
    </g>
  ),
  psa: () => (
    <g>
      {stub(0, 30)}{stub(90, 120)}
      <rect x="30" y="8" width="22" height="58" rx="10" {...S} />
      <rect x="68" y="8" width="22" height="58" rx="10" {...S} />
      <line x1="52" x2="68" y1="14" y2="14" {...S} strokeWidth={1.2} />
      <line x1="52" x2="68" y1="60" y2="60" {...S} strokeWidth={1.2} />
      <path d="M 34 24 L 48 24 M 34 32 L 48 32 M 34 40 L 48 40 M 72 24 L 86 24 M 72 32 L 86 32 M 72 40 L 86 40" {...S} strokeWidth={0.9} />
    </g>
  ),
  burner: () => (
    <g>
      {stub(0, 30)}{stub(96, 120)}
      <rect x="30" y="14" width="66" height="44" rx="10" {...S} />
      <path d="M 44 50 Q 40 36 52 30 Q 52 40 58 38 Q 60 26 70 22 Q 70 34 78 36 Q 86 42 80 50 Z" {...S} stroke="var(--accent)" fill="var(--accent)" fillOpacity={0.25} />
    </g>
  ),
}

export function EquipmentSymbol({ symbol }: { symbol: string }) {
  const draw = symbols[symbol] ?? symbols.heater
  return (
    <svg className="pfd-symbol" viewBox="0 0 120 72" width="140" height="84" aria-hidden="true" focusable="false">
      {draw()}
    </svg>
  )
}


