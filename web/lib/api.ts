import { sampleDashboard, sampleProjects } from "./sample-data";

export type VisibilityMetrics = {
  mention_rate: number;
  citation_share: number;
  answer_position: number;
  token_share: number;
  quote_coverage: number;
  run_variance: number;
  overall_score: number;
};

export type ProjectSummary = {
  id: string;
  name: string;
  base_url?: string | null;
  description?: string | null;
  created_at?: string;
};

export type DashboardData = typeof sampleDashboard;

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

function applyProjectToDashboard(dashboard: DashboardData, project: ProjectSummary): DashboardData {
  return {
    ...dashboard,
    project: {
      ...dashboard.project,
      ...project,
      base_url: project.base_url ?? dashboard.project.base_url,
      description: project.description ?? dashboard.project.description,
    },
  };
}

export async function getProjects(): Promise<ProjectSummary[]> {
  if (!apiBaseUrl) {
    return sampleProjects;
  }

  try {
    const response = await fetch(`${apiBaseUrl}/projects`, {
      cache: "no-store",
    });
    if (!response.ok) {
      return sampleProjects;
    }
    const data = (await response.json()) as ProjectSummary[];
    return Array.isArray(data) && data.length > 0 ? data : sampleProjects;
  } catch {
    return sampleProjects;
  }
}

export async function getDashboard(projectId?: string, project?: ProjectSummary): Promise<DashboardData> {
  if (!apiBaseUrl || !projectId) {
    return applyProjectToDashboard(sampleDashboard, project ?? sampleProjects[0]);
  }

  try {
    const response = await fetch(`${apiBaseUrl}/projects/${projectId}/dashboard`, {
      cache: "no-store",
    });
    if (!response.ok) {
      return applyProjectToDashboard(sampleDashboard, project ?? sampleProjects[0]);
    }
    const dashboard = (await response.json()) as DashboardData;
    return project ? applyProjectToDashboard(dashboard, project) : dashboard;
  } catch {
    return applyProjectToDashboard(sampleDashboard, project ?? sampleProjects[0]);
  }
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function formatScore(value: number): string {
  return value.toFixed(2);
}
