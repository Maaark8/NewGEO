import { DashboardShell, MetricCard, MiniTrend, Panel, StatusPill } from "@/components/dashboard-shell";
import { formatPercent, formatScore } from "@/lib/api";
import { loadWorkspace, type SearchParamsInput } from "@/lib/workspace";

type PageProps = {
  searchParams?: SearchParamsInput;
};

export default async function OverviewPage({ searchParams }: PageProps) {
  const { dashboard, projects, selectedProject } = await loadWorkspace(searchParams);
  const trendValues = dashboard.score_snapshots.map((snapshot) => snapshot.metrics.overall_score);

  return (
    <DashboardShell
      active="overview"
      currentPath="/"
      selectedProjectId={selectedProject.id}
      projects={projects}
      projectName={dashboard.project.name}
      subtitle="Track how your docs show up in LLM-generated answers, keep meaning stable with context packs, and review projected lift before publishing."
    >
      <section className="metrics-grid">
        <MetricCard
          label="Tracked Pages"
          value={String(dashboard.summary.page_count)}
          detail="Docs and articles currently monitored for AI visibility."
        />
        <MetricCard
          label="Context Packs"
          value={String(dashboard.summary.context_pack_count)}
          tone="gold"
          detail="Read-only context bundles that protect meaning during optimization."
        />
        <MetricCard
          label="Benchmark Runs"
          value={String(dashboard.summary.run_count)}
          tone="sky"
          detail="Comparable benchmark runs plus non-comparable live spot checks."
        />
        <MetricCard
          label="Recommendations"
          value={String(dashboard.summary.recommendation_count)}
          tone="coral"
          detail="Human-review suggestions with diffs, rationales, and constraint checks."
        />
      </section>

      <section className="two-col-grid">
        <Panel title="Visibility Trend" subtitle="Momentum">
          <MiniTrend values={trendValues} />
          <p className="panel-subtle">Recent comparable score snapshots show steady lift on the main setup guide.</p>
        </Panel>

        <Panel title="Latest Recommendation" subtitle="Review Queue">
          {dashboard.recommendations.slice(0, 1).map((recommendation) => (
            <div key={recommendation.id} className="data-row">
              <div className="row-meta">
                <StatusPill value={recommendation.status} />
                <span className="chip">
                  Confidence {formatPercent(recommendation.bundle?.confidence ?? 0)}
                </span>
                <span className="chip">
                  Delta <span className="delta-positive">+{formatScore(recommendation.bundle?.preview.score_delta ?? 0)}</span>
                </span>
              </div>
              <h4>Context-aware rewrite draft</h4>
              <p>{recommendation.bundle?.rationale[0]}</p>
              <div className="chip-row">
                {(recommendation.bundle?.supporting_context_used ?? []).map((item) => (
                  <span key={item} className="chip">
                    {item}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </Panel>
      </section>

      <section className="two-col-grid">
        <Panel title="Tracked Pages" subtitle="Coverage">
          <div className="data-grid">
            {dashboard.pages.map((page) => (
              <article key={page.id} className="data-row">
                <div className="row-meta">
                  <StatusPill value={page.status} />
                  <span className="chip">Score {formatScore(page.latest_score)}</span>
                </div>
                <h4>{page.title}</h4>
                <p>{page.url}</p>
              </article>
            ))}
          </div>
        </Panel>

        <Panel title="Recent Benchmark" subtitle="Top Observation">
          {dashboard.runs.slice(0, 1).map((run) => (
            <div key={run.id} className="data-row">
              <div className="row-meta">
                <StatusPill value={run.status} />
                <span className="chip">{run.engine_name}</span>
                <span className="chip">{run.run_kind}</span>
              </div>
              {run.observations.map((observation) => (
                <div key={observation.page_id}>
                  <h4>Page {observation.page_id}</h4>
                  <div className="metric-line">
                    <span>Mention rate</span>
                    <strong>{formatPercent(observation.metrics.mention_rate)}</strong>
                  </div>
                  <div className="metric-line">
                    <span>Citation share</span>
                    <strong>{formatPercent(observation.metrics.citation_share)}</strong>
                  </div>
                  <div className="metric-line">
                    <span>Position</span>
                    <strong>{observation.metrics.answer_position.toFixed(1)}</strong>
                  </div>
                </div>
              ))}
            </div>
          ))}
        </Panel>
      </section>
    </DashboardShell>
  );
}
