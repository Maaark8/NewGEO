import { DashboardShell, Panel, StatusPill } from "@/components/dashboard-shell";
import { formatPercent, formatScore } from "@/lib/api";
import { loadWorkspace, type SearchParamsInput } from "@/lib/workspace";

type PageProps = {
  searchParams?: SearchParamsInput;
};

export default async function RunsPage({ searchParams }: PageProps) {
  const { dashboard, projects, selectedProject } = await loadWorkspace(searchParams);

  return (
    <DashboardShell
      active="runs"
      currentPath="/runs"
      selectedProjectId={selectedProject.id}
      projects={projects}
      projectName={dashboard.project.name}
      subtitle="Benchmark runs use fixed prompts for comparable scoring, while live spot checks are kept visible but separate so noisy data never pollutes trend lines."
    >
      <Panel title="Run Feed" subtitle="Benchmark Feed">
        <div className="data-grid">
          {dashboard.runs.map((run) => (
            <article key={run.id} className="data-row">
              <div className="row-meta">
                <StatusPill value={run.status} />
                <span className="chip">{run.engine_name}</span>
                <span className="chip">{run.run_kind}</span>
              </div>
              <h4>{run.id}</h4>
              {run.observations.map((observation) => (
                <div key={observation.page_id}>
                  <div className="metric-line">
                    <span>{observation.page_id} overall</span>
                    <strong>{formatScore(observation.metrics.overall_score)}</strong>
                  </div>
                  <div className="metric-line">
                    <span>Mention rate</span>
                    <strong>{formatPercent(observation.metrics.mention_rate)}</strong>
                  </div>
                  <div className="metric-line">
                    <span>Citation share</span>
                    <strong>{formatPercent(observation.metrics.citation_share)}</strong>
                  </div>
                </div>
              ))}
            </article>
          ))}
        </div>
      </Panel>
    </DashboardShell>
  );
}
