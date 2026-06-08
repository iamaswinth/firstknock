"use client";
import { SignIn } from "@clerk/nextjs";

const INSIGHT_GRADIENT =
  "radial-gradient(120% 140% at 85% 10%, #f7a23f 0%, #ed6aa6 32%, #7f7be0 60%, #2f5fd0 80%, #14245e 100%)";

export default function LoginPage() {
  return (
    <>
      <style>{`
        .fk-login-root {
          display: flex;
          min-height: 100vh;
          background: #f0f0f3;
        }

        /* Left — white auth column, 50% */
        .fk-auth-col {
          flex: 0 0 50%;
          background: #ffffff;
          display: flex;
          flex-direction: column;
          align-items: center;          /* centres content horizontally */
          justify-content: space-between;
          padding: 40px 32px;
          min-height: 100vh;
          box-sizing: border-box;
        }

        /* logo row — full width, pushed to left edge of column */
        .fk-auth-top {
          width: 100%;
        }

        /* footer spans full max-width block */
        .fk-auth-footer {
          width: 100%;
          max-width: 380px;
        }

        /* form block is also constrained + centred */
        .fk-auth-form {
          width: 100%;
          max-width: 380px;
        }

        /* Right — white background, 50%, holds the floating card */
        .fk-brand-col {
          flex: 0 0 50%;
          background: #ffffff;
          display: flex;
          justify-content: center;   /* centres the card horizontally */
          align-items: stretch;
          padding: 20px 20px 20px 0;
          box-sizing: border-box;
        }

        /* Inner floating gradient card */
        .fk-brand-card {
          flex: 1;
          border-radius: 20px;
          background: ${INSIGHT_GRADIENT};
          border: 1.5px solid rgba(0,0,0,0.35);
          display: flex;
          flex-direction: column;
          justify-content: flex-start;
          padding: 44px;
          overflow: hidden;
        }

        @media (max-width: 860px) {
          .fk-brand-col  { display: none; }
          .fk-auth-col   { flex: 1; min-height: 100vh; padding: 40px 24px; }
          .fk-login-root { background: #fff; }
        }
      `}</style>

      <div className="fk-login-root">
        {/* ─── Left: Auth ─────────────────────────────── */}
        <div className="fk-auth-col">
          {/* Top: Logo — full max-width row */}
          <div
            className="fk-auth-top"
            style={{ display: "flex", alignItems: "center", gap: 9 }}
          >
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: 12,
                background: "linear-gradient(135deg,#f7943f,#ec6a1e)",
                display: "grid",
                placeItems: "center",
                boxShadow: "0 2px 10px rgba(236,106,30,0.38)",
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path
                  d="M12 3.5l7 4v9l-7 4-7-4v-9l7-4Z"
                  stroke="#fff"
                  strokeWidth="2.1"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <span
              style={{
                fontWeight: 700,
                fontSize: 22,
                color: "#0d0d0f",
                letterSpacing: "-0.02em",
              }}
            >
              FirstKnock
            </span>
          </div>

          {/* Middle: Form — centred block */}
          <div className="fk-auth-form">
            <h1
              style={{
                fontSize: 28,
                fontWeight: 700,
                letterSpacing: "-0.03em",
                color: "#0a0a0b",
                margin: "0 0 6px",
              }}
            >
              Welcome Back
            </h1>
            <p
              style={{
                fontSize: 14,
                color: "#9a9a9a",
                margin: "0 0 28px",
                lineHeight: 1.5,
              }}
            >
              Sign in to continue your job search.
            </p>
            <SignIn routing="path" path="/login" />
          </div>

          {/* Bottom: Footer */}
          <div
            className="fk-auth-footer"
            style={{ display: "flex", justifyContent: "space-between" }}
          >
            <span style={{ fontSize: 12, color: "#c0c0c0" }}>
              © 2025 FirstKnock
            </span>
            <a
              href="#"
              style={{ fontSize: 12, color: "#c0c0c0", textDecoration: "none" }}
            >
              Privacy Policy
            </a>
          </div>
        </div>

        {/* ─── Right: Floating Gradient Card ──────────── */}
        <div className="fk-brand-col">
          <div className="fk-brand-card">
            {/* Top: Headline — left-aligned text, card padded */}
            <div style={{ padding: "44px " }}>
              <h2
                style={{
                  fontSize: 32,
                  fontWeight: 700,
                  lineHeight: 1.15,
                  letterSpacing: "-0.035em",
                  color: "#ffffff",
                  margin: "0 0 14px",
                }}
              >
                Turn your résumé into
                <br />
                your unfair advantage.
              </h2>
              <p
                style={{
                  fontSize: 14,
                  color: "rgba(255,255,255,0.68)",
                  lineHeight: 1.65,
                  margin: 0,
                }}
              >
                Log in to access your knowledge graph, matched startups, and
                personalized outreach — all in one place.
              </p>
            </div>

            {/* Bottom: Dashboard screenshot — centred horizontally */}
            <div style={{ width: "92%", margin: "0 auto" }}>
              <img
                src="/dashboard-preview.png"
                alt="FirstKnock dashboard"
                style={{
                  width: "100%",
                  borderRadius: "12px ",
                  display: "block",
                }}
              />
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
