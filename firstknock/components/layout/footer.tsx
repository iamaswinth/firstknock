interface FooterProps {
  userId?: string
  skillCount?: number
  edgeCount?: number
}

export function Footer({ userId, skillCount, edgeCount }: FooterProps) {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 12,
      paddingTop: 8, fontSize: 12, color: "var(--fk-ink-4)",
      fontFamily: "var(--font-geist-mono,monospace)",
    }}>
      <span>FirstKnock · resume → knowledge graph</span>
      {userId && (
        <span style={{ marginLeft: "auto" }}>
          user_id {userId.slice(0, 8)}
          {skillCount !== undefined && ` · ${skillCount} skills`}
          {edgeCount !== undefined && ` · ${edgeCount} edges`}
        </span>
      )}
    </div>
  )
}
