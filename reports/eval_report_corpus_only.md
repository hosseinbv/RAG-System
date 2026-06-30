# Corpus-only evaluation report

Source: `reports/eval_report_corpus_only.json`

## Summary

The corpus-only RAG baseline was evaluated on 48 golden items: 40 synthetic source-grounded
questions and 8 curated sample/hard questions. The current baseline is strong enough to treat
Phase 4 as complete for the project milestone, with citation precision and broader manual judge
validation left as improvement items.

## Results

| Area | Metric | Value |
| --- | --- | --- |
| Retrieval | MRR | 0.745 |
| Retrieval | Hit@1 | 0.625 |
| Retrieval | Hit@3 | 0.85 |
| Retrieval | Hit@5 | 0.925 |
| Retrieval | Hit@10 | 0.975 |
| Generation | Faithfulness | 0.9821 |
| Generation | Answer relevance | 0.9949 |
| Citation | Has-citation rate | 0.974 |
| Citation | Gold-doc-cited rate | 0.697 |
| Abstention | Recall on unanswerable/out-of-scope | 1.0 |
| Abstention | False-abstain rate on answerable | 0.0 |
| System | Mean latency | 2037 ms |
| System | P90 latency | 4090 ms |

## Citation interpretation

`has_citation_rate=0.974` means nearly every non-abstained answer included at least one parsed
inline citation like `[1]`.

`gold_doc_cited_rate=0.697` is stricter: among answered synthetic items, 69.7% cited a chunk from
the exact source document used to generate the eval question. The gap means answers usually cite
sources, but they do not always cite the synthetic gold document. This can happen when multiple
Autodesk pages repeat the same product facts, or when retrieval finds a valid overlapping source
instead of the original synthetic source.

## Judge validity

The judge scored 12 clear-cut hand-labelled faithful/hallucinated cases with:

- Accuracy: 1.0
- Cohen's kappa: 1.0

This validates that the judge can separate obvious grounded vs hallucinated answers, but it is not
yet a substitute for a 30-50 item production-style manual review set.

## Remaining Phase 4 polish

- Save per-item eval outputs for easier failure analysis.
- Review a 30-50 item subset by hand and report agreement on realistic borderline cases.
- Improve source precision so gold-doc citation rises without hurting faithfulness.
- Optionally revise retrieval metrics to compute relevant chunk IDs from the full index rather
  than only from retrieved candidates.
