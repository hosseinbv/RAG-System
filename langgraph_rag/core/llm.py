"""Shared LLM helpers. The judge (Qwen3-8B) is a hybrid reasoning model; we disable
its thinking for structured/JSON calls so output is clean and fast."""
from __future__ import annotations

import json
import re

# turn off Qwen3 thinking for deterministic JSON-style calls
NO_THINK = {"chat_template_kwargs": {"enable_thinking": False}}


def chat(client, model, system, user, max_tokens=512, temperature=0.0, no_think=True) -> str:
    resp = client.chat.completions.create(
        model=model, temperature=temperature, max_tokens=max_tokens,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        extra_body=NO_THINK if no_think else None,
    )
    return resp.choices[0].message.content or ""


def parse_json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
