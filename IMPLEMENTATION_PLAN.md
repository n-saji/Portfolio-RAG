# Portfolio RAG rebuild tracker

Updated: 2026-10-16. Scope: this repository only. The portfolio site's fixed-response proxy remains a separate follow-up.

## Phase 0 — Baseline and measurement
- [x] Record architectural baseline: classifier → optional rewriter → embed → Pinecone → generator; 500-character chunks; hard filters; stale hardcoded source list.
- [x] Repair the stale local virtual environment and obtain a separate short-lived AWS profile; record a CloudWatch baseline for the deployed function.
- [x] Capture the available pre-release CloudWatch `Init Duration`, Lambda duration, and memory baseline.
- [ ] Capture visitor-to-answer timings and the new route's stage timings after release.
- [ ] Run at least 100 representative warm/cold requests and record p50/p95 and stage breakdown below.

## Phase 1 — Reviewed knowledge
- [x] Import published resume and retain source URL, SHA-256, and retrieval date.
- [x] Reconcile current-role, internship, education, and project facts in `data/approved/` using public sources only.
- [x] Snapshot all 56 original public GitHub repositories, excluding forks; group related repositories into projects.
- [x] Support optional, manually supplied LinkedIn export; keep raw export untracked and review candidate changes before indexing. No export has been provided yet.

## Phase 2 — Refresh workflow
- [x] Weekly source check prepares a review PR; merge is the approval gate.
- [x] Record `verified_at` and source dates; qualify current-role claims when evidence is more than 90 days old.
- [x] Reindex only reviewed data and keep the prior namespace for rollback.

## Phase 3 — Retrieval
- [x] Use heading-aware token-sized chunks with stable IDs and source metadata.
- [x] Add exact entity lookup plus lexical and dense retrieval; remove hard classifier filters and uncalibrated score thresholds.
- [x] Build and verify a versioned Pinecone namespace before switching the active version.

## Phase 4 — Chat and resilience
- [x] One normal-path model call, first-person grounded style, bounded follow-up history.
- [x] Preserve `/api/v1/chat` and `/api/v1/advanced-chat`; bound input, timeouts, and failures.
- [x] Add meaningful retrieval, grounding, and route tests (14 unit tests; 17 live answer samples reviewed).

## Phase 5 — Performance and release
- [x] Evaluate `gpt-6-luna` with no reasoning against local answer samples.
- [ ] Tune Lambda memory after stage measurements.
- [ ] Add provisioned concurrency only if cold starts still cause target misses.
- [x] Verify recall@5 ≥ 90% (73/73); 17 sampled answers reviewed with no unsupported claims observed.
- [ ] Verify visitor p95 < 4 seconds across at least 100 representative warm/cold requests.
- [ ] Record release identifier, index namespace, rollback target, and measured results below.

## Measurements
| Run/date | Environment | n | p50 | p95 | Init | Retrieval | Model | Notes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline, prior 30 days to 2026-10-16 | CloudWatch Lambda REPORT | 21 | 1.21 s duration | 17.83 s duration | 10 cold starts; mean 3.51 s, p95 4.53 s | — | — | Mixed routes and health checks; only 21 requests, so this does not meet the 100-request acceptance sample |
| Warm subset, prior 30 days | CloudWatch Lambda REPORT | 11 | 1.21 s duration | 9.12 s duration | — | — | — | Includes non-chat requests; inspect after release |
| Local review, 2026-10-16 | Local Python + remote model | 17 answer samples | — | — | — | — | ~1–3 s in manual samples | Not a visitor or Lambda measurement; all 73 retrieval questions hit in top 5 |

## Release notes
Review PR: [#1 — Rebuild portfolio RAG around reviewed facts and faster retrieval](https://github.com/n-saji/Portfolio-RAG/pull/1), from `codex/portfolio-rag-rebuild` into `main`. The verified new namespace is `portfolio-20261016-headings` (291 chunks); `portfolio-20261016-reviewed` is the rollback namespace. The active pointer is packaged only after deployment. Lambda ran with 1024 MB memory and used at most about 262 MB in the 30-day sample. Cold initialization was significant, but warm duration also has long-tail misses; tune only after the new one-call route is live. The portfolio site's fixed-response proxy must be addressed in that separate repository to apply the new first-person voice to every visitor path.
