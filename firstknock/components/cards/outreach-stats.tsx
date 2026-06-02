import { Crosshair, Mail, Home } from "lucide-react"
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
          <Crosshair size={20} strokeWidth={1.5} color="#ef7b2e" />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 44, fontWeight: 700, letterSpacing: "-0.035em", lineHeight: 1, color: "var(--fk-ink)" }}>
            {count}
          </div>
          <div style={{ fontSize: 13, color: "var(--fk-ink-3)", marginTop: 4 }}>job matches</div>
        </div>
        {delta && (
          <div style={{ fontSize: 14, fontWeight: 600, color: "#ef7b2e", textAlign: "right" }}>{delta}</div>
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
          <Mail size={20} strokeWidth={1.5} color="var(--fk-blue)" />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 44, fontWeight: 700, letterSpacing: "-0.035em", lineHeight: 1, color: "var(--fk-ink)" }}>
            {count}
          </div>
          <div style={{ fontSize: 13, color: "var(--fk-ink-3)", marginTop: 4 }}>emails sent</div>
        </div>
        {delta && (
          <div style={{ fontSize: 14, fontWeight: 600, color: "var(--fk-blue)", textAlign: "right" }}>{delta}</div>
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
          <Home size={20} strokeWidth={1.5} color="var(--fk-green)" />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 44, fontWeight: 700, letterSpacing: "-0.035em", lineHeight: 1, color: "var(--fk-ink)" }}>
            {count}
          </div>
          <div style={{ fontSize: 13, color: "var(--fk-ink-3)", marginTop: 4 }}>replies received</div>
        </div>
        {delta && (
          <div style={{ fontSize: 14, fontWeight: 600, color: "var(--fk-green)", textAlign: "right" }}>{delta}</div>
        )}
      </div>
    </CardShell>
  )
}
