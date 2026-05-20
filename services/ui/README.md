# Experience UI

The custom governance experience layer — the views Phoenix's native UI does not
provide. React 18 + TypeScript + Vite + Tailwind + shadcn-style components,
React Query, React Router v6, and Recharts. Served on **:3000**.

It is designed for three audiences (FR-UI / §12): **engineering** (debug agents,
inspect eval results, traces), **risk & compliance** (audit governance state,
export evidence, review approvals), and **leadership** (dashboards, regressions).

## Pages

| Route | Page |
|---|---|
| `/` | Dashboard — KPIs, 7-day pass-rate, recent regressions + changes |
| `/agents` · `/agents/:id` | Agent registry + detail (metadata, evals, traces, change timeline) |
| `/evals` · `/evals/:id` | Eval registry + detail with the **governance workflow** (submit → calibrate → approve → deprecate) and audit trail |
| `/traces` · `/traces/:traceId` | Trace explorer with the governance overlay; deep-links to Phoenix |
| `/regressions` | Regression alerts + ranked candidate causes + status controls |
| `/changes` | Change-event timeline with before/after diff |
| `/governance` | Governance health, audit-ready CSV exports, regulator view |

## Conventions (FR-UI-2)

- Verdict color coding: green pass, yellow partial, red fail, gray unknown
  (`src/lib/verdict.ts`).
- Numbers right-aligned + tabular (`.num`); timestamps in local TZ with a UTC
  tooltip (`<LocalTime />`).
- Every detail view has a **JSON** button (`<JsonButton />`) showing the raw object.
- The Phoenix span tree is **not** duplicated — span-level views link out.

## Types (NFR-5 / AC-10)

TypeScript types are generated from the live OpenAPI specs:

```bash
# with governance-api (:8001) and orchestrator (:8002) running
npm run gen:types     # → src/api/*.gen.ts ; aliased in src/api/types.ts
```

## Develop / build / test

```bash
npm install
npm run dev      # http://localhost:3000 (proxies to localhost:8001/8002/6006)
npm run build    # tsc --noEmit && vite build
npm run test     # vitest — governance state-machine UI tests
```

API URLs come from `VITE_GOVERNANCE_API_URL`, `VITE_ORCHESTRATOR_URL`,
`VITE_PHOENIX_URL` (baked at build time; default to `localhost` host ports).
