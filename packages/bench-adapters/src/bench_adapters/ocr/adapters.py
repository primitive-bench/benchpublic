"""Concrete OCR vendor adapters (page image -> transcription text).

`invoke(item)` reads `item['image']` (an absolute path to a page image) and
returns the bench-adapters result dict: at least `raw_output`/`text`,
`latency_ms`, `cost_usd`, and `mode` (prompted_vlm | native_ocr).

Keys are read straight from the environment (never hardcoded) via `_env`, with
the repo's `WRODIUM_<VENDOR>_API_KEY` primary name and the bare name as a
fallback. A vendor whose key/binary is unset raises `VendorUnavailable`.

Heavy SDKs (pytesseract, anthropic, …) are imported lazily inside `invoke` so
importing this module never hard-fails when an optional engine is absent — the
keyless `tesseract` lane and the test suite import cleanly regardless.
"""
from __future__ import annotations

import base64
import io
import os
import time
from typing import Any

import httpx

from bench_adapters.ocr import pricing
from bench_adapters.registry import Adapter, register

# The single, version-pinned transcription instruction shared by every PROMPTED
# vision-LLM adapter. Pinning one prompt across vendors removes prompt phrasing
# as a confound; it is recorded in the run manifest. Native-OCR engines ignore it.
OCR_PROMPT = (
    "Transcribe all text in this image exactly as it appears, preserving reading "
    "order and line breaks. Output only the transcription — no commentary, no "
    "preamble, and no markdown code fences."
)

# Downscale long edge before sending to a hosted model (Sonnet 4.6 caps ~1568px).
DEFAULT_MAX_EDGE = 1568


class VendorUnavailable(Exception):
    """Raised when a vendor cannot be queried (missing key, missing binary, ...)."""


def _env(*names: str) -> str:
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return ""


def _need(value: str, vendor: str) -> str:
    if not value:
        raise VendorUnavailable(f"{vendor} key unset")
    return value


def _load_image(path: str, *, max_edge: int | None = None):
    """Open an image as RGB, optionally downscaling the long edge. Lazy PIL import."""
    try:
        from PIL import Image
    except Exception as exc:  # pragma: no cover
        raise VendorUnavailable(f"Pillow unavailable: {exc}") from exc
    if not path or not os.path.exists(path):
        raise VendorUnavailable(f"image not found: {path!r}")
    img = Image.open(path).convert("RGB")
    if max_edge:
        w, h = img.size
        scale = max_edge / max(w, h)
        if scale < 1.0:
            img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))))
    return img


def _tesseract_version() -> str:
    try:
        import pytesseract
        return f"tesseract-{pytesseract.get_tesseract_version()}"
    except Exception:
        return "tesseract"


@register("tesseract")
class TesseractAdapter(Adapter):
    """Local Tesseract — the deterministic, free regression sentinel (no API key).

    Expected to be stable and to LOSE most slices; a drift in its anchor-set
    pass-rate (CUSUM) flags harness drift vs vendor drift. Requires the system
    `tesseract` binary (`brew install tesseract`) + `pytesseract`.
    """

    vendor = "tesseract"
    model_version = _tesseract_version()
    is_sentinel = True
    mode = "native_ocr"

    def invoke(self, item: dict[str, Any]) -> dict[str, Any]:
        try:
            import pytesseract
        except Exception as exc:
            raise VendorUnavailable(f"pytesseract unavailable: {exc}") from exc
        img = _load_image(str(item.get("image", "")))  # full res for tesseract
        t0 = time.monotonic()
        try:
            text = pytesseract.image_to_string(img)
        except pytesseract.TesseractNotFoundError as exc:
            raise VendorUnavailable(f"tesseract binary not found: {exc}") from exc
        latency_ms = (time.monotonic() - t0) * 1000.0
        return {
            "raw_output": text,
            "text": text,
            "latency_ms": latency_ms,
            "cost_usd": 0.0,
            "mode": self.mode,
        }


# --- hosted vision / OCR adapters ----------------------------------------
# Model ids are env-overridable so model drift never needs a code change; the
# resolved id is recorded in the run manifest (AdapterSpec.version).
_MAX_TOKEN_TRIES = (8192, 16384)  # truncation guard: retry larger once, then non_attempt


def _image_b64(path: str, *, max_edge: int = DEFAULT_MAX_EDGE) -> tuple[str, str]:
    """Return (base64 PNG, mime) for a downscaled page image."""
    img = _load_image(path, max_edge=max_edge)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii"), "image/png"


def _post(url: str, body: dict[str, Any], headers: dict[str, str], timeout: float = 120.0) -> dict:
    r = httpx.post(url, json=body, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _ok(text: str, latency_ms: float, cost: float, mode: str) -> dict[str, Any]:
    return {"raw_output": text, "text": text, "latency_ms": latency_ms,
            "cost_usd": cost, "mode": mode}


@register("claude-sonnet-ocr")
class ClaudeOCR(Adapter):
    """Anthropic Claude (vision) via the official `anthropic` SDK — prompted VLM."""

    vendor = "anthropic"
    model_version = os.environ.get("CLAUDE_OCR_MODEL", "claude-sonnet-4-6")
    is_sentinel = False
    mode = "prompted_vlm"

    def invoke(self, item: dict[str, Any]) -> dict[str, Any]:
        try:
            import anthropic
        except Exception as exc:
            raise VendorUnavailable(f"anthropic SDK unavailable: {exc}") from exc
        key = _need(_env("WRODIUM_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"), "claude-sonnet-ocr")
        b64, mime = _image_b64(str(item.get("image", "")))
        client = anthropic.Anthropic(api_key=key)
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
            {"type": "text", "text": OCR_PROMPT},
        ]
        for max_tok in _MAX_TOKEN_TRIES:
            t0 = time.monotonic()
            resp = client.messages.create(
                model=self.model_version, max_tokens=max_tok,
                thinking={"type": "disabled"},
                messages=[{"role": "user", "content": content}],
            )
            latency = (time.monotonic() - t0) * 1000.0
            if resp.stop_reason == "refusal":
                return {"non_attempt": "refused", "latency_ms": latency}
            text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
            cost = pricing.token_cost(self.model_version, resp.usage.input_tokens,
                                      resp.usage.output_tokens)
            if resp.stop_reason == "max_tokens":
                continue
            return _ok(text, latency, cost, self.mode)
        return {"non_attempt": "truncated"}


@register("gpt-ocr")
class GptOCR(Adapter):
    """OpenAI GPT-4o vision via the chat-completions REST API — prompted VLM."""

    vendor = "openai"
    model_version = os.environ.get("GPT_OCR_MODEL", "gpt-4o")
    is_sentinel = False
    mode = "prompted_vlm"

    def invoke(self, item: dict[str, Any]) -> dict[str, Any]:
        key = _need(_env("WRODIUM_OPENAI_API_KEY", "OPENAI_API_KEY"), "gpt-ocr")
        b64, mime = _image_b64(str(item.get("image", "")))
        url = "https://api.openai.com/v1/chat/completions"
        content = [
            {"type": "text", "text": OCR_PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]
        for max_tok in _MAX_TOKEN_TRIES:
            body = {"model": self.model_version, "max_tokens": max_tok, "temperature": 0,
                    "messages": [{"role": "user", "content": content}]}
            t0 = time.monotonic()
            d = _post(url, body, {"Authorization": f"Bearer {key}"})
            latency = (time.monotonic() - t0) * 1000.0
            ch = d["choices"][0]
            text = ch["message"].get("content") or ""
            u = d.get("usage", {})
            cost = pricing.token_cost(self.model_version, u.get("prompt_tokens", 0),
                                      u.get("completion_tokens", 0))
            if ch.get("finish_reason") == "length":
                continue
            return _ok(text, latency, cost, self.mode)
        return {"non_attempt": "truncated"}


@register("gemini-ocr")
class GeminiOCR(Adapter):
    """Google Gemini vision via the generateContent REST API — prompted VLM."""

    vendor = "google"
    model_version = os.environ.get("GEMINI_OCR_MODEL", "gemini-2.5-pro")
    is_sentinel = False
    mode = "prompted_vlm"

    def invoke(self, item: dict[str, Any]) -> dict[str, Any]:
        key = _need(_env("WRODIUM_GEMINI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"), "gemini-ocr")
        b64, mime = _image_b64(str(item.get("image", "")))
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{self.model_version}:generateContent")
        parts = [{"text": OCR_PROMPT}, {"inline_data": {"mime_type": mime, "data": b64}}]
        for max_tok in _MAX_TOKEN_TRIES:
            body = {"contents": [{"parts": parts}],
                    "generationConfig": {"maxOutputTokens": max_tok, "temperature": 0}}
            t0 = time.monotonic()
            d = _post(url, body, {"x-goog-api-key": key})
            latency = (time.monotonic() - t0) * 1000.0
            cand = (d.get("candidates") or [{}])[0]
            text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
            um = d.get("usageMetadata", {})
            cost = pricing.token_cost(self.model_version, um.get("promptTokenCount", 0),
                                      um.get("candidatesTokenCount", 0))
            if cand.get("finishReason") == "MAX_TOKENS":
                continue
            return _ok(text, latency, cost, self.mode)
        return {"non_attempt": "truncated"}


@register("mistral-ocr")
class MistralOCR(Adapter):
    """Mistral dedicated OCR API (document -> markdown) — native OCR, no prompt."""

    vendor = "mistral"
    model_version = os.environ.get("MISTRAL_OCR_MODEL", "mistral-ocr-latest")
    is_sentinel = False
    mode = "native_ocr"

    def invoke(self, item: dict[str, Any]) -> dict[str, Any]:
        key = _need(_env("WRODIUM_MISTRAL_API_KEY", "MISTRAL_API_KEY"), "mistral-ocr")
        b64, mime = _image_b64(str(item.get("image", "")))
        body = {"model": self.model_version,
                "document": {"type": "image_url", "image_url": f"data:{mime};base64,{b64}"}}
        t0 = time.monotonic()
        d = _post("https://api.mistral.ai/v1/ocr", body, {"Authorization": f"Bearer {key}"})
        latency = (time.monotonic() - t0) * 1000.0
        pages = d.get("pages", [])
        text = "\n\n".join(p.get("markdown", "") for p in pages)
        cost = pricing.page_cost(self.model_version, max(1, len(pages)))
        return _ok(text, latency, cost, self.mode)


@register("deepseek-ocr")
class DeepSeekOCR(Adapter):
    """DeepSeek-OCR — self-host only (no hosted vision API as of 2026-06).

    Set `DEEPSEEK_OCR_BASE_URL` to a vLLM/Ollama OpenAI-compatible endpoint to
    enable it; otherwise it is skipped (`VendorUnavailable`), uncharged.
    """

    vendor = "deepseek"
    model_version = os.environ.get("DEEPSEEK_OCR_MODEL", "deepseek-ocr")
    is_sentinel = False
    mode = "native_ocr"

    def invoke(self, item: dict[str, Any]) -> dict[str, Any]:
        base = _env("DEEPSEEK_OCR_BASE_URL")
        if not base:
            raise VendorUnavailable(
                "deepseek-ocr is self-host only; set DEEPSEEK_OCR_BASE_URL to a vLLM/Ollama "
                "OpenAI-compatible endpoint"
            )
        key = _env("WRODIUM_DEEPSEEK_API_KEY", "DEEPSEEK_API_KEY") or "EMPTY"
        b64, mime = _image_b64(str(item.get("image", "")))
        url = base.rstrip("/") + "/chat/completions"
        content = [
            {"type": "text", "text": OCR_PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]
        body = {"model": self.model_version, "temperature": 0,
                "messages": [{"role": "user", "content": content}]}
        t0 = time.monotonic()
        d = _post(url, body, {"Authorization": f"Bearer {key}"}, timeout=180.0)
        latency = (time.monotonic() - t0) * 1000.0
        text = d["choices"][0]["message"].get("content") or ""
        return _ok(text, latency, 0.0, self.mode)
