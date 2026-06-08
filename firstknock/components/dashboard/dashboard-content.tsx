"use client"
import { Nav } from "@/components/layout/nav"
import { TitleBar } from "@/components/layout/title-bar"
import { Footer } from "@/components/layout/footer"
import { SkillGraph } from "@/components/graph/skill-graph"
import { Insight } from "@/components/cards/insight"
import { InferredSkills } from "@/components/cards/inferred-skills"
import { CareerTimeline } from "@/components/cards/career-timeline"
import { MetricCard } from "@/components/cards/metric-card"
import { MatchesFoundCard, EmailsSentCard, RepliesCard } from "@/components/cards/outreach-stats"
import { CompaniesSection } from "@/components/sections/companies-section"
import { ProjectsSection } from "@/components/sections/projects-section"
import { useProfile } from "@/lib/api/hooks/use-profile"
import { useSkills } from "@/lib/api/hooks/use-skills"
import { useSkillContext } from "@/lib/api/hooks/use-skill-context"
import { useAnalytics } from "@/lib/api/hooks/use-analytics"
import { useRoles } from "@/lib/api/hooks/use-roles"
import { useCareerTimeline } from "@/lib/api/hooks/use-career-timeline"
import type { PinnedRepo } from "@/lib/api/types"
import { useAuth } from "@/providers/auth-provider"

interface DashboardContentProps {
  userId: string
  onOpenUploadModal?: () => void
  onReingest?: () => void
  onDelete?: () => void
}

export function DashboardContent({ userId, onOpenUploadModal, onReingest, onDelete }: DashboardContentProps) {
  const { resumeName } = useAuth()
  const profile      = useProfile(userId)
  const skills       = useSkills(userId)
  const skillContext = useSkillContext(userId)
  const analytics    = useAnalytics(userId)
  const roles        = useRoles(userId)
  const careerTl     = useCareerTimeline(userId)

  if (profile.isLoading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--fk-page)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 18, height: 18, borderRadius: "50%", border: "2px solid var(--fk-ink)", borderTopColor: "transparent", animation: "spin 0.7s linear infinite" }} />
          <p style={{ fontSize: 15, color: "var(--fk-ink-3)" }}>Loading your profile…</p>
        </div>
      </div>
    )
  }

  if (profile.isError || !profile.data) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--fk-page)" }}>
        <div style={{ textAlign: "center" }}>
          <p style={{ fontSize: 15, color: "var(--fk-ink-3)", marginBottom: 12 }}>Could not load your profile.</p>
          <button
            onClick={() => profile.refetch()}
            style={{ fontSize: 13, color: "var(--fk-brand)", background: "none", border: "none", cursor: "pointer", textDecoration: "underline" }}
          >
            Try again
          </button>
        </div>
      </div>
    )
  }

  const pData = profile.data
  const sData = skills.data
  const gData = skillContext.data
  const aData = analytics.data
  const rData = roles.data

  const pinnedRepos: PinnedRepo[] = (pData as { enriched?: { github?: { pinned_repos?: PinnedRepo[] } } })
    ?.enriched?.github?.pinned_repos ?? []

  return (
    <div
      style={{
        background: "var(--fk-page)",
        minHeight: "100vh",
        width: "100%",
        maxWidth: 1280,
        margin: "0 auto",
        padding: "24px 48px 40px",
        display: "flex",
        flexDirection: "column",
      }}
    >
        <Nav name={pData?.name ?? "AD"} profilePictureUrl={pData?.profile_picture_url} onUpload={onOpenUploadModal} />

        <TitleBar
          syncDate={new Date().toLocaleDateString("en-US", { month: "short", day: "numeric" })}
          resumeName={resumeName ?? undefined}
          totalMonths={pData?.total_experience_months}
          onUpload={onOpenUploadModal}
          onReingest={onReingest}
          onDelete={onDelete}
        />

        {/* Bento grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(12, 1fr)", gap: 24 }}>

          {/* Row 1 — Graph + Insight (full height, no SkillComposition) */}
          <div style={{ gridColumn: "span 8", display: "flex" }}>
            {gData ? (
              <SkillGraph nodes={gData.nodes} links={gData.links} />
            ) : (
              <GraphPlaceholder />
            )}
          </div>
          <div style={{ gridColumn: "span 4", display: "flex" }}>
            <Insight
              bridgeSkills={aData?.bridge_skills ?? null}
              roles={rData?.roles ?? null}
            />
          </div>

          {/* Row 2 — Companies */}
          <div style={{ gridColumn: "span 12", display: "flex" }}>
            <CompaniesSection
              events={careerTl.data?.events ?? []}
              resume_experience={pData?.experience ?? []}
            />
          </div>

          {/* Row 3 — Projects */}
          <div style={{ gridColumn: "span 12", display: "flex" }}>
            <ProjectsSection
              projects={pData?.projects ?? []}
              pinnedRepos={pinnedRepos}
            />
          </div>

          {/* Row 4 — Inferred Skills */}
          <div style={{ gridColumn: "span 12", display: "flex" }}>
            <InferredSkills skills={aData?.inferred_skills ?? []} />
          </div>

          {/* Row 5 — Career Timeline */}
          <div style={{ gridColumn: "span 12", display: "flex" }}>
            <CareerTimeline
              events={careerTl.data?.events ?? []}
              totalMonths={careerTl.data?.total_experience_months}
            />
          </div>

          {/* Row 6 — Outreach funnel */}
          <div style={{ gridColumn: "span 4", display: "flex" }}>
            <MatchesFoundCard />
          </div>
          <div style={{ gridColumn: "span 4", display: "flex" }}>
            <EmailsSentCard />
          </div>
          <div style={{ gridColumn: "span 4", display: "flex" }}>
            <RepliesCard />
          </div>

          {/* Row 7 — Metrics */}
          <div style={{ gridColumn: "span 6", display: "flex" }}>
            <MetricCard
              title="Skills Mapped"
              value={String(sData?.total ?? 0)}
              peakLabel="Top"
              peak={aData?.skill_communities?.[0]?.name ?? "—"}
              delta={`+${sData?.inferred.length ?? 0} inferred`}
              color="green"
              sub="across communities"
            />
          </div>
          <div style={{ gridColumn: "span 6", display: "flex" }}>
            <MetricCard
              title="GitHub Reach"
              value={String(pData?.github_followers ?? 0)}
              peakLabel="Peak"
              peak={pinnedRepos.length > 0 ? pinnedRepos[0].name : "—"}
              delta={`${pData?.public_repos ?? 0} repos`}
              color="blue"
              sub="public repos"
            />
          </div>
        </div>

        <Footer
          userId={userId}
          skillCount={sData?.total}
          edgeCount={gData?.links.length}
        />
    </div>
  )
}

function GraphPlaceholder() {
  return (
    <div style={{
      flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
      background: "var(--fk-card)", border: "1px solid var(--fk-line)",
      borderRadius: "var(--fk-radius-lg)", boxShadow: "var(--fk-shadow)", minHeight: 560,
    }}>
      <p style={{ fontSize: 14, color: "var(--fk-ink-4)" }}>
        Graph not yet built — re-ingest to generate.
      </p>
    </div>
  )
}
