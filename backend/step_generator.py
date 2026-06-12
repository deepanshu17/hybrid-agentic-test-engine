"""Claude-powered step generation.

Read this after `main.py` when studying Phase 2.

This module owns one job: convert a plain-English intent into `TestStep` objects.
It does not know anything about Playwright execution or AI recovery. Keeping it
small makes it easy to test and replace independently.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from typing import Any

from anthropic import AsyncAnthropic

from backend.models import TestStep


DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")


class StepGenerationError(RuntimeError):
    """Raised when Claude cannot produce valid `TestStep` JSON."""


def _require_api_key() -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise StepGenerationError(
            "ANTHROPIC_API_KEY is required for Phase 2 step generation."
        )
    return api_key


def _extract_json_array(text: str) -> str:
    """Pull the first JSON array out of a model response.

    The prompt asks for JSON only, but this guard makes local debugging less
    fragile if the model adds a short preface.
    """

    stripped = text.strip()
    if stripped.startswith("["):
        return stripped

    match = re.search(r"\[[\s\S]*\]", stripped)
    if not match:
        raise StepGenerationError("Claude did not return a JSON array of steps.")
    return match.group(0)


def _parse_steps(raw_text: str) -> list[TestStep]:
    try:
        payload: Any = json.loads(_extract_json_array(raw_text))
    except json.JSONDecodeError as exc:
        raise StepGenerationError(f"Invalid JSON from Claude: {exc}") from exc

    if not isinstance(payload, list):
        raise StepGenerationError("Claude response must be a JSON array.")

    try:
        steps = [TestStep.model_validate(item) for item in payload]
    except Exception as exc:
        raise StepGenerationError(f"Claude returned invalid step objects: {exc}") from exc

    if not steps:
        raise StepGenerationError("Claude returned no executable steps.")

    return steps


async def generate_steps(intent: str) -> list[TestStep]:
    """Generate executable Playwright steps from a user intent.

    For the take-home prototype we constrain the target site to
    `automationexercise.com` so the live demo is repeatable. The model still
    performs the intent-to-steps translation, but it does so inside a known app.
    """

    client = AsyncAnthropic(api_key=_require_api_key())

    prompt = f"""
You convert plain-English test intents into structured browser automation steps.

TARGET SITE:
- Use https://automationexercise.com/products unless the user explicitly gives another URL.
- Prefer stable CSS selectors.
- For product search on automationexercise.com:
  - search input selector: #search_product
  - search submit button selector: #submit_search
  - first product add-to-cart selector: .features_items .product-image-wrapper:first-child a.add-to-cart

SUPPORTED ACTIONS:
- navigate: requires url
- fill: requires selector and value
- click: requires selector
- assert_text: requires selector and expected_outcome

IMPORTANT:
- Return JSON only.
- Return an array of 3 to 6 step objects.
- Every step_id must be sequential: step_1, step_2, step_3, ...
- For a search-and-add-to-cart intent, make step_3 the click on #submit_search.

USER INTENT:
{intent}

JSON SHAPE:
[
  {{
    "step_id": "step_1",
    "description": "Navigate to products page",
    "action": "navigate",
    "selector": null,
    "value": null,
    "url": "https://automationexercise.com/products",
    "expected_outcome": "Products page loads"
  }}
]
""".strip()

    response = await client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=1200,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    )
    return _parse_steps(raw_text)


async def _cli() -> None:
    parser = argparse.ArgumentParser(description="Generate TestStep JSON from intent.")
    parser.add_argument("intent")
    args = parser.parse_args()
    steps = await generate_steps(args.intent)
    print(json.dumps([step.model_dump() for step in steps], indent=2))


if __name__ == "__main__":
    asyncio.run(_cli())
