"""LLM-as-judge for generation quality, plus judge VALIDATION.

Metrics per answer (judge = Qwen3-8B, different model from the generator):
  - faithfulness:    is every claim supported by the retrieved contexts? [0,1]
  - answer_relevance: does the answer actually address the question? [0,1]
  - (citation_correctness is computed structurally in run_eval from parsed citations)

Validity (the brief's "how to evaluate its validity"): we cannot trust an unvalidated
LLM judge, so `validate_judge` runs it on a small hand-labelled set and reports agreement
(accuracy + Cohen's kappa) with the human labels. Labels here are author-curated proxies;
in production these would come from real annotators.
"""
from __future__ import annotations

from openai import OpenAI

from ..core.config import load_config
from ..core.interfaces import BaseJudge
from ..core.llm import chat, parse_json
from ..core.registry import register

_SYS = (
    "You are a strict RAG answer evaluator. Given a QUESTION, the CONTEXTS the system "
    "retrieved, and the ANSWER it produced, score two things from 0.0 to 1.0:\n"
    "- faithfulness: fraction of the answer's factual claims that are directly supported by "
    "the CONTEXTS (1.0 = fully grounded, 0.0 = unsupported/contradicted).\n"
    "- answer_relevance: how well the answer addresses the QUESTION (1.0 = directly answers).\n"
    "A correct refusal when the contexts truly lack the answer is faithful (1.0). "
    'Respond as JSON: {"faithfulness": <float>, "answer_relevance": <float>, "reason": "..."}'
)


@register("judge", "qwen")
class GenerationJudge(BaseJudge):
    def __init__(self, cfg=None):
        cfg = cfg or load_config()
        jc = cfg.get_path("models.judge")
        self.client = OpenAI(base_url=jc["base_url"], api_key=jc.get("api_key", "EMPTY"))
        self.model = jc["model"]

    def score(self, sample: dict) -> dict:
        ctx = "\n\n".join(f"[{i+1}] {c}" for i, c in enumerate(sample.get("contexts", [])))
        user = (f"QUESTION: {sample['question']}\n\nCONTEXTS:\n{ctx}\n\n"
                f"ANSWER: {sample['answer']}")
        data = parse_json(chat(self.client, self.model, _SYS, user, max_tokens=400)) or {}
        return {
            "faithfulness": _clip(data.get("faithfulness")),
            "answer_relevance": _clip(data.get("answer_relevance")),
        }


def _clip(x) -> float:
    try:
        return max(0.0, min(1.0, float(x)))
    except (TypeError, ValueError):
        return 0.0


# --- judge validation ----------------------------------------------------------
# Hand-labelled cases: clearly faithful (label 1) vs clearly unfaithful (label 0).
VALIDATION_CASES = [
    # faithful: answer supported by context
    {"question": "Does AutoCAD LT do 3D?", "contexts": ["AutoCAD LT is 2D drafting software; it does not include 3D modeling."],
     "answer": "No, AutoCAD LT is 2D only and does not do 3D.", "human_faithful": 1},
    {"question": "Is Fusion 360 cloud-based?", "contexts": ["Fusion 360 is a cloud-based 3D CAD, CAM, and CAE platform."],
     "answer": "Yes, Fusion 360 is cloud-based.", "human_faithful": 1},
    {"question": "What is Maya used for?", "contexts": ["Maya is software for 3D animation, modeling, and rendering."],
     "answer": "Maya is used for 3D animation, modeling, and rendering.", "human_faithful": 1},
    {"question": "Does Revit support BIM?", "contexts": ["Revit is BIM software for architects and engineers."],
     "answer": "Yes, Revit is BIM software.", "human_faithful": 1},
    {"question": "What does Civil 3D do?", "contexts": ["Civil 3D supports civil engineering design and documentation."],
     "answer": "Civil 3D supports civil engineering design and documentation.", "human_faithful": 1},
    {"question": "Price of AutoCAD?", "contexts": ["AutoCAD is 2D and 3D CAD software used by professionals."],
     "answer": "I don't have enough information in the documentation to answer that.", "human_faithful": 1},
    # unfaithful: answer adds claims not in context (hallucination)
    {"question": "How much does Fusion 360 cost?", "contexts": ["Fusion 360 is a cloud-based CAD/CAM tool."],
     "answer": "Fusion 360 costs $545 per year.", "human_faithful": 0},
    {"question": "Does AutoCAD LT do 3D?", "contexts": ["AutoCAD LT is 2D drafting software."],
     "answer": "Yes, AutoCAD LT has full 3D modeling and rendering.", "human_faithful": 0},
    {"question": "What is Maya's latest version?", "contexts": ["Maya is 3D animation software."],
     "answer": "The latest version of Maya is Maya 2026, released last week.", "human_faithful": 0},
    {"question": "Is Revit free?", "contexts": ["Revit is BIM software for building design."],
     "answer": "Yes, Revit is completely free for everyone forever.", "human_faithful": 0},
    {"question": "Does Inventor run on Linux?", "contexts": ["Inventor is mechanical design software for Windows."],
     "answer": "Yes, Inventor runs natively on Linux, macOS, and Windows.", "human_faithful": 0},
    {"question": "What is Navisworks?", "contexts": ["Navisworks is project review software for AEC."],
     "answer": "Navisworks is a video game developed by Autodesk in 1998.", "human_faithful": 0},
]


def validate_judge(threshold: float = 0.5) -> dict:
    """Run the judge on labelled cases; report accuracy + Cohen's kappa vs human labels."""
    judge = GenerationJudge()
    preds, gold = [], []
    rows = []
    for case in VALIDATION_CASES:
        s = judge.score(case)
        pred = 1 if s["faithfulness"] >= threshold else 0
        preds.append(pred)
        gold.append(case["human_faithful"])
        rows.append({"q": case["question"], "human": case["human_faithful"],
                     "judge_faithfulness": s["faithfulness"], "pred": pred})
    acc = sum(int(p == g) for p, g in zip(preds, gold)) / len(gold)
    return {"accuracy": round(acc, 3), "cohen_kappa": round(_cohen_kappa(gold, preds), 3),
            "n": len(gold), "threshold": threshold, "rows": rows}


def _cohen_kappa(a: list[int], b: list[int]) -> float:
    n = len(a)
    po = sum(int(x == y) for x, y in zip(a, b)) / n
    # expected agreement
    pe = 0.0
    for cls in (0, 1):
        pa = a.count(cls) / n
        pb = b.count(cls) / n
        pe += pa * pb
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


if __name__ == "__main__":
    import json
    print(json.dumps(validate_judge(), indent=2))
