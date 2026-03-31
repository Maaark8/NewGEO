import { DashboardShell, Panel, StatusPill } from "@/components/dashboard-shell";
import { formatScore } from "@/lib/api";
import { loadWorkspace, type SearchParamsInput } from "@/lib/workspace";

type PageProps = {
  searchParams?: SearchParamsInput;
};

export default async function PagesPage({ searchParams }: PageProps) {
  const { dashboard, projects, selectedProject } = await loadWorkspace(searchParams);

  return (
    <DashboardShell
      active="pages"
      currentPath="/pages"
      selectedProjectId={selectedProject.id}
      projects={projects}
      projectName={dashboard.project.name}
      subtitle="The page inventory is organized around docs/article content, latest benchmark score, and which pages are eligible for context-aware optimization."
    >
      <Panel title="Page Inventory" subtitle="Content Surface">
        <div className="data-grid">
          {dashboard.pages.map((page) => (
            <article key={page.id} className="data-row">
              <div className="row-meta">
                <StatusPill value={page.status} />
                <span className="chip">{page.content_type.replaceAll("_", " ")}</span>
                <span className="chip">Score {formatScore(page.latest_score)}</span>
              </div>
              <h4>{page.title}</h4>
              <p>{page.url}</p>
              <p className="panel-subtle">
                {dashboard.context_packs.some((pack) => pack.page_id === page.id)
                  ? "Context pack attached"
                  : "No context pack attached yet"}
              </p>
            </article>
          ))}
        </div>
      </Panel>
    </DashboardShell>
  );
}
