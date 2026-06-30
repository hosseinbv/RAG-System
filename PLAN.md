# Company RAG Chatbot — Build Plan

> Snapshot corpus: `/home/ubuntu/research/langgraph/pages` — 1,218 HTML files (~1,049 unique),
> Company product/support pages, crawled **Dec 2023**. Canonical URLs + titles present.

## 0. Design principles (the part that makes it expandable)

The whole system is built around **swappable components behind stable interfaces**, so that
removing a non-major node never blocks the rest, and adding a new one is config + one class.

Three mechanisms enforce this:

1. **Interfaces + registry.** Every component implements an ABC (`BaseRetriever`,
   `BaseReranker`, `BaseGenerator`, `BaseGuard`, `BaseJudge`, `BaseLogger`). Concrete classes
   register by name; the factory builds them from `config/settings.yaml`. Swap an
   implementation by changing a string — no code edits elsewhere.
2. **Config-driven graph assembly.** Each *optional* node has an `enabled` flag. `build_graph()`
   only wires enabled nodes and reroutes edges around disabled ones (passthrough). Turn the
   reranker, web-retriever, or grounding guard off → the graph still runs end to end.
3. **OpenAI-compatible model endpoints.** Generator, judge, embeddings, reranker are all reached
   via `base_url` + model name (served by vLLM). Changing Qwen3-4B → 8B is a config line.

Graph state is a single `TypedDict`; optional keys are checked-for, and nodes **degrade
gracefully** when an upstream optional node didn't run.

### Repository layout
```
langgraph_rag/
  config/settings.yaml        # feature flags, endpoints, thresholds — single source of truth
  core/
    state.py                  # GraphState TypedDict
    interfaces.py             # ABCs for every pluggable component
    registry.py               # name -> class factory, built from config
  ingest/
    clean.py                  # junk/lang filter + main-content extraction (trafilatura)
    metadata.py               # canonical-URL -> {url, product, page_type, title, snapshot_date}
    chunk.py                  # structure-aware (heading-based) chunking
    build_index.py            # embed -> vector store (+ BM25 sidecar)
  retrieval/{dense,bm25,hybrid,web}.py   # web.py optional
  rerank/{qwen_reranker,passthrough}.py  # passthrough = no-op when disabled
  generate/{generator,prompts}.py
  guards/{abstention,grounding}.py
  graph/{nodes,build_graph}.py
  eval/{golden_set,judge,metrics,run_eval,report}.py
  app/{cli,api}.py            # api/streamlit optional
  obs/logger.py               # JSONL trace per query
  requirements.txt
```

---

## PRIMARY PLAN (get a correct, evaluated system running)

Order is by leverage. Each phase ends with something runnable + a deliverable artifact.

### Phase 0 — Scaffold (skeleton that makes everything pluggable)  ✅ DONE
- `core/config.py`, `core/interfaces.py`, `core/registry.py`, `core/state.py`, `config/settings.yaml`,
  `obs/report.py`, `requirements.txt`. Tests: `tests/test_phase0_scaffold.py` (4 passed).
- vLLM serving for generator (Qwen3-4B-Instruct-2507), embeddings (Qwen3-Embedding-0.6B),
  reranker (Qwen3-Reranker-0.6B), judge (Qwen3-8B) — all OpenAI-compatible. _[deferred to when first needed]_

### Phase 1 — Ingestion (highest quality leverage)
**Phase 1a ✅ DONE** — 1218 raw → **729 clean docs**. Dual-strategy extraction
(trafilatura primary, bs4 fallback). Dropped: 238 JS-shell support pages (unrecoverable
from static HTML — documented), 184 dup-content, 64 legal/terms, 2 tiny, 1 non-English.
Metadata (url/product/page_type) derived from canonical URLs. Tests: 6 passed.
Artifacts: `data/clean_docs.jsonl`, `reports/corpus_stats.md`.
- **Filter junk:** drop the Incapsula block page, files < 3 KB, non-English (`lang`/path `/en/`).
- **Dedupe:** exact (md5) now; near-dup (MinHash) deferred to optional.
- **Extract main content** with trafilatura/readability → strip nav/footer/cookie/legal chrome.
- **Metadata from canonical URL:** `url`, `product` (path seg 2), `page_type` (path seg 1),
  `title`, `snapshot_date=2023-12-16`. Store on every chunk.
- **Document selection (documented rationale):** keep `products/*`, `support/*`, `collections/*`,
  `blogs/*`, `learning/*`; **drop** `company/legal-*`, `terms-of-use`, pure-nav pages.
- **Structure-aware chunking** on HTML headings (h1/h2/h3), ~512-token target w/ overlap.
- **Exit + deliverable:** `corpus_stats.md` (counts kept/dropped per page_type, chunk histogram)
  and a built index. This table *is* the "document selection" reflection deliverable.

**Phase 1b ✅ DONE** — 729 docs → **1494 chunks** (paragraph-packed, title-prefixed).
Dense (Qwen3-Embedding-0.6B, 1024-d) + BM25 indexes built; HybridRetriever (RRF) verified.
Models served via vLLM in base env behind a per-process torchaudio stub (no shared pkg touched).

### Phase 2 — Core RAG, corpus-only  ✅ DONE
LangGraph `retrieve→rerank→generate` live. Hybrid retrieval (RRF), Qwen3-Reranker (fixed via
hf-overrides for proper P(yes) scores), grounded generation w/ inline [n] citations parsed back
to URLs. 5 sample Qs answered; pricing & out-of-scope correctly abstain; "latest Maya" exposes the
stale-corpus trap. CLI + sample-answer deliverables. Tests: 4 passed (incl. gated e2e).

- **Hybrid retrieve:** dense (Qwen3-Embedding) + BM25, fused via **RRF**. (BM25 matters for exact
  tokens like "AutoCAD LT", version strings.)
- **Rerank:** Qwen3-Reranker-0.6B cross-encoder, top-k → top-n.
- **Generate** with citations: answer must cite chunk URLs; prompt forbids unsupported claims.
- LangGraph wiring: `rewrite → retrieve → rerank → generate → cite`.
- **Exit + deliverable:** answers to the 5 sample questions with sources.

### Phase 3 — Conversation + guards (anti-hallucination, abstention)  ✅ DONE
Guards wired as independent, toggle-able LangGraph nodes (collapses to Phase 2 core when off).
Conversation rewrite resolves follow-up pronouns; two-layer abstention (retrieval-confidence gate
+ generator grounding prompt); grounding guard (judge=Qwen3-8B ≠ generator) annotates per-claim
groundedness and caught a real Mac over-claim. Full suite: 23 passed.

- **Conversation rewrite** node: rewrite follow-ups to standalone queries — but only when
  context-dependent (pronoun/ellipsis heuristic) so standalone queries aren't corrupted.
- **Abstention** node: if max rerank score < threshold → "not in the documentation" instead of
  guessing. Tunable threshold (calibrated in Phase 4).
- **Grounding guard** (PoC level): LLM check that the answer's claims are supported by retrieved
  context; flag/strip unsupported sentences. (Upgrade to sentence-level NLI = optional.)
- **Exit:** multi-turn transcript demo + correct abstention on out-of-scope query.

### Phase 4 — Evaluation harness (the differentiator)  ✅ DONE
**Status:** corpus-only baseline completed on **48 golden items** (40 synthetic + 8 curated).
Artifacts: `data/golden_set.jsonl`, `reports/eval_report_corpus_only.json`,
`reports/eval_report_corpus_only.md`, and appended sections in `reports/BUILD_REPORT.md`.

Headline results: retrieval `hit@10=0.975`, `mrr=0.745`; generation `faithfulness=0.9821`,
`answer_relevance=0.9949`; citation `has_citation_rate=0.974`, `gold_doc_cited_rate=0.697`;
abstention recall on unanswerable/out-of-scope = `1.0`; false-abstain on curated answerable = `0.0`;
latency mean/p90 = `2037/4090 ms`.

Notes/caveats: judge validation currently uses 12 clear-cut hand-labelled examples
(`accuracy=1.0`, `Cohen's kappa=1.0`), not yet a full 30-50 production-style manual review.
`gold_doc_cited_rate` is intentionally strict: answers may be faithful while citing an overlapping
Autodesk page instead of the exact synthetic source document.

- **Golden set:** local LLM (Qwen3-8B) generates `question → (answer, source_chunk_id)` from
  sampled chunks, stratified by product + question-type (factual/comparison/recency/how-to).
  **Hand-verify ~30–50**; add human-authored **hard + unanswerable** questions (pricing,
  "latest release") so the set isn't optimistically self-consistent.
- **Metrics:**
  - Retrieval: Recall@k, MRR, nDCG (using golden source labels), context relevance.
  - Generation: faithfulness/groundedness, answer relevance, citation correctness.
  - Abstention: precision/recall on "should-refuse".
  - System: latency, est. cost/tokens per query, failure-mode log.
- **Judge validity (required by brief):** hand-label ~30 examples, report **judge-vs-human
  agreement (Cohen's κ / accuracy)**. Judge = Qwen3-8B ≠ generator.
- **Exit + deliverable:** `eval_report_corpus_only.md` / `.json` — the corpus-only baseline.

### Phase 5 — Web augmentation + A/B  🚧 IMPLEMENTED, LIVE A/B PENDING
**Status:** web fallback code and tests are implemented. The goal remains to keep the current
corpus-first graph intact and add web augmentation as an optional, confidence-driven fallback.
The corpus-only path continues to run unchanged when `web.enabled=false`.

Implemented artifacts:
- `retrieval/web.py` — DuckDuckGo HTML no-key web retriever, restricted by allowed domains,
  returning normal `Chunk(source="web")` objects.
- `graph/nodes.py` — web trigger, web retrieval, merge/rerank, and trace fields.
- `graph/build_graph.py` — optional web branch wired only when `web.enabled=true`.
- `generate/prompts.py` — source labels distinguish Dec-2023 corpus snapshot vs live web.
- `eval/run_eval.py` — `web_augmented` condition, per-item JSONL outputs, and A/B report writer.
- `tests/test_phase5_web.py` — deterministic no-network unit tests. Full non-live suite:
  **26 passed, 3 skipped**.

Live A/B first pass:
- `web_augmented` completed on 48 items and produced
  `reports/eval_report_web_augmented.json`, `reports/eval_items_web_augmented.jsonl`,
  `reports/eval_report_ab.md`, and `reports/eval_report_ab.json`.
- Result regressed vs the older corpus-only aggregate: faithfulness **0.9821 -> 0.955**,
  answer relevance **0.9949 -> 0.9887**, gold-doc-cited rate **0.697 -> 0.588**, and
  latency mean **2037 ms -> 3615 ms**.
- Diagnosis: web triggered on **14.6%** of queries but only reached final contexts on **4.2%**.
  Several triggered searches returned no web pages, and generic subscription/cost wording was too
  broad as a recency trigger.

Mitigation applied:
- `config/settings.yaml`: recency trigger terms now focus on real freshness wording
  (`latest/current/today/release/version`) instead of generic subscription/cost terms.
- `graph/nodes.py`: if web search returns no usable chunks, the graph preserves the existing
  corpus reranked contexts instead of reranking a broader candidate pool.
- `graph/nodes.py`: when web chunks exist, merge them with already reranked corpus contexts for a
  more conservative final rerank.
- `tests/test_phase5_web.py`: added regression tests for high-confidence subscription queries and
  empty-web-result fallback. Verification: **26 passed, 3 skipped**.

Post-mitigation A/B rerun:
- Current-code `corpus_only` and `web_augmented` were rerun on the same 48 items.
- Quality was effectively unchanged: faithfulness **0.9712 -> 0.9725**, answer relevance
  **0.9925 -> 0.9963**, and gold-doc-cited rate **0.647 -> 0.647**.
- Web did **not** supply evidence: trigger rate **0.042** (2/48), web result rate **0.0**, and
  final web context rate **0.0**.
- Latency worsened: mean **3087 ms -> 3877 ms**, p90 **5945 ms -> 8734 ms**.
- Triggered rows were the Inventor latest-release synthetic item and curated "What's the latest
  release for Maya?"; both had `n_web_results=0` and fell back to corpus-only contexts.

Conclusion:
- Current web augmentation is safe after the fallback fix, but the DuckDuckGo HTML search branch is
  not useful yet. Keep it off by default until the provider/querying layer can reliably return
  Autodesk pages for freshness questions.

**Subplan:**

1. **Add web configuration.** ✅
   - Extend `config/settings.yaml` with provider settings, allowed domains, result limits,
     fetch timeouts, and trigger rules.
   - Keep `web.enabled=false` by default until tests and reports are ready.
   - Suggested fields: `provider`, `allowed_domains: [autodesk.com]`, `top_k`, `fetch_pages`,
     `trigger_max_score`, `recency_terms`, `in_domain_terms`.

2. **Implement `retrieval/web.py`.** ✅
   - Add `WebRetriever(BaseRetriever)` that returns `Chunk` objects with `source="web"`.
   - Search should be restricted to Autodesk/current product pages where possible.
   - Prefer fetching top result pages and extracting main content over using only search snippets.
   - Store URL/title/page_type/product metadata so citations work the same as corpus citations.
   - Provide a no-op/stub path for tests so normal unit tests do not require live internet.

3. **Add web routing logic to LangGraph.** ✅
   - Current graph: `rewrite -> retrieve -> rerank -> abstain/generate -> ground`.
   - Target graph when web is enabled:
     `rewrite -> retrieve -> rerank -> web_gate -> web_retrieve? -> merge/rerank -> generate -> ground`.
   - `web_gate` should trigger on:
     - corpus top rerank score below `web.trigger_max_score`, and query looks in-domain; or
     - recency-sensitive wording such as "latest", "newest", "current", "today", "release".
   - It should not web-search obvious out-of-domain questions like "capital of France".

4. **Merge and rerank contexts.** ✅
   - Combine corpus contexts and web contexts.
   - Reuse the existing Qwen reranker over the merged candidates.
   - Keep trace fields: `web_triggered`, `web_reason`, `n_web_results`, `web_ms`,
     `final_context_sources`.

5. **Update generation prompts.** ✅
   - Label corpus sources as Dec-2023 snapshot sources and web sources as live/current sources.
   - For recency questions, instruct the generator to prefer web sources over stale corpus sources.
   - Preserve the existing citation format so parser/eval logic still works.

6. **Update evaluation for A/B.** ✅
   - Extend `eval/run_eval.py` so `--condition web_augmented` enables web in config.
   - Save per-item outputs for both conditions (`reports/eval_items_corpus_only.jsonl`,
     `reports/eval_items_web_augmented.jsonl`) to inspect failures.
   - Add an A/B report writer comparing corpus-only vs web-augmented:
     retrieval/generation/citation/abstention/latency plus web trigger rate.
   - Highlight curated recency questions, especially the Maya latest-release stale-corpus case.

7. **Add tests.** ✅
   - Pure unit tests for recency/in-domain trigger logic.
   - Stubbed `WebRetriever` test that returns deterministic web chunks.
   - Graph-routing test proving web can be toggled off and on by config.
   - Eval writer test for A/B report shape.
   - Optional gated live-web test (`WEB_STACK_UP=1`) if an external provider is configured.

8. **Deliverables and bookkeeping.** 🚧
   - `reports/eval_report_ab.md` and `.json`.
   - Optional `reports/sample_answers_web_augmented.md`.
   - Update `PLAN.md` and append `reports/BUILD_REPORT.md` after implementation.

- `web.py` retriever (privacy-respecting search; zero-retention). **Confidence-driven fallback:**
  trigger web only when corpus rerank confidence is low — *not* an upfront classifier guess.
- Re-run the same golden set with web on. **Deliverable:** `eval_report_ab.md` — corpus-only vs
  web-blended delta, highlighting recency questions (e.g. "latest Maya release").
- **Exit:** the two required response sets + their comparison.

**Primary plan done = full task satisfied:** running RAG, both response sets, evaluation results,
and the reflections (selection, preprocessing, architecture, eval) backed by real artifacts.

---

## OPTIONAL / FUTURE PLAN (apply if time remains; otherwise "what I'd do next")

Each is independent and additive — none blocks the primary system.

- **Routing as a learned classifier** (in addition to confidence fallback) for cleaner
  out-of-scope detection.
- **Sentence-level NLI grounding** (entailment model) replacing the LLM grounding check.
- **Query decomposition** for comparison questions ("AutoCAD vs Revit" → two sub-retrievals).
- **Metadata-filtered retrieval** (filter by `product`/`page_type` when query names a product).
- **Near-duplicate removal** (MinHash/SimHash) + semantic dedup of chunks.
- **Freshness/recency detector** node that auto-flags time-sensitive queries → force web.
- **Persistent conversation memory** store + summarization for long sessions.
- **Transparent UI** (Streamlit/FastAPI): show retrieved chunks, scores, and source links;
  let users inspect/expand citations.
- **Human feedback loop:** thumbs up/down logged with query+sources+answer → review queue that
  feeds the golden set; basis for later personalization.
- **Caching** (embedding + answer cache) and a **cost/latency dashboard**.
- **Eval dashboard** + regression gate in CI (fail build if faithfulness drops).
- **Reranker/threshold tuning** sweep; hybrid-fusion weight search.

---

## Model stack (final)
- Generator: **Qwen3-4B-Instruct-2507** (vLLM, OpenAI-compatible).
- Embeddings: **Qwen3-Embedding-0.6B** + **BM25** → RRF hybrid.
- Reranker: **Qwen3-Reranker-0.6B**.
- Judge: **Qwen3-8B** — must differ from generator to avoid self-evaluation bias.
- Vector store: **Chroma or FAISS** (corpus is small; either is fine).
- All local → satisfies the no-data-retention requirement by construction.
