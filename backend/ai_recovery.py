"""Claude-powered recovery for failed Playwright steps.

This is the most important Phase 2 module. A deterministic selector fails, so
we show Claude the user's intended action plus a compact snapshot of interactive
DOM elements and ask for a replacement selector.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from typing import Any

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from backend.models import TestStep


DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")


class AIRecoveryError(RuntimeError):
    """Raised when the recovery agent cannot return a usable step."""


class RecoverySuggestion(BaseModel):
    recovered_selector: str
    recovered_action: str
    technical_reasoning: str
    customer_explanation: str


def _require_api_key() -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise AIRecoveryError("ANTHROPIC_API_KEY is required for Phase 2 recovery.")
    return api_key


async def extract_interactive_dom(page: Any) -> list[dict[str, Any]]:
    """Return a token-efficient snapshot of elements an agent can act on.

    Full HTML is usually too noisy. This keeps buttons, links, inputs, and
    elements with click handlers, which is enough context for selector recovery.
    """

    return await page.evaluate(
        """
        () => Array.from(document.querySelectorAll(
          'a, button, input, select, textarea, [role="button"], [onclick]'
        )).slice(0, 120).map((el, index) => ({
          index,
          tag: el.tagName.toLowerCase(),
          text: (el.innerText || el.value || el.getAttribute('aria-label') || '')
            .trim()
            .slice(0, 120),
          id: el.id || null,
          classes: typeof el.className === 'string' ? el.className : null,
          name: el.getAttribute('name'),
          type: el.getAttribute('type'),
          href: el.getAttribute('href'),
          role: el.getAttribute('role'),
          placeholder: el.getAttribute('placeholder')
        }))
        """
    )


def _extract_json_object(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("{"):
        return stripped

    match = re.search(r"\{[\s\S]*\}", stripped)
    if not match:
        raise AIRecoveryError("Claude did not return a JSON recovery object.")
    return match.group(0)


def _parse_suggestion(raw_text: str) -> RecoverySuggestion:
    try:
        payload = json.loads(_extract_json_object(raw_text))
    except json.JSONDecodeError as exc:
        raise AIRecoveryError(f"Invalid JSON from Claude recovery: {exc}") from exc

    try:
        return RecoverySuggestion.model_validate(payload)
    except Exception as exc:
        raise AIRecoveryError(f"Invalid recovery suggestion from Claude: {exc}") from exc


async def recover_step(
    *,
    original_step: TestStep,
    failed_step: TestStep,
    error: str,
    dom_snapshot: list[dict[str, Any]],
) -> tuple[TestStep, RecoverySuggestion]:
    """Ask Claude to recover the selector/action for a failed step."""

    client = AsyncAnthropic(api_key=_require_api_key())
    prompt = f"""
You are a test recovery agent. A deterministic Playwright step failed because
the target element was not found or could not be acted on.

ORIGINAL STEP INTENT:
{original_step.model_dump_json(indent=2)}

FAILED RUNTIME STEP:
{failed_step.model_dump_json(indent=2)}

PLAYWRIGHT ERROR:
{error}

CURRENT INTERACTIVE DOM SNAPSHOT:
{json.dumps(dom_snapshot, indent=2)}

Your job:
1. Find the element that best matches the original step intent.
2. Return a CSS selector that Playwright can use now.
3. Keep the recovered action the same unless the DOM clearly requires a safer action.
4. Explain the recovery technically and in customer-readable language.

Return JSON only:
{{
  "recovered_selector": "...",
  "recovered_action": "click",
  "technical_reasoning": "...",
  "customer_explanation": "..."
}}
""".strip()

    response = await client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=900,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    raw_text = "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    )
    suggestion = _parse_suggestion(raw_text)
    recovered_step = original_step.model_copy(
        update={
            "action": suggestion.recovered_action,
            "selector": suggestion.recovered_selector,
        }
    )
    return recovered_step, suggestion


async def _cli() -> None:
    parser = argparse.ArgumentParser(description="Parse a sample recovery suggestion.")
    parser.add_argument("json_text")
    args = parser.parse_args()
    print(_parse_suggestion(args.json_text).model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(_cli())
