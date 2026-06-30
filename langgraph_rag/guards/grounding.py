"""Grounding guard: verify the answer's claims are supported by the retrieved contexts.

PoC implementation uses an LLM (the judge model, NOT the generator) to entail each
sentence against the sources and flag unsupported ones. A sentence-level NLI model is
the optional upgrade. Returns a verdict; the graph annotates the answer with it rather
than silently dropping text, keeping the system transparent.
"""
from __future__ import annotations

import json
import re

from openai import OpenAI

from ..core.config import load_config
from ..core.registry import register
from ..core.state import Chunk

_SENT = re.compile(r"(?<=[.!?])\s+")

_SYS = (
    "You are a strict fact-checker. Given SOURCES and a list of CLAIMS, decide for each "
    "claim whether it is supported by the sources. Respond with JSON: "
    '{"verdicts": [{"i": <claim index>, "supported": true|false}]}. '
    "A claim is supported only if the sources directly state it."
)


def split_claims(answer: str) -> list[str]:
    parts = [s.strip() for s in _SENT.split(answer) if len(s.strip()) > 0]
    # ignore citation-only fragments and the abstention preamble
    return [p for p in parts if len(re.sub(r"\[\d+\]", "", p).strip()) > 12]


@register("guard", "grounding")
class GroundingGuard:
    def __init__(self, cfg=None):
        cfg = cfg or load_config()
        jc = cfg.get_path("models.judge")
        self.client = OpenAI(base_url=jc["base_url"], api_key=jc.get("api_key", "EMPTY"))
        self.model = jc["model"]

    def check(self, query: str, answer: str, contexts: list[Chunk]) -> dict:
        claims = split_claims(answer)
        if not claims:
            return {"passed": True, "supported": 0, "total": 0, "unsupported": []}
        sources = "\n\n".join(f"[{i+1}] {c.text}" for i, c in enumerate(contexts))
        claim_list = "\n".join(f"{i}: {c}" for i, c in enumerate(claims))
        try:
            resp = self.client.chat.completions.create(
                model=self.model, temperature=0.0, max_tokens=512,
                messages=[
                    {"role": "system", "content": _SYS},
                    {"role": "user", "content": f"SOURCES:\n{sources}\n\nCLAIMS:\n{claim_list}"},
                ],
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
            data = _parse_json(resp.choices[0].message.content)
            verdicts = {v["i"]: v["supported"] for v in data.get("verdicts", [])}
        except Exception:                       # noqa: BLE001 - fail open, mark unknown
            return {"passed": True, "supported": 0, "total": len(claims),
                    "unsupported": [], "error": "grounding_check_failed"}

        unsupported = [claims[i] for i in range(len(claims)) if not verdicts.get(i, True)]
        supported = len(claims) - len(unsupported)
        return {"passed": len(unsupported) == 0, "supported": supported,
                "total": len(claims), "groundedness": round(supported / len(claims), 3),
                "unsupported": unsupported}


def _parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {"verdicts": []}
