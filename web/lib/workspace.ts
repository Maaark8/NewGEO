import type { DashboardData, ProjectSummary } from "./api";
import { getDashboard, getProjects } from "./api";
import { sampleProjects } from "./sample-data";

type SearchValue = string | string[] | undefined;
export type SearchParamsInput = Promise<Record<string, SearchValue>> | undefined;

export type WorkspaceState = {
  projects: ProjectSummary[];
  selectedProject: ProjectSummary;
  dashboard: DashboardData;
};

export function resolveQueryValue(value: SearchValue): string | undefined {
  if (Array.isArray(value)) {
    return value[0];
  }
  return value;
}

export async function loadWorkspace(
  searchParams?: SearchParamsInput | Record<string, SearchValue>,
): Promise<WorkspaceState> {
  const resolvedParams = await Promise.resolve(searchParams ?? {});
  const projects = await getProjects();
  const fallbackProjects = projects.length > 0 ? projects : sampleProjects;
  const requestedProjectId = resolveQueryValue(resolvedParams.project);
  const selectedProject =
    fallbackProjects.find((project) => project.id === requestedProjectId) ??
    fallbackProjects.find((project) => project.id === sampleProjects[0].id) ??
    fallbackProjects[0];

  const dashboard = await getDashboard(selectedProject.id, selectedProject);
  return {
    projects: fallbackProjects,
    selectedProject,
    dashboard,
  };
}

export function withProjectQuery(path: string, projectId: string): string {
  return `${path}${path.includes("?") ? "&" : "?"}project=${encodeURIComponent(projectId)}`;
}
