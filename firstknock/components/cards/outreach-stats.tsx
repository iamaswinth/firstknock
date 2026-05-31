import { CardShell } from "./card-shell"

interface OutreachStatProps {
  count?: number
  delta?: string
}

export function MatchesFoundCard({ count = 0, delta }: OutreachStatProps) {
  return (
    <CardShell title="Matches Found" sub="based on your skill graph">
      <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
        <div style={{
          width: 44, height: 44, borderRadius: 12, flexShrink: 0,
          background: "rgba(239,123,46,0.1)", display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <svg width={20} height={20} viewBox="0 0 20 20" fill="none">
            <circle cx={10} cy={10} r={7} stroke="#ef7b2e" strokeWidth={1.5} />
            <circle cx={10} cy={10} r={3} fill="#ef7b2e" />
            <path d="M10 1v2M10 17v2M1 10h2M17 10h2" stroke="#ef7b2e" strokeWidth={1.5} strokeLinecap="round" />
          </svg>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 44, fontWeight: 700, letterSpacing: "-0.035em", lineHeight: 1, color: "var(--fk-ink)" }}>
            {count}
          </div>
          <div style={{ fontSize: 12.5, color: "var(--fk-ink-3)", marginTop: 4 }}>job matches</div>
        </div>
        {delta && (
          <div style={{ fontSize: 13, fontWeight: 600, color: "#ef7b2e", textAlign: "right" }}>{delta}</div>
        )}
      </div>
    </CardShell>
  )
}

export function EmailsSentCard({ count = 0, delta }: OutreachStatProps) {
  return (
    <CardShell title="Emails Sent" sub="outreach this session">
      <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
        <div style={{
          width: 44, height: 44, borderRadius: 12, flexShrink: 0,
          background: "rgba(47,106,240,0.1)", display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <svg width={20} height={20} viewBox="0 0 20 20" fill="none">
            <rect x={2} y={4} width={16} height={12} rx={2} stroke="var(--fk-blue)" strokeWidth={1.5} />
            <path d="M2 7l8 5 8-5" stroke="var(--fk-blue)" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 44, fontWeight: 700, letterSpacing: "-0.035em", lineHeight: 1, color: "var(--fk-ink)" }}>
            {count}
          </div>
          <div style={{ fontSize: 12.5, color: "var(--fk-ink-3)", marginTop: 4 }}>emails sent</div>
        </div>
        {delta && (
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--fk-blue)", textAlign: "right" }}>{delta}</div>
        )}
      </div>
    </CardShell>
  )
}

export function RepliesCard({ count = 0, delta }: OutreachStatProps) {
  return (
    <CardShell title="Replies" sub="responses received">
      <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
        <div style={{
          width: 44, height: 44, borderRadius: 12, flexShrink: 0,
          background: "var(--fk-green-bg)", display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <svg width={20} height={20} viewBox="0 0 20 20" fill="none">
            <path d="M3 7l7-4 7 4v7a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" stroke="var(--fk-green)" strokeWidth={1.5} strokeLinejoin="round" />
            <path d="M7 18v-6h6v6" stroke="var(--fk-green)" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 44, fontWeight: 700, letterSpacing: "-0.035em", lineHeight: 1, color: "var(--fk-ink)" }}>
            {count}
          </div>
          <div style={{ fontSize: 12.5, color: "var(--fk-ink-3)", marginTop: 4 }}>replies received</div>
        </div>
        {delta && (
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--fk-green)", textAlign: "right" }}>{delta}</div>
        )}
      </div>
    </CardShell>
  )
}
