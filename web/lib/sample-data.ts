export const sampleProjects = [
  {
    id: "prj_demo",
    name: "Atlas Docs",
    base_url: "https://docs.example.com",
    description: "Context-aware documentation optimization for AI search visibility.",
  },
  {
    id: "prj_orion",
    name: "Orion Knowledge Base",
    base_url: "https://kb.example.com",
    description: "Support articles and how-to guides for a fictional product knowledge base.",
  },
];

export const sampleDashboard = {
  project: {
    id: "prj_demo",
    name: "Atlas Docs",
    base_url: "https://docs.example.com",
    description: "Context-aware documentation optimization for AI search visibility.",
  },
  summary: {
    page_count: 3,
    context_pack_count: 2,
    query_cluster_count: 2,
    run_count: 4,
    recommendation_count: 2,
  },
  pages: [
    {
      id: "pag_guide",
      title: "Distributed tracing setup guide",
      url: "https://docs.example.com/tracing/setup",
      content_type: "docs_article",
      status: "active",
      latest_score: 0.74,
    },
    {
      id: "pag_concepts",
      title: "Tracing concepts",
      url: "https://docs.example.com/tracing/concepts",
      content_type: "docs_article",
      status: "active",
      latest_score: 0.58,
    },
    {
      id: "pag_reference",
      title: "Collector reference",
      url: "https://docs.example.com/reference/collector",
      content_type: "docs_article",
      status: "active",
      latest_score: 0.49,
    },
  ],
  context_packs: [
    {
      id: "cpk_demo",
      page_id: "pag_guide",
      brief: "Serve platform engineers who need concise, trustworthy setup guidance.",
      voice_rules: ["Technical and direct", "Prefer definitions and steps"],
      constraints: [
        { id: "con_1", kind: "locked_fact", value: "stores spans for 30 days by default" },
        { id: "con_2", kind: "required_term", value: "distributed tracing" },
      ],
      supporting_documents: [
        { id: "ctx_1", title: "Tracing concepts", url: "https://docs.example.com/tracing/concepts" },
        { id: "ctx_2", title: "Collector reference", url: "https://docs.example.com/reference/collector" },
      ],
    },
  ],
  query_clusters: [
    {
      id: "qcl_tracing",
      name: "Distributed tracing setup",
      description: "Queries from engineers looking for setup and implementation guidance.",
      target_page_ids: ["pag_guide"],
      queries: [
        { id: "qry_1", text: "how to set up distributed tracing", intent: "informational" },
        { id: "qry_2", text: "distributed tracing configuration guide", intent: "informational" },
      ],
    },
    {
      id: "qcl_latency",
      name: "Latency root cause analysis",
      description: "Queries focused on debugging slow services.",
      target_page_ids: ["pag_concepts"],
      queries: [
        { id: "qry_3", text: "latency root cause analysis tracing", intent: "informational" },
      ],
    },
  ],
  runs: [
    {
      id: "run_benchmark_1",
      engine_name: "newgeo-benchmark-v1",
      run_kind: "benchmark",
      status: "completed",
      created_at: "2026-03-22T10:15:00Z",
      observations: [
        {
          page_id: "pag_guide",
          metrics: {
            mention_rate: 0.92,
            citation_share: 0.77,
            answer_position: 1.0,
            token_share: 0.71,
            quote_coverage: 0.54,
            run_variance: 0.02,
            overall_score: 0.74,
          },
          notes: [
            "Strong early query coverage.",
            "Likely to appear near the top of generated answers.",
          ],
        },
        {
          page_id: "pag_concepts",
          metrics: {
            mention_rate: 0.56,
            citation_share: 0.18,
            answer_position: 2.0,
            token_share: 0.33,
            quote_coverage: 0.36,
            run_variance: 0.01,
            overall_score: 0.43,
          },
          notes: ["Good supporting context, but weaker direct setup language."],
        },
      ],
    },
    {
      id: "run_live_1",
      engine_name: "newgeo-live-spot-check",
      run_kind: "live_spot_check",
      status: "completed",
      created_at: "2026-03-22T11:00:00Z",
      observations: [
        {
          page_id: "pag_guide",
          metrics: {
            mention_rate: 0.86,
            citation_share: 0.72,
            answer_position: 1.2,
            token_share: 0.65,
            quote_coverage: 0.51,
            run_variance: 0.11,
            overall_score: 0.69,
          },
          notes: ["Spot-check result is observational and not directly comparable."],
        },
      ],
    },
  ],
  recommendations: [
    {
      id: "rec_guide",
      page_id: "pag_guide",
      context_pack_id: "cpk_demo",
      query_cluster_id: "qcl_tracing",
      status: "approved",
      created_at: "2026-03-22T10:30:00Z",
      bundle: {
        confidence: 0.88,
        supporting_context_used: ["Tracing concepts", "Collector reference"],
        rationale: [
          "Added a quick answer block aligned to the tracked query cluster.",
          "Surfaced locked facts explicitly so meaning-critical details stay visible.",
          "Pulled in read-only internal context from related docs.",
        ],
        preview: {
          baseline: {
            mention_rate: 0.92,
            citation_share: 0.77,
            answer_position: 1.0,
            token_share: 0.71,
            quote_coverage: 0.54,
            run_variance: 0.02,
            overall_score: 0.74,
          },
          projected: {
            mention_rate: 0.96,
            citation_share: 0.84,
            answer_position: 1.0,
            token_share: 0.79,
            quote_coverage: 0.62,
            run_variance: 0.02,
            overall_score: 0.81,
          },
          score_delta: 0.07,
        },
        constraint_checks: [
          { constraint_id: "con_1", constraint_kind: "locked_fact", status: "pass", message: "Locked fact preserved." },
          { constraint_id: "con_2", constraint_kind: "required_term", status: "pass", message: "Required term surfaced." },
          { constraint_id: "source_claims", constraint_kind: "source_claims", status: "pass", message: "Source claims were preserved." },
        ],
        diff_markdown: "```diff\n+ ## Quick answer\n+ ## Locked facts to preserve\n+ ## Related internal context\n```",
        rewritten_markdown: "# Distributed tracing setup guide\n\n## Quick answer\nAtlas tracing captures request flow across services and stores spans for 30 days by default.\n\n## Locked facts to preserve\n- stores spans for 30 days by default\n\n## Related internal context\n- Tracing concepts: Tracing follows a request through services.\n- Collector reference: The Atlas collector accepts OpenTelemetry spans.\n\n## Suggested page body\nOriginal page body...",
      },
    },
    {
      id: "rec_latency",
      page_id: "pag_concepts",
      context_pack_id: "cpk_demo",
      query_cluster_id: "qcl_latency",
      status: "generated",
      created_at: "2026-03-22T11:12:00Z",
      bundle: {
        confidence: 0.73,
        supporting_context_used: ["Tracing concepts"],
        rationale: ["Added a clearer lead paragraph for root cause analysis queries."],
        preview: {
          baseline: {
            mention_rate: 0.48,
            citation_share: 0.28,
            answer_position: 2.1,
            token_share: 0.31,
            quote_coverage: 0.29,
            run_variance: 0.02,
            overall_score: 0.41,
          },
          projected: {
            mention_rate: 0.61,
            citation_share: 0.36,
            answer_position: 1.8,
            token_share: 0.42,
            quote_coverage: 0.35,
            run_variance: 0.02,
            overall_score: 0.5,
          },
          score_delta: 0.09,
        },
        constraint_checks: [
          { constraint_id: "source_claims", constraint_kind: "source_claims", status: "pass", message: "Source claims were preserved." },
        ],
        diff_markdown: "```diff\n+ ## Quick answer\n```",
        rewritten_markdown: "Generated draft...",
      },
    },
  ],
  score_snapshots: [
    { id: "scr_1", page_id: "pag_guide", metrics: { overall_score: 0.62 }, created_at: "2026-03-19T09:00:00Z" },
    { id: "scr_2", page_id: "pag_guide", metrics: { overall_score: 0.68 }, created_at: "2026-03-20T09:00:00Z" },
    { id: "scr_3", page_id: "pag_guide", metrics: { overall_score: 0.74 }, created_at: "2026-03-22T09:00:00Z" },
    { id: "scr_4", page_id: "pag_concepts", metrics: { overall_score: 0.43 }, created_at: "2026-03-22T09:00:00Z" },
  ],
};
