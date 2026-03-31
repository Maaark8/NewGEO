import { DashboardShell, Panel } from "@/components/dashboard-shell";
import { loadWorkspace, type SearchParamsInput } from "@/lib/workspace";

type PageProps = {
  searchParams?: SearchParamsInput;
};

export default async function QueriesPage({ searchParams }: PageProps) {
  const { dashboard, projects, selectedProject } = await loadWorkspace(searchParams);

  return (
    <DashboardShell
      active="queries"
      currentPath="/queries"
      selectedProjectId={selectedProject.id}
      projects={projects}
      projectName={dashboard.project.name}
      subtitle="Query clusters group real informational demand so visibility can be measured by topic, not only by page."
    >
      <Panel title="Query Clusters" subtitle="Demand Map">
        <div className="data-grid">
          {dashboard.query_clusters.map((cluster) => (
            <article key={cluster.id} className="data-row">
              <h4>{cluster.name}</h4>
              <p>{cluster.description}</p>
              <div className="chip-row">
                {cluster.queries.map((query) => (
                  <span key={query.id} className="chip">
                    {query.text}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </div>
      </Panel>
    </DashboardShell>
  );
}
