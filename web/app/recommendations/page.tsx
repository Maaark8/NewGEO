import { DashboardShell, Panel, StatusPill } from "@/components/dashboard-shell";
import { formatPercent, formatScore } from "@/lib/api";
import { loadWorkspace, type SearchParamsInput } from "@/lib/workspace";

type PageProps = {
  searchParams?: SearchParamsInput;
};

export default async function RecommendationsPage({ searchParams }: PageProps) {
  const { dashboard, projects, selectedProject } = await loadWorkspace(searchParams);

  return (
    <DashboardShell
      active="recommendations"
      currentPath="/recommendations"
      selectedProjectId={selectedProject.id}
      projects={projects}
      projectName={dashboard.project.name}
      subtitle="Recommendations stay human-review-first: the system shows rationale, context used, projected lift, and every constraint check before approval."
    >
      <Panel title="Recommendation Queue" subtitle="Review Queue">
        <div className="data-grid">
          {dashboard.recommendations.map((recommendation) => (
            <article key={recommendation.id} className="data-row">
              <div className="row-meta">
                <StatusPill value={recommendation.status} />
                <span className="chip">Confidence {formatPercent(recommendation.bundle?.confidence ?? 0)}</span>
                <span className="chip">
                  Lift <span className="delta-positive">+{formatScore(recommendation.bundle?.preview.score_delta ?? 0)}</span>
                </span>
              </div>
              <h4>{recommendation.id}</h4>
              <div className="chip-row">
                {(recommendation.bundle?.supporting_context_used ?? []).map((item) => (
                  <span key={item} className="chip">
                    {item}
                  </span>
                ))}
              </div>
              <ul className="stack-list">
                {(recommendation.bundle?.rationale ?? []).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </Panel>
    </DashboardShell>
  );
}
