import type { ProjectEntry, PinnedRepo } from "@/lib/api/types"
import { ProjectCard } from "@/components/cards/project-card"

interface ProjectsSectionProps {
  projects: ProjectEntry[]
  pinnedRepos: PinnedRepo[]
}

function matchRepo(project: ProjectEntry, repos: PinnedRepo[]): PinnedRepo | null {
  return repos.find(r =>
    r.name.toLowerCase() === project.name.toLowerCase() ||
    (project.github_url && project.github_url.endsWith(`/${r.name}`))
  ) ?? null
}

export function ProjectsSection({ projects, pinnedRepos }: ProjectsSectionProps) {
  if (!projects.length) return null

  return (
    <section style={{
      background: "var(--fk-card)",
      border: "1px solid var(--fk-line)",
      borderRadius: "var(--fk-radius-lg)",
      boxShadow: "var(--fk-shadow)",
      overflow: "hidden",
      width: "100%",
    }}>
      <div style={{ padding: "24px 28px 16px", display: "flex", alignItems: "center" }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 600, letterSpacing: "-0.01em", color: "var(--fk-ink)" }}>
            Projects
          </div>
          <div style={{ fontSize: 14, color: "var(--fk-ink-3)", marginTop: 2 }}>
            {projects.length} {projects.length === 1 ? "project" : "projects"} built
          </div>
        </div>
      </div>
      <div style={{
        display: "flex", gap: 12, overflowX: "auto",
        padding: "4px 28px 28px",
        scrollbarWidth: "none",
      }}>
        {projects.map((p) => (
          <ProjectCard
            key={p.name}
            project={p}
            repo={matchRepo(p, pinnedRepos)}
          />
        ))}
      </div>
    </section>
  )
}
