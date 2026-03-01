"""Optional LLM enhancement for Layer 3 (deep semantic, subtle irony).

Only invoked when llm_enhance=True and structural layers yield low confidence
or ambiguous results. Uses OpenAI or Ollama (localhost:11434).
"""

from __future__ import annotations

import json
import re

from discourse_engine.models.report import AssumptionFlag


def _call_ollama(prompt: str, model: str = "llama3.2:3b", base_url: str = "http://localhost:11434") -> str | None:
    """Call Ollama API. Returns response text or None on failure."""
    try:
        import urllib.request
        import urllib.error

        url = f"{base_url.rstrip('/')}/api/generate"
        body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return data.get("response", "").strip() or None
    except Exception:
        return None


def _call_openai(prompt: str, model: str, api_key: str) -> str | None:
    """Call OpenAI-compatible API. Returns response text or None on failure."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )
        if resp.choices:
            return (resp.choices[0].message.content or "").strip() or None
        return None
    except Exception:
        return None


def _call_llm(
    prompt: str,
    *,
    api_key: str | None = None,
    model: str = "gpt-4",
    ollama_model: str | None = None,
    ollama_base: str = "http://localhost:11434",
) -> str | None:
    """Call LLM via OpenAI or Ollama. Returns response text or None."""
    if ollama_model:
        return _call_ollama(prompt, model=ollama_model, base_url=ollama_base)
    if api_key:
        return _call_openai(prompt, model=model, api_key=api_key)
    return None


def enhance_assumptions(
    text: str,
    candidates: list[AssumptionFlag],
    *,
    api_key: str | None = None,
    model: str = "gpt-4",
    ollama_model: str | None = None,
    ollama_base: str = "http://localhost:11434",
) -> list[AssumptionFlag]:
    """
    Optional LLM enhancement for hidden assumptions.
    Only adds new assumptions when structural layer found few/none and text is argumentative.
    """
    if len(candidates) >= 3:
        return candidates

    # Heuristic: argumentative if modal verbs, conditionals, or value terms
    lower = text.lower()
    arg_signals = (
        "must" in lower or "should" in lower or "require" in lower
        or "if " in lower or "therefore" in lower or "because" in lower
    )
    if not arg_signals:
        return candidates

    prompt = f"""Analyze this text and extract any UNSTATED premises (hidden assumptions) that the argument relies on.
Return ONLY a numbered list of assumptions, one per line. If there are none, reply with "None".

Text:
{text[:1500]}

Assumptions (numbered list or "None"):"""

    response = _call_llm(
        prompt,
        api_key=api_key,
        model=model,
        ollama_model=ollama_model,
        ollama_base=ollama_base,
    )
    if not response:
        return candidates

    new_flags: list[AssumptionFlag] = list(candidates)
    seen = {a.description for a in candidates}

    # Parse numbered list
    for line in response.split("\n"):
        line = line.strip()
        m = re.match(r"^\d+[\.\)]\s*(.+)", line)
        if m:
            desc = m.group(1).strip().rstrip(".")
            if desc.lower() not in ("none", "n/a", "") and desc not in seen:
                seen.add(desc)
                new_flags.append(
                    AssumptionFlag(description=f"LLM: {desc}", sentence="", confidence=0.6)
                )
        elif line and not line.lower().startswith("none"):
            # Unnumbered line that looks like an assumption
            if len(line) > 20 and line not in seen:
                seen.add(line)
                new_flags.append(
                    AssumptionFlag(description=f"LLM: {line}", sentence="", confidence=0.55)
                )

    return new_flags


def enhance_satire_irony(
    text: str,
    base_probability: float,
    signals: list,
    *,
    api_key: str | None = None,
    model: str = "gpt-4",
    ollama_model: str | None = None,
    ollama_base: str = "http://localhost:11434",
) -> tuple[float, list]:
    """
    Optional LLM check for subtle irony when structural signals are inconclusive.
    Called when satire is 0.2-0.5 and value clash detected.
    """
    if base_probability < 0.2 or base_probability > 0.5:
        return base_probability, signals

    prompt = f"""Does this text contain subtle irony or mockery (saying one thing while implying the opposite)?
Reply with ONLY a number 0-100 (probability of irony/satire), then a brief reason on the next line.

Text:
{text[:1000]}

Probability (0-100):"""

    response = _call_llm(
        prompt,
        api_key=api_key,
        model=model,
        ollama_model=ollama_model,
        ollama_base=ollama_base,
    )
    if not response:
        return base_probability, signals

    lines = response.strip().split("\n")
    if lines:
        first = lines[0].strip()
        m = re.search(r"(\d{1,3})", first)
        if m:
            llm_prob = int(m.group(1)) / 100.0
            llm_prob = max(0, min(1, llm_prob))
            # Blend with base
            blended = 0.4 * base_probability + 0.6 * llm_prob
            return min(blended, 0.95), signals

    return base_probability, signals
