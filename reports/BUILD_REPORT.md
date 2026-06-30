# Autodesk RAG — Build & Eval Report


## Phase 0 — Scaffold
_2026-06-29 15:37:00_

**Status: DONE.** Orchestration-only env (`/mnt/data/ubuntu/research/env/lang`, py3.11); models served separately via vLLM OpenAI-compatible endpoints.

Delivered:
- `core/config.py` — single config loader (dotted access) over `config/settings.yaml`.
- `core/state.py` — `Chunk` dataclass (text + provenance metadata) and `GraphState` TypedDict (all keys optional -> graceful degradation).
- `core/interfaces.py` — ABCs: `BaseRetriever`, `BaseReranker`, `BaseGenerator`, `BaseGuard`, `BaseJudge`.
- `core/registry.py` — name->class registry/factory (swap components via a config string).
- `obs/report.py` — append-only report helper (this file).
- `requirements.txt`, project package skeleton.

Modularity mechanisms in place: (1) interfaces+registry, (2) config-driven flags (`enabled` per optional component), (3) OpenAI-compatible model endpoints.

Tests: `tests/test_phase0_scaffold.py` — 4 passed (config load, Chunk roundtrip, registry register/build/swap, partial state).


## Phase 1a — Ingestion & Document Selection
_2026-06-29 15:59:51_

**Status: DONE.** Cleaned the raw HTML dump into a deduped, metadata-rich doc set.

- Raw files: **1218**  →  kept docs: **729**
- Output: `/home/ubuntu/research/langgraph/data/clean_docs.jsonl`
- Extraction methods used: {'trafilatura': 660, 'bs4': 69}
- Text length (chars): {'min': 269, 'max': 32681, 'median': 2600, 'mean': 3423, 'p10': 630, 'p90': 7356}

**Dropped (selection rationale):**
| reason | count |
| --- | --- |
| empty_after_extraction | 238 |
| duplicate_content | 184 |
| dropped_page_type | 64 |
| too_small | 2 |
| non_english | 1 |

**Kept by page_type:**
| page_type | docs |
| --- | --- |
| products | 226 |
| support | 85 |
| customer-stories | 37 |
| unknown | 35 |
| en | 27 |
| solutions | 19 |
| resources | 19 |
| tools | 17 |
| collections | 17 |
| campaigns | 13 |
| partners | 10 |
| workflows | 10 |
| home | 10 |
| education | 9 |
| industry | 8 |
| buying | 8 |
| trust | 8 |
| forma | 8 |
| webinars | 7 |
| blogs | 7 |
| sustainability | 7 |
| aec | 7 |
| compare | 6 |
| design-make | 6 |
| learning | 6 |
| careers | 6 |
| genuine | 6 |
| research-areas | 5 |
| insights | 4 |
| partner-program | 4 |
| events | 4 |
| publications | 4 |
| financials | 3 |
| news-events | 3 |
| developer | 3 |
| stock-information | 3 |
| news-releases | 3 |
| contact-us | 3 |
| promotions | 2 |
| future-of-work | 2 |
| design-studio | 2 |
| contact | 2 |
| blog | 2 |
| affiliate-program | 2 |
| autodesk-developer-programs | 2 |
| trial | 2 |
| training | 2 |
| customer-value | 2 |
| corporate-governance | 2 |
| pricing | 2 |
| ${newurl} | 1 |
| issue-resolution-clash-avoidance-autodesk-bim-collaborate | 1 |
| free-trials | 1 |
| certification | 1 |
| collaborations | 1 |
| streamline-bid-management | 1 |
| site-selector | 1 |
| get-help | 1 |
| autodesk-university | 1 |
| winning-construction-bids | 1 |
| customer-impressions-autodesk-takeoff | 1 |
| model-design-coordination-field | 1 |
| inventor | 1 |
| customer | 1 |
| construction-estimating-software | 1 |
| submittals-template | 1 |
| master-class | 1 |
| how-to-estimate-construction-costs | 1 |
| social-media | 1 |
| autodesk-life | 1 |
| vault | 1 |
| shortcuts | 1 |
| advanced-manufacturing | 1 |
| subcontractor-qualification | 1 |
| bim-360 | 1 |
| subscription | 1 |
| learn-lab | 1 |
| why-autodesk-construction-cloud | 1 |
| vision | 1 |
| design-automation-apis | 1 |
| big-room | 1 |
| covid-19 | 1 |
| 360-cloud | 1 |
| projects | 1 |
| people | 1 |
| technology-centers | 1 |
| sitemap | 1 |
| viewers | 1 |
| benefits | 1 |
| how-to-find-subcontractors | 1 |
| community | 1 |
| autodesk-takeoff | 1 |

Rationale: dropped bot-block pages, tiny redirects, non-English localized pages,
near-empty templates, exact-content duplicates, and low-value `legal`/`terms-of-use`
pages. Each kept doc carries `url`, `product`, `page_type` for cited, filterable retrieval.


## Phase 1a — Ingestion & Document Selection
_2026-06-29 16:16:58_

**Status: DONE.** Cleaned the raw HTML dump into a deduped, metadata-rich doc set.

- Raw files: **1218**  →  kept docs: **729**
- Output: `/home/ubuntu/research/langgraph/data/clean_docs.jsonl`
- Extraction methods used: {'trafilatura': 660, 'bs4': 69}
- Text length (chars): {'min': 269, 'max': 32681, 'median': 2600, 'mean': 3423, 'p10': 630, 'p90': 7356}

**Dropped (selection rationale):**
| reason | count |
| --- | --- |
| empty_after_extraction | 238 |
| duplicate_content | 184 |
| dropped_page_type | 64 |
| too_small | 2 |
| non_english | 1 |

**Kept by page_type:**
| page_type | docs |
| --- | --- |
| products | 226 |
| support | 85 |
| customer-stories | 37 |
| unknown | 35 |
| solutions | 19 |
| resources | 19 |
| tools | 17 |
| collections | 17 |
| campaigns | 13 |
| home | 11 |
| partners | 10 |
| workflows | 10 |
| education | 9 |
| industry | 8 |
| buying | 8 |
| trust | 8 |
| forma | 8 |
| webinars | 7 |
| blogs | 7 |
| sustainability | 7 |
| aec | 7 |
| compare | 6 |
| design-make | 6 |
| learning | 6 |
| news | 6 |
| careers | 6 |
| genuine | 6 |
| stories | 5 |
| research-areas | 5 |
| views | 5 |
| insights | 4 |
| partner-program | 4 |
| pressrelease | 4 |
| events | 4 |
| publications | 4 |
| media-resources | 3 |
| financials | 3 |
| news-events | 3 |
| developer | 3 |
| stock-information | 3 |
| news-releases | 3 |
| contact-us | 3 |
| promotions | 2 |
| future-of-work | 2 |
| design-studio | 2 |
| contact | 2 |
| blog | 2 |
| affiliate-program | 2 |
| autodesk-developer-programs | 2 |
| trial | 2 |
| training | 2 |
| customer-value | 2 |
| corporate-governance | 2 |
| pricing | 2 |
| ${newurl} | 1 |
| categories | 1 |
| issue-resolution-clash-avoidance-autodesk-bim-collaborate | 1 |
| free-trials | 1 |
| certification | 1 |
| collaborations | 1 |
| streamline-bid-management | 1 |
| site-selector | 1 |
| get-help | 1 |
| autodesk-university | 1 |
| winning-construction-bids | 1 |
| customer-impressions-autodesk-takeoff | 1 |
| model-design-coordination-field | 1 |
| inventor | 1 |
| customer | 1 |
| construction-estimating-software | 1 |
| submittals-template | 1 |
| master-class | 1 |
| how-to-estimate-construction-costs | 1 |
| social-media | 1 |
| autodesk-life | 1 |
| vault | 1 |
| shortcuts | 1 |
| media-contacts | 1 |
| advanced-manufacturing | 1 |
| subcontractor-qualification | 1 |
| bim-360 | 1 |
| subscription | 1 |
| learn-lab | 1 |
| why-autodesk-construction-cloud | 1 |
| vision | 1 |
| design-automation-apis | 1 |
| big-room | 1 |
| covid-19 | 1 |
| 360-cloud | 1 |
| projects | 1 |
| people | 1 |
| technology-centers | 1 |
| about | 1 |
| sitemap | 1 |
| viewers | 1 |
| benefits | 1 |
| how-to-find-subcontractors | 1 |
| community | 1 |
| autodesk-takeoff | 1 |

Rationale: dropped bot-block pages, tiny redirects, non-English localized pages,
near-empty templates, exact-content duplicates, and low-value `legal`/`terms-of-use`
pages. Each kept doc carries `url`, `product`, `page_type` for cited, filterable retrieval.


## Phase 1a — Note: the 238 'empty' pages
_2026-06-29 16:17:17_


Investigated the 238 `empty_after_extraction` drops (169 are `/support/technical` KB
pages). Confirmed they are **client-side-rendered shells**: ~29 visible chars, ~35 KB of
src-based scripts, no `__NEXT_DATA__` / JSON-LD / inline JSON. The article body was never
in the static crawl, so it is unrecoverable without a headless browser render. Dropping
them is correct. (We still keep 85 support pages that *do* carry static content.)

**Implication / future work:** to cover the support KB, re-crawl those URLs with a JS-capable
fetcher (Playwright) — listed in the optional plan, not blocking the PoC.

Taxonomy fix applied: leading locale segments (`/en/...`) are now stripped before deriving
`page_type` (previously produced a bogus `page_type="en"`).


## Phase 1b — Index build
_2026-06-29 16:48:31_

**Status: DONE.**
- Indexed **1494** chunks.
- Dense: `embeddings.npy` (1024-d, normalized) via `Qwen3-Embedding-0.6B`.
- Lexical: BM25Okapi over tokenized chunks (`bm25.pkl`).
- Transparent numpy-backed store behind `BaseRetriever` (swap to Chroma/FAISS = config change).


## Phase 1a — Ingestion & Document Selection
_2026-06-29 16:50:20_

**Status: DONE.** Cleaned the raw HTML dump into a deduped, metadata-rich doc set.

- Raw files: **1218**  →  kept docs: **729**
- Output: `/home/ubuntu/research/langgraph/data/clean_docs.jsonl`
- Extraction methods used: {'trafilatura': 660, 'bs4': 69}
- Text length (chars): {'min': 269, 'max': 32681, 'median': 2600, 'mean': 3423, 'p10': 630, 'p90': 7356}

**Dropped (selection rationale):**
| reason | count |
| --- | --- |
| empty_after_extraction | 238 |
| duplicate_content | 184 |
| dropped_page_type | 64 |
| too_small | 2 |
| non_english | 1 |

**Kept by page_type:**
| page_type | docs |
| --- | --- |
| products | 226 |
| support | 85 |
| customer-stories | 37 |
| unknown | 35 |
| solutions | 19 |
| resources | 19 |
| tools | 17 |
| collections | 17 |
| campaigns | 13 |
| home | 11 |
| partners | 10 |
| workflows | 10 |
| education | 9 |
| industry | 8 |
| buying | 8 |
| trust | 8 |
| forma | 8 |
| webinars | 7 |
| blogs | 7 |
| sustainability | 7 |
| aec | 7 |
| compare | 6 |
| design-make | 6 |
| learning | 6 |
| news | 6 |
| careers | 6 |
| genuine | 6 |
| stories | 5 |
| research-areas | 5 |
| views | 5 |
| insights | 4 |
| partner-program | 4 |
| pressrelease | 4 |
| events | 4 |
| publications | 4 |
| media-resources | 3 |
| financials | 3 |
| news-events | 3 |
| developer | 3 |
| stock-information | 3 |
| news-releases | 3 |
| contact-us | 3 |
| promotions | 2 |
| future-of-work | 2 |
| design-studio | 2 |
| contact | 2 |
| blog | 2 |
| affiliate-program | 2 |
| autodesk-developer-programs | 2 |
| trial | 2 |
| training | 2 |
| customer-value | 2 |
| corporate-governance | 2 |
| pricing | 2 |
| ${newurl} | 1 |
| categories | 1 |
| issue-resolution-clash-avoidance-autodesk-bim-collaborate | 1 |
| free-trials | 1 |
| certification | 1 |
| collaborations | 1 |
| streamline-bid-management | 1 |
| site-selector | 1 |
| get-help | 1 |
| autodesk-university | 1 |
| winning-construction-bids | 1 |
| customer-impressions-autodesk-takeoff | 1 |
| model-design-coordination-field | 1 |
| inventor | 1 |
| customer | 1 |
| construction-estimating-software | 1 |
| submittals-template | 1 |
| master-class | 1 |
| how-to-estimate-construction-costs | 1 |
| social-media | 1 |
| autodesk-life | 1 |
| vault | 1 |
| shortcuts | 1 |
| media-contacts | 1 |
| advanced-manufacturing | 1 |
| subcontractor-qualification | 1 |
| bim-360 | 1 |
| subscription | 1 |
| learn-lab | 1 |
| why-autodesk-construction-cloud | 1 |
| vision | 1 |
| design-automation-apis | 1 |
| big-room | 1 |
| covid-19 | 1 |
| 360-cloud | 1 |
| projects | 1 |
| people | 1 |
| technology-centers | 1 |
| about | 1 |
| sitemap | 1 |
| viewers | 1 |
| benefits | 1 |
| how-to-find-subcontractors | 1 |
| community | 1 |
| autodesk-takeoff | 1 |

Rationale: dropped bot-block pages, tiny redirects, non-English localized pages,
near-empty templates, exact-content duplicates, and low-value `legal`/`terms-of-use`
pages. Each kept doc carries `url`, `product`, `page_type` for cited, filterable retrieval.


## Phase 1b — Index build
_2026-06-29 16:50:40_

**Status: DONE.**
- Indexed **1494** chunks.
- Dense: `embeddings.npy` (1024-d, normalized) via `Qwen3-Embedding-0.6B`.
- Lexical: BM25Okapi over tokenized chunks (`bm25.pkl`).
- Transparent numpy-backed store behind `BaseRetriever` (swap to Chroma/FAISS = config change).


## Phase 1b — Chunking & Index
_2026-06-29 16:50:55_

**Status: DONE.**
- Structure-aware chunking: 729 docs -> **1494 chunks** (paragraph-packed, ~512-token target,
  64-token overlap, title prepended to each chunk). Median ~344 words/chunk.
- Dense index: `embeddings.npy` (1494 x 1024, normalized) via Qwen3-Embedding-0.6B.
- Lexical index: BM25Okapi (`bm25.pkl`).
- HybridRetriever (RRF, k=60) verified: Fusion queries -> Fusion product pages; "AutoCAD vs
  Revit" -> AEC/BIM pages. Titles HTML-unescaped for clean citations.

**Serving note:** models served via vLLM in the base env using a per-process `_stubs/torchaudio`
shim (a broken torchaudio in that env otherwise blocks `transformers` import). No shared package
modified; orchestration runs in the isolated `lang` env and talks HTTP only. vLLM 0.23 flags:
`--runner pooling --max-model-len 2048` for the embedding model.


## Phase 2 — Core corpus-only RAG
_2026-06-29 17:11:12_

**Status: DONE.** LangGraph pipeline `retrieve -> rerank -> generate` working end to end.

- **Retrieval:** HybridRetriever (dense Qwen3-Embedding + BM25, RRF fusion), top_k=20.
- **Rerank:** Qwen3-Reranker-0.6B via vLLM `/rerank`. Fixed weak-contrast issue with
  `--hf-overrides {architectures:[Qwen3ForSequenceClassification], classifier_from_token:[no,yes],
  is_original_qwen3_reranker:true}` -> proper P(yes) scores (0.96 relevant / 0.36 off-topic).
- **Generate:** Qwen3-4B-Instruct-2507, grounded prompt with inline [n] citations; citations
  parsed back to source URLs for transparency + citation-correctness eval.

**Sample-question behavior (`reports/sample_answers_corpus_only.md`):**
- Fusion 360 / AutoCAD LT 3D / Fusion-on-Mac -> correct, grounded, cited.
- AutoCAD vs Revit -> honestly notes the corpus has no direct comparison (no hallucinated diff).
- "Latest Maya release" -> answers "Maya 2024" = the **stale-corpus trap** (Dec-2023 snapshot);
  the case for web augmentation (Phase 5).
- "How much does AutoCAD cost?" / "Capital of France?" -> correctly **abstain**.

**Latency:** retrieve 17-300ms, rerank 300-480ms, generate 0.7-2.7s.
**Tests:** `tests/test_phase2_rag.py` 4 passed incl. gated e2e (`RAG_STACK_UP=1`).
**Deliverables:** `app/cli.py` (interactive+single-shot), `app/run_samples.py`.


## Phase 3 — Conversation + guards
_2026-06-29 17:20:02_

**Status: DONE.** Guard nodes wired into the LangGraph, each independently toggle-able
in config. Full graph: `rewrite -> retrieve -> rerank -> [abstain_gate] -> generate|abstain_response -> ground`.
With all guards off it collapses to the Phase 2 core (verified) — demonstrates the modular design.

- **Conversation rewrite** (generator LLM, gated by a pronoun/ellipsis heuristic): multi-turn
  "Does it run on a Mac?" after a Fusion 360 turn -> rewritten to "Does Fusion 360 run on a Mac?".
  Standalone queries are left untouched.
- **Abstention** = two layers: (1) retrieval-confidence gate (conditional edge, threshold on top
  rerank score) for early exit; (2) the generator's grounding prompt. Nonsense/out-of-scope -> abstain.
- **Grounding guard** (judge = Qwen3-8B, *different model from the generator*): per-claim entailment
  vs sources, annotates answer with `groundedness` without rewriting it. Caught a real over-claim:
  the "Fusion 360 on Mac" answer scored groundedness=0.0 (sources said "any device", not "Mac"),
  while the AutoCAD-LT-3D answer scored 1.0.

**Tests:** full suite **23 passed** (incl. gated e2e: rewrite resolves pronoun, grounding annotates).


## Phase 4 — Evaluation (corpus_only)
_2026-06-29 18:47:10_

**Condition: `corpus_only`** · golden items: 3

### Judge validity (judge vs human labels)
accuracy = **1.0**, Cohen's kappa = **1.0**
on 12 hand-labelled faithful/hallucinated cases. (Cases are clear-cut by
design; a production annotation set would be harder. This establishes the judge discriminates
grounded from hallucinated answers before we trust its scores below.)

### Retrieval (synthetic items, doc-level relevance)
| metric | value |
| --- | --- |
| mrr | 0.8333 |
| recall@1 | 0.2778 |
| hit@1 | 0.6667 |
| ndcg@1 | 0.6667 |
| recall@3 | 0.75 |
| hit@3 | 1.0 |
| ndcg@3 | 0.7654 |
| recall@5 | 0.9167 |
| hit@5 | 1.0 |
| ndcg@5 | 0.8551 |
| recall@10 | 1.0 |
| hit@10 | 1.0 |
| ndcg@10 | 0.8985 |

### Generation (LLM judge, answered items)
- faithfulness = **1.0**
- answer_relevance = **1.0**

### Citation
- has-citation rate (answered) = 1.0
- gold-doc-cited rate (synthetic answered) = 1.0

### Abstention
- abstain recall on unanswerable/out-of-scope = None
- false-abstain rate on answerable = None

### System
- latency mean = 2055 ms · p90 = 2976 ms


## Phase 4 — Evaluation (corpus_only)
_2026-06-29 18:52:57_

**Condition: `corpus_only`** · golden items: 48

### Judge validity (judge vs human labels)
accuracy = **1.0**, Cohen's kappa = **1.0**
on 12 hand-labelled faithful/hallucinated cases. (Cases are clear-cut by
design; a production annotation set would be harder. This establishes the judge discriminates
grounded from hallucinated answers before we trust its scores below.)

### Retrieval (synthetic items, doc-level relevance)
| metric | value |
| --- | --- |
| mrr | 0.745 |
| recall@1 | 0.35 |
| hit@1 | 0.625 |
| ndcg@1 | 0.625 |
| recall@3 | 0.6771 |
| hit@3 | 0.85 |
| ndcg@3 | 0.6567 |
| recall@5 | 0.7771 |
| hit@5 | 0.925 |
| ndcg@5 | 0.7035 |
| recall@10 | 0.9208 |
| hit@10 | 0.975 |
| ndcg@10 | 0.7621 |

### Generation (LLM judge, answered items)
- faithfulness = **0.9821**
- answer_relevance = **0.9949**

### Citation
- has-citation rate (answered) = 0.974
- gold-doc-cited rate (synthetic answered) = 0.697

### Abstention
- abstain recall on unanswerable/out-of-scope = 1.0
- false-abstain rate on answerable = 0.0

### System
- latency mean = 2037 ms · p90 = 4090 ms


## Phase 4 — Baseline interpretation and status
_2026-06-29 19:12:28_

**Status: DONE for the corpus-only milestone.** The full corpus-only eval completed on
48 golden items and wrote `reports/eval_report_corpus_only.json`. A human-readable summary was
also added at `reports/eval_report_corpus_only.md`.

Key interpretation:
- Retrieval is strong enough for the current baseline: `hit@10=0.975`, `mrr=0.745`.
- Generation quality is high under the Qwen3-8B judge: `faithfulness=0.9821`,
  `answer_relevance=0.9949`.
- Citation format compliance is excellent: `has_citation_rate=0.974`.
- Exact synthetic-source citation is more moderate: `gold_doc_cited_rate=0.697`. This is a strict
  metric: answers can be faithful while citing an overlapping Autodesk source instead of the exact
  document used to generate the synthetic question.
- Abstention behavior is strong on the small curated set: unanswerable/out-of-scope recall `1.0`,
  false abstain on answerable curated questions `0.0`.

Remaining Phase 4 polish: save per-item eval outputs, hand-review a realistic 30-50 item subset,
and improve source precision/citation targeting. These are quality improvements, not blockers for
moving to Phase 5.


## Serving ops — vLLM startup stabilization
_2026-06-29 19:12:28_

Updated `serve_models.sh` after vLLM reported negative available KV-cache memory when multiple
servers warmed up on GPU 4 simultaneously. The script now starts model servers sequentially and
waits for each `/v1/models` endpoint before launching the next one. It also adds:

- `bash serve_models.sh status` for endpoint checks.
- `bash serve_models.sh eval` for judge + generator + embedding + reranker.
- Qwen3 reranker `hf-overrides` for proper sequence-classification relevance scores.

This keeps the all-local serving plan intact while avoiding concurrent vLLM profiling spikes.


## Phase 5 — Web augmentation subplan
_2026-06-29 19:20:00_

**Status: PLANNED / NEXT.** Added a detailed Phase 5 subplan to `PLAN.md`.

Implementation will keep the current corpus-first path intact and add web as an optional,
confidence-driven fallback. Main code areas to update:

- `config/settings.yaml`: web provider, allowed domains, trigger thresholds, recency terms.
- `retrieval/web.py`: web search/fetch retriever returning normal `Chunk` objects.
- `graph/nodes.py` and `graph/build_graph.py`: web trigger gate, web retrieval node, merge/rerank path.
- `generate/prompts.py`: distinguish Dec-2023 corpus sources from live web sources.
- `eval/run_eval.py`: add `web_augmented` condition, per-item outputs, and A/B report generation.
- `tests/`: stubbed web retriever, routing, trigger, and A/B report tests.

Primary Phase 5 deliverables will be `reports/eval_report_ab.md` / `.json` and optionally
`reports/sample_answers_web_augmented.md`, with special attention to recency questions such as
"latest Maya release."


## Phase 5 — Web augmentation implementation
_2026-06-29 19:34:00_

**Status: IMPLEMENTED, LIVE A/B PENDING.** The optional web branch is now coded and covered by
deterministic unit tests. `web.enabled=false` remains the default, so the existing corpus-only
path is unchanged unless explicitly enabled.

Implemented:
- `config/settings.yaml`: web provider settings, allowed domains, result limits, recency/dynamic
  trigger terms, in-domain terms.
- `retrieval/web.py`: `WebRetriever(BaseRetriever)` using DuckDuckGo HTML search by default,
  constrained to configured domains and returning normal `Chunk(source="web")` objects.
- `graph/nodes.py`: web trigger decision, web retrieval, merge/rerank, and trace fields
  (`web_triggered`, `web_reason`, `n_web_results`, `final_context_sources`).
- `graph/build_graph.py`: optional web branch is wired only when `web.enabled=true`.
- `generate/prompts.py`: source blocks now label Dec-2023 corpus snapshot sources vs live web
  sources; live web is preferred for latest/current/version/pricing questions when present.
- `eval/run_eval.py`: supports `--condition web_augmented`, writes per-item JSONL, and writes
  `eval_report_ab.md/.json` when both corpus-only and web-augmented reports exist.
- `tests/test_phase5_web.py`: no-network tests for trigger logic, URL filtering, web chunk shape,
  and optional graph wiring.

Verification:
- `python -m pytest tests/test_phase5_web.py -q` -> **5 passed**.
- `python -m pytest -q` -> **25 passed, 3 skipped**.

Pending live A/B run:
- With model servers online and network access available, run
  `python -m langgraph_rag.eval.run_eval --condition web_augmented`.
- Then inspect `reports/eval_report_ab.md`, `reports/eval_items_web_augmented.jsonl`, and the
  recency cases such as "latest Maya release."


## Phase 5 — Evaluation (web_augmented)
_2026-06-29 20:13:30_

**Condition: `web_augmented`** · golden items: 48

### Judge validity (judge vs human labels)
accuracy = **1.0**, Cohen's kappa = **1.0**
on 12 hand-labelled faithful/hallucinated cases. (Cases are clear-cut by
design; a production annotation set would be harder. This establishes the judge discriminates
grounded from hallucinated answers before we trust its scores below.)

### Retrieval (synthetic items, doc-level relevance)
| metric | value |
| --- | --- |
| mrr | 0.745 |
| recall@1 | 0.35 |
| hit@1 | 0.625 |
| ndcg@1 | 0.625 |
| recall@3 | 0.6771 |
| hit@3 | 0.85 |
| ndcg@3 | 0.6567 |
| recall@5 | 0.7771 |
| hit@5 | 0.925 |
| ndcg@5 | 0.7035 |
| recall@10 | 0.9208 |
| hit@10 | 0.975 |
| ndcg@10 | 0.7621 |

### Generation (LLM judge, answered items)
- faithfulness = **0.955**
- answer_relevance = **0.9887**

### Citation
- has-citation rate (answered) = 0.975
- gold-doc-cited rate (synthetic answered) = 0.588

### Abstention
- abstain recall on unanswerable/out-of-scope = 1.0
- false-abstain rate on answerable = 0.0

### Web
- web trigger rate = 0.146
- web result rate = 0.042
- final context contains web rate = 0.042

### System
- latency mean = 3615 ms · p90 = 4930 ms


## Phase 5 — Web A/B regression follow-up
_2026-06-29 20:31:00_

The first live `web_augmented` run completed, but it should not be treated as a win yet. Compared
with the earlier `corpus_only` aggregate, quality moved down while latency moved up:

- faithfulness: **0.9821 -> 0.955**
- answer relevance: **0.9949 -> 0.9887**
- gold-doc-cited rate: **0.697 -> 0.588**
- latency mean: **2037 ms -> 3615 ms**
- web trigger rate: **0.146**
- final web context rate: **0.042**

Interpretation:
- Retrieval metrics are unchanged because the current evaluator scores the corpus `retrieved`
  candidates, not the final post-web context list.
- The web branch triggered on a small slice of queries but produced final web evidence for only
  two items. For several important freshness questions, the DuckDuckGo HTML provider returned no
  usable Autodesk pages.
- Generic subscription/cost wording was too broad as a freshness trigger. Those queries often have
  strong corpus answers and do not need web unless corpus confidence is low.
- Exact `gold_doc_cited_rate` can fall when a web source or alternate corpus page answers the
  question correctly but does not match the synthetic item's gold document id. Still, the drop is a
  useful warning signal.

Mitigation applied:
- Narrowed `web.recency_terms` to real freshness terms: latest/newest/current/today/release/version.
- Changed `merge_contexts` so empty web results preserve the already reranked corpus contexts.
- Changed web merging to combine live web chunks with already reranked corpus contexts, not the
  full broader retrieval pool.
- Added regression tests for high-confidence subscription queries and empty-web-result fallback.

Verification:
- `/mnt/data/ubuntu/research/env/lang/bin/python -m pytest tests/test_phase5_web.py -q`
  -> **6 passed**.
- `/mnt/data/ubuntu/research/env/lang/bin/python -m pytest -q`
  -> **26 passed, 3 skipped**.

Next eval:
- Rerun `python -m langgraph_rag.eval.run_eval --condition corpus_only`.
- Then rerun `python -m langgraph_rag.eval.run_eval --condition web_augmented`.
- Compare the new `eval_items_corpus_only.jsonl` and `eval_items_web_augmented.jsonl` per item,
  especially the curated recency questions.


## Phase 4 — Evaluation (corpus_only)
_2026-06-29 20:48:24_

**Condition: `corpus_only`** · golden items: 48

### Judge validity (judge vs human labels)
accuracy = **1.0**, Cohen's kappa = **1.0**
on 12 hand-labelled faithful/hallucinated cases. (Cases are clear-cut by
design; a production annotation set would be harder. This establishes the judge discriminates
grounded from hallucinated answers before we trust its scores below.)

### Retrieval (synthetic items, doc-level relevance)
| metric | value |
| --- | --- |
| mrr | 0.745 |
| recall@1 | 0.35 |
| hit@1 | 0.625 |
| ndcg@1 | 0.625 |
| recall@3 | 0.6771 |
| hit@3 | 0.85 |
| ndcg@3 | 0.6567 |
| recall@5 | 0.7771 |
| hit@5 | 0.925 |
| ndcg@5 | 0.7035 |
| recall@10 | 0.9208 |
| hit@10 | 0.975 |
| ndcg@10 | 0.7621 |

### Generation (LLM judge, answered items)
- faithfulness = **0.9712**
- answer_relevance = **0.9925**

### Citation
- has-citation rate (answered) = 0.975
- gold-doc-cited rate (synthetic answered) = 0.647

### Abstention
- abstain recall on unanswerable/out-of-scope = 1.0
- false-abstain rate on answerable = 0.0

### Web
- web trigger rate = 0.0
- web result rate = 0.0
- final context contains web rate = 0.0

### System
- latency mean = 3087 ms · p90 = 5945 ms


## Phase 5 — Evaluation (web_augmented)
_2026-06-29 20:55:32_

**Condition: `web_augmented`** · golden items: 48

### Judge validity (judge vs human labels)
accuracy = **1.0**, Cohen's kappa = **1.0**
on 12 hand-labelled faithful/hallucinated cases. (Cases are clear-cut by
design; a production annotation set would be harder. This establishes the judge discriminates
grounded from hallucinated answers before we trust its scores below.)

### Retrieval (synthetic items, doc-level relevance)
| metric | value |
| --- | --- |
| mrr | 0.745 |
| recall@1 | 0.35 |
| hit@1 | 0.625 |
| ndcg@1 | 0.625 |
| recall@3 | 0.6771 |
| hit@3 | 0.85 |
| ndcg@3 | 0.6567 |
| recall@5 | 0.7771 |
| hit@5 | 0.925 |
| ndcg@5 | 0.7035 |
| recall@10 | 0.9208 |
| hit@10 | 0.975 |
| ndcg@10 | 0.7621 |

### Generation (LLM judge, answered items)
- faithfulness = **0.9725**
- answer_relevance = **0.9963**

### Citation
- has-citation rate (answered) = 0.975
- gold-doc-cited rate (synthetic answered) = 0.647

### Abstention
- abstain recall on unanswerable/out-of-scope = 1.0
- false-abstain rate on answerable = 0.0

### Web
- web trigger rate = 0.042
- web result rate = 0.0
- final context contains web rate = 0.0

### System
- latency mean = 3877 ms · p90 = 8734 ms


## Phase 5 — Current A/B conclusion
_2026-06-29 21:02:00_

The post-mitigation A/B rerun shows that web search does **not** help yet.

Compared with `corpus_only`, `web_augmented` has tiny positive generation deltas, but no web
evidence was actually used:

- faithfulness: **0.9712 -> 0.9725** (`+0.0013`)
- answer relevance: **0.9925 -> 0.9963** (`+0.0038`)
- gold-doc-cited rate: **0.647 -> 0.647** (`+0.0`)
- web trigger rate: **0.042** (2/48 items)
- web result rate: **0.0**
- final web context rate: **0.0**
- latency mean: **3087 ms -> 3877 ms** (`+790 ms`)
- latency p90: **5945 ms -> 8734 ms** (`+2789 ms`)

Triggered rows:

| id | question | n_web_results | fallback |
| --- | --- | --- | --- |
| syn::adsk-1372ba28d2de4202879ac6fe982b8abf::0 | What are some new features in the latest release of Inventor® 3D CAD software? | 0 | corpus-only |
| curated::3 | What's the latest release for Maya? | 0 | corpus-only |

Decision:
- Keep `web.enabled=false` as the default.
- Treat the current DuckDuckGo HTML provider as insufficient for Phase 5 freshness coverage.
- Next useful work is provider/query improvement, not more threshold tuning: use a more reliable
  search API or add targeted Autodesk URL/query templates for product release/version pages.


## System graph artifacts
_2026-06-29 21:37:00_

Generated graph plots for the current RAG system:

- `reports/graphs/system_graph.svg` and `reports/graphs/system_graph.png`: full architecture plot
  showing corpus ingestion/indexes, runtime LangGraph flow, optional web augmentation, model
  services, and eval dependency.
- `reports/graphs/system_graph.dot`: Graphviz source.
- `reports/graphs/langgraph_corpus_only.mmd`: exact compiled graph with `web.enabled=false`.
- `reports/graphs/langgraph_web_augmented.mmd`: exact compiled graph with `web.enabled=true`.

Verification:
- `dot -Tsvg reports/graphs/system_graph.dot -o reports/graphs/system_graph.svg`
- `dot -Tpng reports/graphs/system_graph.dot -o reports/graphs/system_graph.png`
- Rendered PNG checked successfully: 1176 x 1512.


## README
_2026-06-30_

Added root `README.md` with:

- first-page architecture figure from `reports/graphs/system_graph.svg`
- project overview, repository layout, architecture summary, corpus statistics, and caveats
- environment installation for the existing `/mnt/data/ubuntu/research/env/lang` interpreter and a
  fresh Python 3.11 conda environment
- model-service startup/status commands via `serve_models.sh`
- commands for rebuilding corpus/chunks/indexes, running the CLI, running samples, tests, and eval
- links to `PLAN.md`, `reports/BUILD_REPORT.md`, `reports/eval_report_ab.md`, and
  `reports/sample_answers_corpus_only.md`


## UI Plan
_2026-06-30_

Added `UI-PLAN.md` as the tracking document for optional chat UI work.

Initial workstreams are all marked **NOT DONE**:

1. Transparent Chat UI
2. Persistent Conversation Memory
3. Human Feedback Loop
4. Caching + Latency/Cost View
5. Eval/Admin Dashboard

Tracking rule: when a workstream is completed, update `UI-PLAN.md`, add tests under `tests/`
when applicable, include any A/B or before/after comparison when meaningful, and append the
implementation details to this report.


## Phase 4 — Evaluation (corpus_only)
_2026-06-29 21:56:38_

**Condition: `corpus_only`** · golden items: 48

### Judge validity (judge vs human labels)
accuracy = **1.0**, Cohen's kappa = **1.0**
on 12 hand-labelled faithful/hallucinated cases. (Cases are clear-cut by
design; a production annotation set would be harder. This establishes the judge discriminates
grounded from hallucinated answers before we trust its scores below.)

### Retrieval (synthetic items, doc-level relevance)
| metric | value |
| --- | --- |
| mrr | 0.745 |
| recall@1 | 0.35 |
| hit@1 | 0.625 |
| ndcg@1 | 0.625 |
| recall@3 | 0.6771 |
| hit@3 | 0.85 |
| ndcg@3 | 0.6567 |
| recall@5 | 0.7771 |
| hit@5 | 0.925 |
| ndcg@5 | 0.7035 |
| recall@10 | 0.9208 |
| hit@10 | 0.975 |
| ndcg@10 | 0.7621 |

### Generation (LLM judge, answered items)
- faithfulness = **0.9712**
- answer_relevance = **0.9963**

### Citation
- has-citation rate (answered) = 0.975
- gold-doc-cited rate (synthetic answered) = 0.647

### Abstention
- abstain recall on unanswerable/out-of-scope = 1.0
- false-abstain rate on answerable = 0.0

### Web
- web trigger rate = 0.0
- web result rate = 0.0
- final context contains web rate = 0.0

### System
- latency mean = 2152 ms · p90 = 4616 ms


## Phase 5 — Evaluation (web_augmented)
_2026-06-29 22:00:29_

**Condition: `web_augmented`** · golden items: 48

### Judge validity (judge vs human labels)
accuracy = **1.0**, Cohen's kappa = **1.0**
on 12 hand-labelled faithful/hallucinated cases. (Cases are clear-cut by
design; a production annotation set would be harder. This establishes the judge discriminates
grounded from hallucinated answers before we trust its scores below.)

### Retrieval (synthetic items, doc-level relevance)
| metric | value |
| --- | --- |
| mrr | 0.745 |
| recall@1 | 0.35 |
| hit@1 | 0.625 |
| ndcg@1 | 0.625 |
| recall@3 | 0.6771 |
| hit@3 | 0.85 |
| ndcg@3 | 0.6567 |
| recall@5 | 0.7771 |
| hit@5 | 0.925 |
| ndcg@5 | 0.7035 |
| recall@10 | 0.9208 |
| hit@10 | 0.975 |
| ndcg@10 | 0.7621 |

### Generation (LLM judge, answered items)
- faithfulness = **0.97**
- answer_relevance = **0.9925**

### Citation
- has-citation rate (answered) = 0.975
- gold-doc-cited rate (synthetic answered) = 0.647

### Abstention
- abstain recall on unanswerable/out-of-scope = 1.0
- false-abstain rate on answerable = 0.0

### Web
- web trigger rate = 0.042
- web result rate = 0.0
- final context contains web rate = 0.0

### System
- latency mean = 2119 ms · p90 = 4565 ms


## UI Workstream 1 — Transparent Chat UI
_2026-06-30_

**Status: DONE.** Added a first local browser UI for chatting with the existing LangGraph RAG
pipeline.

Implemented:

- `langgraph_rag/app/streamlit_app.py`: Streamlit chat UI.
- `langgraph_rag/app/ui_adapter.py`: testable display-payload helpers that convert raw graph
  outputs into UI-ready answer, citation, context, and trace structures.
- `tests/test_ui_adapter.py`: no-live-service tests for UI helper behavior.
- `requirements.txt`: added `streamlit>=1.36`.
- `README.md`: added browser UI run command.
- `UI-PLAN.md`: Workstream 1 marked **DONE**.

UI behavior:

- chat input plus in-session chat history
- sidebar sample-question buttons
- clear-chat control
- cited answer display
- expandable sources
- expandable retrieved/final-context inspector with score, source type, product, page type, URL,
  and chunk id
- trace panel with top score, total latency, web trigger state, web result count, groundedness,
  and raw trace
- friendly model-service error message if the graph invocation fails

Run command:

```bash
cd /home/ubuntu/research/langgraph
/mnt/data/ubuntu/research/env/lang/bin/streamlit run langgraph_rag/app/streamlit_app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
```

Current local server:

- PID: `2369120`
- URL: `http://localhost:8501`
- Log: `logs/streamlit_ui.log`

Verification:

- Installed `streamlit 1.58.0` in `/mnt/data/ubuntu/research/env/lang`.
- `/mnt/data/ubuntu/research/env/lang/bin/python -m pytest tests/test_ui_adapter.py -q`
  -> **5 passed**.
- `/mnt/data/ubuntu/research/env/lang/bin/python -m pytest -q`
  -> **31 passed, 3 skipped**.
- `/mnt/data/ubuntu/research/env/lang/bin/python -m py_compile langgraph_rag/app/streamlit_app.py langgraph_rag/app/ui_adapter.py`
  -> passed.
- Streamlit startup log reports `Uvicorn server started on 0.0.0.0:8501`; `ss -ltnp` confirms
  `streamlit` listening on port `8501`.

A/B:

- Not applicable for this workstream. The UI wraps the existing graph without changing retrieval,
  reranking, generation, or evaluation behavior.

Known limitations:

- Conversation history is in Streamlit session memory only. Persistent sessions are Workstream 2.
- No thumbs up/down logging yet. Feedback is Workstream 3.
- No cache layer yet. Caching and latency/cost view are Workstream 4.
- The sandbox cannot make local HTTP requests to the Streamlit socket, so endpoint verification was
  done via process/port/log checks.

Follow-up fix:

- Added a project-root bootstrap to `langgraph_rag/app/streamlit_app.py` so `streamlit run
  langgraph_rag/app/streamlit_app.py ...` can import `langgraph_rag` reliably even when Streamlit
  executes the file as a script.
- Rechecked:
  - `/mnt/data/ubuntu/research/env/lang/bin/python -m py_compile langgraph_rag/app/streamlit_app.py langgraph_rag/app/ui_adapter.py`
  - `/mnt/data/ubuntu/research/env/lang/bin/python -m pytest tests/test_ui_adapter.py -q`
    -> **5 passed**.

User verification:

- User opened the web UI and confirmed it works on 2026-06-30.


## UI Workstream 2 — Persistent Conversation Memory
_2026-06-30_

**Status: DONE.** Added local persistent chat sessions for the Streamlit UI.

Implemented:

- `langgraph_rag/app/session_store.py`: local JSON session storage helpers.
- `langgraph_rag/app/streamlit_app.py`: sidebar controls for new/load/clear/delete chat sessions
  and automatic save after each user/assistant turn.
- `tests/test_session_store.py`: no-live-service tests for session persistence behavior.
- `UI-PLAN.md`: Workstream 2 marked **DONE**.
- `README.md`: documented local session storage path.

Storage:

- Directory: `data/ui/sessions/`.
- Format: one JSON file per session.
- Session fields:
  - `id`
  - `title`
  - `created_at`
  - `updated_at`
  - `messages`
- Message fields:
  - `role`
  - `content`
  - `created_at`
  - optional assistant `payload`
- Assistant payloads preserve citations, final contexts, metrics, grounding, and trace details so
  reloaded chats remain inspectable.

UI behavior:

- Users can create a new chat.
- Users can load a saved chat from the sidebar.
- Users can clear the current chat.
- Users can delete the current chat.
- Loaded messages are converted back to graph `chat_history`, so follow-up questions can use prior
  turns after reload.
- Session titles are derived from the first user message.
- Storage is local-only; no external logging was added.

Summarization:

- Deferred. This first pass stores complete messages. Long-session summarization remains optional
  future work if sessions grow large enough to pressure the query-rewrite context.

Verification:

- `/mnt/data/ubuntu/research/env/lang/bin/python -m pytest tests/test_session_store.py tests/test_ui_adapter.py -q`
  -> **9 passed**.
- `/mnt/data/ubuntu/research/env/lang/bin/python -m pytest -q`
  -> **35 passed, 3 skipped**.
- `/mnt/data/ubuntu/research/env/lang/bin/python -m py_compile langgraph_rag/app/streamlit_app.py langgraph_rag/app/ui_adapter.py langgraph_rag/app/session_store.py`
  -> passed.

A/B:

- Not applicable for this workstream. Persistent memory changes UI/session behavior but does not
  change retrieval, reranking, generation, or eval metrics.

Before/after behavior:

- Before: refreshing/restarting the UI lost the chat.
- After: sessions persist in `data/ui/sessions/` and can be reloaded from the UI sidebar.

Current local server:

- PID: `2823094`
- URL: `http://localhost:8501`
- Log: `logs/streamlit_ui.log`


## UI Workstream 3 — Human Feedback Loop
_2026-06-30_

**Status: DONE.** Added local per-answer feedback capture for the Streamlit UI.

Implemented:

- `langgraph_rag/app/feedback_store.py`: append-only JSONL feedback queue helpers.
- `langgraph_rag/app/streamlit_app.py`: per-assistant-answer feedback controls with positive,
  negative, and optional free-text comment inputs.
- `tests/test_feedback_store.py`: no-live-service tests for feedback record and JSONL behavior.
- `UI-PLAN.md`: Workstream 3 marked **DONE**.
- `README.md`: documented feedback storage path and current test status.

Storage:

- File: `data/ui/feedback.jsonl`.
- Format: one JSON object per feedback submission.
- Records include:
  - feedback id and UTC timestamp
  - `review_status`
  - session id and turn id
  - user message index/id and assistant message index/id
  - query and answer text
  - label: `positive` or `negative`
  - optional reviewer/user comment
  - citations
  - final context ids
  - source URLs
  - trace, metrics, top score, total latency, and abstention flag

UI behavior:

- Each assistant response has a Feedback expander.
- Users can submit positive or negative feedback.
- Users can add an optional comment before submitting.
- Saved feedback is independent from saved chat sessions, so reviewing the queue does not mutate
  `data/ui/sessions/`.
- Negative examples can be filtered with `load_feedback(path, label="negative")`.

Current local server:

- PID: `2892838`
- URL: `http://localhost:8501`
- Log: `logs/streamlit_ui.log`

Verification:

- `/mnt/data/ubuntu/research/env/lang/bin/python -m pytest tests/test_feedback_store.py tests/test_session_store.py tests/test_ui_adapter.py -q`
  -> **14 passed**.
- `/mnt/data/ubuntu/research/env/lang/bin/python -m pytest -q`
  -> **40 passed, 3 skipped**.
- `/mnt/data/ubuntu/research/env/lang/bin/python -m py_compile langgraph_rag/app/streamlit_app.py langgraph_rag/app/ui_adapter.py langgraph_rag/app/session_store.py langgraph_rag/app/feedback_store.py`
  -> passed.

A/B:

- Not applicable for this first logging pass. The feedback queue is now in place so later prompt,
  retrieval, or UI variants can compare positive/negative rates against the same JSONL schema.


## UI Workstream 4 — Latency Counter Slice
_2026-06-30_

**Status: DEFERRED after requested slice.** Implemented the visible latency-counter portion of
Workstream 4 and deferred caching/cost work by user request so the project can move to the
Eval/Admin dashboard.

Implemented:

- `langgraph_rag/app/ui_adapter.py`: added `stage_latency_ms(...)`.
- `langgraph_rag/app/streamlit_app.py`: Trace panel now shows:
  - retrieval latency
  - rerank latency
  - generation latency
  - web latency
  - total latency
- `tests/test_ui_adapter.py`: added coverage for per-stage latency extraction and missing-stage
  defaults.
- `UI-PLAN.md`: Workstream 4 marked **DEFERRED** with latency slice completed and caching/cost
  scope postponed.

Deferred by request:

- query embedding cache
- retrieval/rerank cache
- exact-answer cache
- cache keys and invalidation rules
- token/cost estimates
- before/after cache latency comparison

Verification:

- `/mnt/data/ubuntu/research/env/lang/bin/python -m pytest tests/test_ui_adapter.py -q`
  -> **6 passed**.

A/B:

- Not applicable for this latency-only UI slice. It exposes existing trace timings and does not
  change retrieval, reranking, generation, or answer content.


## UI Workstream 5 — Eval/Admin Dashboard
_2026-06-30_

**Status: DONE.** Added a local Admin view for evaluation reports, A/B deltas, sample answers,
feedback review, and source artifact paths.

Implemented:

- `langgraph_rag/app/admin_dashboard.py`: pure loader/summary helpers for report JSON,
  A/B deltas, sample-answer markdown, and feedback JSONL.
- `langgraph_rag/app/streamlit_app.py`: sidebar view switch between Chat and Admin.
- `tests/test_admin_dashboard.py`: no-live-service tests for dashboard payload construction.
- `README.md`: documented the Admin view and updated test status.
- `UI-PLAN.md`: Workstream 5 marked **DONE**.

Dashboard tabs:

- Corpus-only eval: key metric cards plus flattened metric table.
- Web-augmented eval: key metric cards plus flattened metric table.
- A/B: rows from `reports/eval_report_ab.json`.
- Feedback: total/positive/negative/new counts plus recent review records, defaulting to negative
  examples.
- Samples: rendered `reports/sample_answers_corpus_only.md`.
- Files: source artifact paths and existence checks.

Design notes:

- The dashboard reads existing artifacts and does not recompute hidden metrics.
- A/B deltas come directly from `reports/eval_report_ab.json`.
- Feedback records come from `data/ui/feedback.jsonl`.
- The A/B tab highlights current caveats:
  - current web provider produced no final web evidence
  - recency questions can be stale in corpus-only/default mode
  - judge validation is a smoke test, not production human review

Current local server:

- PID: `3069661`
- URL: `http://localhost:8501`
- Log: `logs/streamlit_ui.log`

Verification:

- `/mnt/data/ubuntu/research/env/lang/bin/python -m pytest tests/test_admin_dashboard.py tests/test_ui_adapter.py -q`
  -> **11 passed**.
- `/mnt/data/ubuntu/research/env/lang/bin/python -m pytest -q`
  -> **46 passed, 3 skipped**.
- `/mnt/data/ubuntu/research/env/lang/bin/python -m py_compile langgraph_rag/app/streamlit_app.py langgraph_rag/app/ui_adapter.py langgraph_rag/app/admin_dashboard.py`
  -> passed.

A/B:

- Existing A/B report is displayed as-is. The dashboard does not introduce another evaluation
  calculation path, so it cannot drift from the saved report JSON.
