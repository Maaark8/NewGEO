import Link from "next/link";
import { ReactNode } from "react";
import type { ProjectSummary } from "@/lib/api";
import { withProjectQuery } from "@/lib/workspace";

type NavKey = "overview" | "pages" | "queries" | "runs" | "recommendations" | "compare";

const navItems: Array<{ key: NavKey; href: string; label: string; eyebrow: string }> = [
  { key: "overview", href: "/", label: "Overview", eyebrow: "Mission Control" },
  { key: "pages", href: "/pages", label: "Pages", eyebrow: "Content Surface" },
  { key: "queries", href: "/queries", label: "Queries", eyebrow: "Demand Map" },
  { key: "runs", href: "/runs", label: "Runs", eyebrow: "Benchmark Feed" },
  { key: "recommendations", href: "/recommendations", label: "Recommendations", eyebrow: "Review Queue" },
  { key: "compare", href: "/compare", label: "Compare", eyebrow: "Before / After" },
];

export function DashboardShell({
  active,
  projectName,
  currentPath,
  selectedProjectId,
  projects,
  subtitle,
  children,
}: {
  active: NavKey;
  projectName: string;
  currentPath: string;
  selectedProjectId: string;
  projects: ProjectSummary[];
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <div className="app-frame">
      <aside className="sidebar">
        <div className="brand-panel">
          <p className="eyebrow">Open Source GEO Platform</p>
          <h1>NewGEO</h1>
          <p className="brand-copy">
            Monitor generative visibility, optimize with context, and review measurable lift without losing meaning.
          </p>
        </div>

        <div className="project-switcher">
          <p className="eyebrow">Projects</p>
          <div className="project-list">
            {projects.map((project) => (
              <Link
                key={project.id}
                href={withProjectQuery(currentPath, project.id)}
                className={`project-card ${project.id === selectedProjectId ? "active" : ""}`}
              >
                <strong>{project.name}</strong>
                <span>{project.base_url ?? project.id}</span>
              </Link>
            ))}
          </div>
        </div>

        <nav className="nav-list">
          {navItems.map((item) => (
            <Link
              key={item.key}
              href={withProjectQuery(item.href, selectedProjectId)}
              className={`nav-card ${active === item.key ? "active" : ""}`}
            >
              <span>{item.eyebrow}</span>
              <strong>{item.label}</strong>
            </Link>
          ))}
        </nav>
      </aside>

      <main className="content-area">
        <section className="hero-panel">
          <div>
            <p className="eyebrow">Project</p>
            <h2>{projectName}</h2>
            <p className="hero-copy">{subtitle}</p>
          </div>
          <div className="hero-stat">
            <span>Design note</span>
            <strong>Context pack first</strong>
            <p>Supporting pages stay read-only while recommendations keep locked facts visible.</p>
          </div>
        </section>
        {children}
      </main>
    </div>
  );
}

export function MetricCard({
  label,
  value,
  tone = "mint",
  detail,
}: {
  label: string;
  value: string;
  tone?: "mint" | "gold" | "coral" | "sky";
  detail: string;
}) {
  return (
    <article className={`metric-card tone-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{detail}</p>
    </article>
  );
}

export function Panel({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">{subtitle}</p>
          <h3>{title}</h3>
        </div>
      </div>
      {children}
    </section>
  );
}

export function StatusPill({ value }: { value: string }) {
  const tone =
    value === "approved" || value === "completed"
      ? "success"
      : value === "generated" || value === "queued"
        ? "warning"
        : "neutral";
  return <span className={`pill pill-${tone}`}>{value.replaceAll("_", " ")}</span>;
}

export function MiniTrend({ values }: { values: number[] }) {
  return (
    <div className="mini-trend" aria-hidden="true">
      {values.map((value, index) => (
        <span key={`${value}-${index}`} style={{ height: `${Math.max(18, value * 110)}px` }} />
      ))}
    </div>
  );
}
