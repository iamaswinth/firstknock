import { cn } from "@/lib/utils"

interface StripedBarProps {
  value: number
  max?: number
  color: string
  className?: string
}

export function StripedBar({ value, max = 100, color, className }: StripedBarProps) {
  const pct = Math.min(100, (value / max) * 100)
  return (
    <div
      className={cn("relative h-2 rounded-full overflow-hidden", className)}
      style={{ background: "var(--fk-well)" }}
    >
      <div
        className="absolute inset-y-0 left-0 rounded-full striped-bar-fill"
        style={{ width: `${pct}%`, background: color }}
      />
    </div>
  )
}
