"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { initials } from "@/lib/utils"
import { useAuth } from "@/providers/auth-provider"

const NAV_LINKS = [
  { label: "Dashboard",  href: "/dashboard" },
  { label: "Matches",    href: "/matches"   },
  { label: "Startups",   href: "/startups"  },
  { label: "Outreach",   href: "/outreach"  },
  { label: "Analytics",  href: "/analytics" },
]

interface NavProps {
  name: string
  profilePictureUrl?: string | null
  onUpload?: () => void
}

export function Nav({ name, profilePictureUrl, onUpload }: NavProps) {
  const { logout } = useAuth()
  const pathname = usePathname()

  return (
    <nav style={{ display: "flex", alignItems: "center", gap: 18, height: 56 }}>
      {/* Brand */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{
          width: 30, height: 30, borderRadius: 9,
          background: "linear-gradient(150deg,#f7943f,#ec6a1e)",
          display: "grid", placeItems: "center", color: "#fff",
          boxShadow: "0 2px 6px rgba(236,106,30,0.35)",
        }}>
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
            <path d="M12 3.5l7 4v9l-7 4-7-4v-9l7-4Z" stroke="#fff" strokeWidth="1.8" strokeLinejoin="round" />
          </svg>
        </div>
        <span style={{ fontSize: 18, fontWeight: 600, letterSpacing: "-0.01em" }}>FirstKnock</span>
      </div>

      {/* Links */}
      <div style={{ display: "flex", alignItems: "center", gap: 2, margin: "0 auto" }}>
        {NAV_LINKS.map(({ label, href }) => {
          const active = pathname === href
          return (
            <Link key={href} href={href} style={{
              padding: "8px 14px", borderRadius: 9,
              fontSize: 14, fontWeight: 500,
              color: active ? "#fff" : "var(--fk-ink-3)",
              background: active ? "var(--fk-ink)" : "transparent",
              transition: "background .14s, color .14s",
              textDecoration: "none",
            }}>
              {label}
            </Link>
          )
        })}
      </div>

      {/* Right cluster */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {/* Search */}
        <button style={{
          width: 40, height: 40, borderRadius: "50%",
          border: "1px solid var(--fk-line-2)", background: "var(--fk-card)",
          display: "grid", placeItems: "center", color: "var(--fk-ink-2)", cursor: "pointer",
        }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8" />
            <path d="m20 20-3-3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        </button>

        {/* Bell */}
        <button style={{
          width: 40, height: 40, borderRadius: "50%",
          border: "1px solid var(--fk-line-2)", background: "var(--fk-card)",
          display: "grid", placeItems: "center", color: "var(--fk-ink-2)", cursor: "pointer",
          position: "relative",
        }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
            <path d="M10 20a2 2 0 0 0 4 0" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
          </svg>
          <span style={{
            position: "absolute", top: 9, right: 10,
            width: 7, height: 7, borderRadius: "50%",
            background: "var(--fk-brand)", border: "1.5px solid var(--fk-page)",
          }} />
        </button>

        {/* Avatar + dropdown trigger */}
        <div style={{ position: "relative", display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{
            width: 42, height: 42, borderRadius: "50%", padding: 2,
            background: "conic-gradient(from 200deg,#f7943f,#e6457f,#2f6af0,#14a05a,#f7943f)",
            flexShrink: 0,
          }}>
            {profilePictureUrl ? (
              <img
                src={profilePictureUrl}
                alt={name || "Profile"}
                width={38}
                height={38}

                style={{
                  display: "block",
                  width: "100%", height: "100%",
                  borderRadius: "50%",
                  objectFit: "cover",
                  border: "2px solid var(--fk-page)",
                }}
              />
            ) : (
              <span style={{
                display: "grid", placeItems: "center",
                width: "100%", height: "100%", borderRadius: "50%",
                background: "var(--fk-ink)", color: "#fff",
                fontWeight: 700, fontSize: 13,
                border: "2px solid var(--fk-page)",
              }}>
                {initials(name || "AD")}
              </span>
            )}
          </div>

          {/* Sign out */}
          <button
            onClick={logout}
            title="Sign out"
            style={{
              height: 30, padding: "0 12px",
              border: "1px solid var(--fk-line-2)",
              borderRadius: 8,
              background: "var(--fk-card)",
              fontSize: 12, fontWeight: 500,
              color: "var(--fk-ink-3)",
              cursor: "pointer",
              transition: "background .14s, color .14s",
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = "var(--fk-card-2)"; e.currentTarget.style.color = "var(--fk-ink)" }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "var(--fk-card)"; e.currentTarget.style.color = "var(--fk-ink-3)" }}
          >
            Sign out
          </button>
        </div>
      </div>
    </nav>
  )
}
