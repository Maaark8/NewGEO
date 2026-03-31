import { DashboardShell, Panel } from "@/components/dashboard-shell";
import { formatPercent, formatScore } from "@/lib/api";
import { loadWorkspace, type SearchParamsInput } from "@/lib/workspace";

type PageProps = {
  searchParams?: SearchParamsInput;
};

export default async function ComparePage({ searchParams }: PageProps) {
  const { dashboard, projects, selectedProject } = await loadWorkspace(searchParams);
  const recommendation = dashboard.recommendations[0];
  if (!recommendation?.bundle) {
    return (
      <DashboardShell
        active="compare"
        currentPath="/compare"
        selectedProjectId={selectedProject.id}
        projects={projects}
        projectName={dashboard.project.name}
        subtitle="Before/after comparison becomes available once a recommendation has been generated."
      >
        <Panel title="No Recommendation Yet" subtitle="Before / After">
          <p className="panel-subtle">Generate a recommendation to unlock compare mode.</p>
        </Panel>
      </DashboardShell>
    );
  }
  const preview = recommendation.bundle?.preview;

  return (
    <DashboardShell
      active="compare"
      currentPath="/compare"
      selectedProjectId={selectedProject.id}
      projects={projects}
      projectName={dashboard.project.name}
      subtitle="Before/after comparison is built around measurable benchmark deltas and the exact diff that introduced them, so reviewers can inspect gain versus risk quickly."
    >
      <section className="two-col-grid">
        <Panel title="Performance Delta" subtitle="Before / After">
          <div className="metric-line">
            <span>Baseline score</span>
            <strong>{formatScore(preview?.baseline.overall_score ?? 0)}</strong>
          </div>
          <div className="metric-line">
            <span>Projected score</span>
            <strong>{formatScore(preview?.projected.overall_score ?? 0)}</strong>
          </div>
          <div className="metric-line">
            <span>Citation share gain</span>
            <strong>
              {formatPercent((preview?.projected.citation_share ?? 0) - (preview?.baseline.citation_share ?? 0))}
            </strong>
          </div>
          <div className="metric-line">
            <span>Mention rate gain</span>
            <strong>
              {formatPercent((preview?.projected.mention_rate ?? 0) - (preview?.baseline.mention_rate ?? 0))}
            </strong>
          </div>
        </Panel>

        <Panel title="Constraint Checks" subtitle="Safety">
          <div className="data-grid">
            {(recommendation.bundle?.constraint_checks ?? []).map((check) => (
              <article key={check.constraint_id} className="data-row">
                <strong>{check.constraint_kind}</strong>
                <p>{check.message}</p>
                <span className="chip">{check.status}</span>
              </article>
            ))}
          </div>
        </Panel>
      </section>

      <section className="two-col-grid">
        <Panel title="Diff Preview" subtitle="Patch">
          <div className="mono-box">{recommendation.bundle?.diff_markdown}</div>
        </Panel>
        <Panel title="Draft Preview" subtitle="Suggested Rewrite">
          <div className="mono-box">{recommendation.bundle?.rewritten_markdown}</div>
        </Panel>
      </section>
    </DashboardShell>
  );
}
