"""The Claude call: system prompt + document -> validated ContractReview."""

import logging
import os
from pathlib import Path

import anthropic

from .extract import PreparedInput
from .schema import ContractReview

log = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-5-5"
DEFAULT_EFFORT = "high"

# Choices offered in the web UI (cheapest first). Only these are accepted from the form.
MODEL_OPTIONS = {
    "claude-haiku-5-5": "Haiku 5.5 — cheapest (~$0.003–0.02 / review)",
    "claude-sonnet-5-5": "Sonnet 5.5 — balanced (~$0.05–0.30 / review)",
    "claude-opus-5-5": "Opus 5.5 — strongest (~$0.10–0.60 / review)",
}
EFFORT_OPTIONS = ["low", "medium", "high", "xhigh", "max"]
# Models that support the server-side refusal fallback (Haiku does not).
FALLBACK_MODELS = {"claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5", "claude-fable-5-2", "claude-fable-5-1"}
SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "system.md"

_client: anthropic.Anthropic | None = None


class ReviewError(RuntimeError):
    """The review couldn't be produced; message is shown to the user."""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def default_settings() -> tuple[str, str]:
    """Model and effort from .env, falling back to the built-in defaults."""
    model = os.environ.get("CLAUDE_MODEL", "").strip() or DEFAULT_MODEL
    effort = os.environ.get("CLAUDE_EFFORT", "").strip() or DEFAULT_EFFORT
    return model, effort


def review_contract(doc: PreparedInput, model: str | None = None, effort: str | None = None) -> ContractReview:
    # Read on each call so prompt edits apply without restarting the server.
    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    default_model, default_effort = default_settings()
    model = model or default_model
    effort = effort or default_effort

    extra = {}
    if model in FALLBACK_MODELS:
        # If a safety classifier declines, the API retries on a suitable fallback model.
        extra = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}

    try:
        response = _get_client().beta.messages.parse(
            model=model,
            max_tokens=16000,  # higher values need streaming to avoid SDK HTTP timeouts
            system=system_prompt,
            output_config={"effort": effort},
            **extra,
            messages=[
                {
                    "role": "user",
                    "content": [
                        doc.content_block,
                        {"type": "text", "text": "Review this contract."},
                    ],
                }
            ],
            output_format=ContractReview,
        )
    except anthropic.AuthenticationError as e:
        raise ReviewError("Anthropic API key is missing or invalid. Set ANTHROPIC_API_KEY in .env.") from e
    except anthropic.RateLimitError as e:
        raise ReviewError("Rate limited by the Anthropic API. Try again in a minute.") from e
    except anthropic.BadRequestError as e:
        raise ReviewError(f"The API rejected the request: {e.message}") from e
    except anthropic.APIStatusError as e:
        raise ReviewError(f"Anthropic API error ({e.status_code}). Try again shortly.") from e
    except anthropic.APIConnectionError as e:
        raise ReviewError("Could not reach the Anthropic API. Check your network connection.") from e

    log.info(
        "review done request_id=%s model=%s stop=%s in=%s out=%s",
        response._request_id, response.model, response.stop_reason,
        response.usage.input_tokens, response.usage.output_tokens,
    )

    if response.stop_reason == "refusal":
        raise ReviewError("The model declined to review this document.")
    if response.stop_reason == "max_tokens":
        raise ReviewError("The review was cut off because it was too long. Try a shorter document.")
    if response.parsed_output is None:
        raise ReviewError("The model did not return a structured review.")
    return response.parsed_output
