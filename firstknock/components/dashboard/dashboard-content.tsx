"use client"
import { Nav } from "@/components/layout/nav"
import { TitleBar } from "@/components/layout/title-bar"
import { Footer } from "@/components/layout/footer"
import { SkillGraph } from "@/components/graph/skill-graph"
import { SkillComposition } from "@/components/cards/skill-composition"
import { Insight } from "@/components/cards/insight"
import { InferredSkills } from "@/components/cards/inferred-skills"
import { RoleFit } from "@/components/cards/role-fit"
import { CareerTimeline } from "@/components/cards/career-timeline"
import { MetricCard } from "@/components/cards/metric-card"
import { MatchesFoundCard, EmailsSentCard, RepliesCard } from "@/components/cards/outreach-stats"
import { useProfile } from "@/lib/api/hooks/use-profile"
import { useSkills } from "@/lib/api/hooks/use-skills"
import { useGraph } from "@/lib/api/hooks/use-graph"
import { useAnalytics } from "@/lib/api/hooks/use-analytics"
import { useRoles } from "@/lib/api/hooks/use-roles"
import { useCareerTimeline } from "@/lib/api/hooks/use-career-timeline"

interface DashboardContentProps {
  userId: string
  onOpenUploadModal?: () => void
  onReingest?: () => void
  onDelete?: () => void
}

export function DashboardContent({ userId, onOpenUploadModal, onReingest, onDelete }: DashboardContentProps) {
  const profile      = useProfile(userId)
  const skills       = useSkills(userId)
  const graph        = useGraph(userId)
  const analytics    = useAnalytics(userId)
  const roles        = useRoles(userId)
  const careerTl     = useCareerTimeline(userId)

  const isLoading = profile.isLoading || skills.isLoading || analytics.isLoading

  if (isLoading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--fk-page)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 18, height: 18, borderRadius: "50%", border: "2px solid var(--fk-ink)", borderTopColor: "transparent", animation: "spin 0.7s linear infinite" }} />
          <p style={{ fontSize: 14, color: "var(--fk-ink-3)" }}>Loading your profile…</p>
        </div>
      </div>
    )
  }

  const pData = profile.data
  const sData = skills.data
  const gData = graph.data
  const aData = analytics.data
  const rData = roles.data

  const pinnedRepos = (pData as { enriched?: { github?: { pinned_repos?: unknown[] } } })
    ?.enriched?.github?.pinned_repos ?? []

  return (
    <div
      style={{
        background: "var(--fk-page)",
        minHeight: "100vh",
        width: "100%",
        maxWidth: 1500,
        margin: "0 auto",
        padding: "18px 22px 26px",
        display: "flex",
        flexDirection: "column",
      }}
    >
        <Nav name={pData?.name ?? "AD"} profilePictureUrl={pData?.profile_picture_url} onUpload={onOpenUploadModal} />

        <TitleBar
          syncDate={new Date().toLocaleDateString("en-US", { month: "short", day: "numeric" })}
          totalMonths={pData?.total_experience_months}
          onUpload={onOpenUploadModal}
          onReingest={onReingest}
          onDelete={onDelete}
        />

        {/* Bento grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(12, 1fr)", gap: 16 }}>

          {/* Row 1 */}
          <div style={{ gridColumn: "span 8", display: "flex" }}>
            {gData ? (
              <SkillGraph nodes={gData.nodes} links={gData.links} communities={gData.communities} />
            ) : (
              <GraphPlaceholder />
            )}
          </div>
          <div style={{ gridColumn: "span 4", display: "flex", flexDirection: "column", gap: 16 }}>
            {sData ? <SkillComposition skills={sData} /> : <CardSkeleton />}
            <div style={{ flex: 1, display: "flex" }}>
              <Insight bridgeSkills={aData?.bridge_skills ?? null} />
            </div>
          </div>

          {/* Row 2 */}
          <div style={{ gridColumn: "span 6", display: "flex" }}>
            <InferredSkills skills={aData?.inferred_skills ?? []} />
          </div>
          <div style={{ gridColumn: "span 6", display: "flex" }}>
            <RoleFit roles={rData?.roles ?? []} />
          </div>

          {/* Row 3 */}
          <div style={{ gridColumn: "span 12", display: "flex" }}>
            <CareerTimeline
              events={careerTl.data?.events ?? []}
              totalMonths={careerTl.data?.total_experience_months}
            />
          </div>

          {/* Row 4 – Outreach funnel */}
          <div style={{ gridColumn: "span 4", display: "flex" }}>
            <MatchesFoundCard />
          </div>
          <div style={{ gridColumn: "span 4", display: "flex" }}>
            <EmailsSentCard />
          </div>
          <div style={{ gridColumn: "span 4", display: "flex" }}>
            <RepliesCard />
          </div>

          {/* Row 5 */}
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
              peak={pinnedRepos.length > 0 ? (pinnedRepos[0] as { name: string }).name : "—"}
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

function CardSkeleton() {
  return (
    <div style={{
      flex: 1, height: 160, borderRadius: "var(--fk-radius-lg)",
      background: "var(--fk-card-2)", border: "1px solid var(--fk-line)",
      animation: "pulse 2s cubic-bezier(0.4,0,0.6,1) infinite",
    }} />
  )
}
