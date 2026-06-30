# Corpus-only vs web-augmented A/B report

| metric | corpus_only | web_augmented | delta |
| --- | --- | --- | --- |
| mrr | 0.745 | 0.745 | 0.0 |
| hit@10 | 0.975 | 0.975 | 0.0 |
| faithfulness | 0.9712 | 0.97 | -0.0012 |
| answer_relevance | 0.9963 | 0.9925 | -0.0038 |
| has_citation_rate | 0.975 | 0.975 | 0.0 |
| gold_doc_cited_rate | 0.647 | 0.647 | 0.0 |
| abstain_recall | 1.0 | 1.0 | 0.0 |
| false_abstain | 0.0 | 0.0 | 0.0 |
| latency_mean_ms | 2152 | 2119 | -33 |
| latency_p90_ms | 4616 | 4565 | -51 |
| web_trigger_rate | 0.0 | 0.042 | 0.042 |
| final_web_context_rate | 0.0 | 0.0 | 0.0 |

Notes:
- Positive quality deltas are good for retrieval, generation, citation, and abstention recall.
- Lower latency deltas are good.
- Web trigger/context rates are expected to be null or zero for corpus-only and nonzero for web.
- Inspect `eval_items_web_augmented.jsonl` for recency examples such as latest release questions.
