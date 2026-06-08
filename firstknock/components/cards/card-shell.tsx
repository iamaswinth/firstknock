import { MoreHorizontal } from "lucide-react"

interface CardShellProps {
  title?: string
  sub?: string
  right?: React.ReactNode
  children: React.ReactNode
  className?: string
  id?: string
  style?: React.CSSProperties
}

export function CardShell({ title, sub, right, children, className, id, style }: CardShellProps) {
  return (
    <section
      id={id}
      className={className}
      style={{
        background: "var(--fk-card)",
        border: "1px solid var(--fk-line)",
        borderRadius: "var(--fk-radius-lg)",
        boxShadow: "var(--fk-shadow)",
        display: "flex",
        flexDirection: "column",
        minWidth: 0,
        overflow: "hidden",
        flex: "1 1 auto",
        width: "100%",
        ...style,
      }}
    >
      {(title || right) && (
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "24px 28px 0" }}>
          {title && (
            <div>
              <div style={{ fontSize: 20, fontWeight: 600, letterSpacing: "-0.01em", color: "var(--fk-ink)" }}>
                {title}
              </div>
              {sub && (
                <div style={{ fontSize: 16, color: "var(--fk-ink-3)", marginTop: 2 }}>{sub}</div>
              )}
            </div>
          )}
          <div style={{ flex: 1 }} />
          {right}
          <button style={{
            width: 34, height: 34, borderRadius: "50%",
            border: "1px solid var(--fk-line-2)",
            color: "var(--fk-ink-3)",
            display: "grid", placeItems: "center",
            cursor: "pointer", background: "transparent", flexShrink: 0,
          }}>
            <MoreHorizontal size={18} />
          </button>
        </div>
      )}
      <div style={{ padding: "24px 28px 28px" }}>{children}</div>
    </section>
  )
}
