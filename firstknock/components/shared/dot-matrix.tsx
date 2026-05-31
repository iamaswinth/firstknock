// Dot-matrix column chart matching the reference design exactly
// 7px dots, 5px gaps, columns aligned to flex-end

interface DotMatrixProps {
  values?: number[]
  color?: "green" | "blue"
  peakCol?: number
}

const DEFAULT_COLS = [2, 3, 4, 3, 5, 6, 8, 6, 4, 3, 4, 3, 2]
const MAX_ROWS = 8
const DOT = 7
const GAP = 5

export function DotMatrix({ values = DEFAULT_COLS, color = "green", peakCol = 6 }: DotMatrixProps) {
  const onClass = color === "green" ? "var(--fk-green)" : "var(--fk-blue)"
  const maxVal = Math.max(...values)

  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: GAP, height: MAX_ROWS * (DOT + GAP) - GAP }}>
      {values.map((h, ci) => {
        const filled = maxVal > 0 ? Math.round((h / maxVal) * MAX_ROWS) : 0
        const isPeak = ci === peakCol
        return (
          <div key={ci} style={{ display: "flex", flexDirection: "column-reverse", gap: GAP }}>
            {Array.from({ length: MAX_ROWS }).map((_, ri) => {
              const isOn = ri < filled
              return (
                <span key={ri} style={{
                  display: "block",
                  width: DOT, height: DOT, borderRadius: "50%",
                  background: isOn ? onClass : "var(--fk-line-2)",
                  opacity: isOn && !isPeak ? 0.45 : 1,
                }} />
              )
            })}
          </div>
        )
      })}
    </div>
  )
}
