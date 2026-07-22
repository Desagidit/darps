"""Provider calls + full call logging, with NO required third-party deps.

Almost every LLM provider exposes an OpenAI-compatible /chat/completions
endpoint, so a small stdlib HTTP client covers Anthropic, OpenAI, Ollama,
LM Studio, vLLM, and most others. LiteLLM is used ONLY if you opt into it
(provider: litellm), so a plain `pip install pyyaml` is enough to play.

Every call is appended to logs/calls.jsonl (prompt in, response out, latency,
pipeline tag). When a character misbehaves, read the log — don't guess.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "calls.jsonl"

# Named presets so config.yaml stays short. base_url may be overridden per-config.
PROVIDERS = {
    "openai":    {"base_url": "https://api.openai.com/v1", "key_env": "OPENAI_API_KEY",    "style": "openai"},
    "anthropic": {"base_url": "https://api.anthropic.com/v1", "key_env": "ANTHROPIC_API_KEY", "style": "anthropic"},
    "ollama":    {"base_url": "http://localhost:11434/v1", "key_env": None,                "style": "openai"},
    "lmstudio":  {"base_url": "http://localhost:1234/v1",  "key_env": None,                "style": "openai"},
    "openai_compatible": {"base_url": None, "key_env": "LLM_API_KEY", "style": "openai"},
}


class ProviderError(RuntimeError):
    """A configured model provider could not complete a DARPS call."""


def _resolve(cfg: dict, classifier: bool) -> dict:
    classifier_provider = cfg.get("classifier_provider") if classifier else None
    provider = classifier_provider or cfg.get("provider", "openai")
    model_key = "classifier_model" if classifier else "model"
    model = cfg.get(model_key)
    if not isinstance(model, str) or not model.strip():
        raise ProviderError(f"config needs a non-empty '{model_key}'")

    # A classifier inherits the response provider's endpoint only when it also
    # inherits that provider. Once classifier_provider is explicit, its own
    # preset (or classifier_base_url) must win over an unrelated base_url.
    if classifier and cfg.get("classifier_base_url"):
        configured_base_url = cfg["classifier_base_url"]
    elif not classifier_provider:
        configured_base_url = cfg.get("base_url")
    else:
        configured_base_url = None

    if provider == "litellm":
        return {"provider": "litellm", "model": model,
                "base_url": configured_base_url}
    preset = PROVIDERS.get(provider)
    if preset is None:
        raise ProviderError(f"Unknown provider '{provider}'. Known: "
                            f"{', '.join(PROVIDERS)}, litellm.")
    base_url = configured_base_url or preset["base_url"]
    if not base_url:
        field = "classifier_base_url" if classifier_provider else "base_url"
        raise ProviderError(f"provider '{provider}' needs {field} set in config.yaml.")
    api_key = ""
    if preset["key_env"]:
        api_key = os.environ.get(preset["key_env"], "")
        if not api_key:
            raise ProviderError(
                f"Missing {preset['key_env']}. Put it in a .env file (see .env.example) "
                f"or export it in your shell."
            )
    return {"provider": provider, "style": preset["style"], "base_url": base_url.rstrip("/"),
            "api_key": api_key, "model": model}


def _http_json(url: str, payload: dict, headers: dict, timeout: int = 120) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:500]
        raise ProviderError(f"HTTP {e.code} from {url}: {body}") from None
    except urllib.error.URLError as e:
        raise ProviderError(f"Could not reach {url}: {e.reason}. "
                            f"If this is a local model, is the server running?") from None


def _call_openai_style(rc, messages, temperature, max_tokens) -> str:
    headers = {}
    if rc["api_key"]:
        headers["Authorization"] = f"Bearer {rc['api_key']}"
    data = _http_json(f"{rc['base_url']}/chat/completions", {
        "model": rc["model"], "messages": messages,
        "temperature": temperature, "max_tokens": max_tokens,
    }, headers)
    return data["choices"][0]["message"]["content"] or ""


def _call_anthropic(rc, messages, temperature, max_tokens) -> str:
    headers = {"x-api-key": rc["api_key"], "anthropic-version": "2023-06-01"}
    data = _http_json(f"{rc['base_url']}/messages", {
        "model": rc["model"], "messages": messages,
        "temperature": temperature, "max_tokens": max_tokens,
    }, headers)
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def _call_litellm(rc, messages, temperature, max_tokens, base_url) -> str:
    import litellm  # optional; only imported if provider == litellm
    litellm.suppress_debug_info = True
    kwargs = dict(model=rc["model"], messages=messages,
                  temperature=temperature, max_tokens=max_tokens)
    if base_url:
        kwargs["api_base"] = base_url
    return litellm.completion(**kwargs).choices[0].message.content or ""


# ------------------------------------------------------------------ streaming
def _sse_data_lines(url: str, payload: dict, headers: dict, timeout: int = 120):
    """POST and yield decoded `data:` payload strings from an SSE response."""
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if line.startswith("data:"):
                    yield line[len("data:"):].strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:500]
        raise ProviderError(f"HTTP {e.code} from {url}: {body}") from None
    except urllib.error.URLError as e:
        raise ProviderError(f"Could not reach {url}: {e.reason}. "
                            f"If this is a local model, is the server running?") from None


def _stream_openai_style(rc, messages, temperature, max_tokens):
    headers = {}
    if rc["api_key"]:
        headers["Authorization"] = f"Bearer {rc['api_key']}"
    for data in _sse_data_lines(f"{rc['base_url']}/chat/completions", {
            "model": rc["model"], "messages": messages,
            "temperature": temperature, "max_tokens": max_tokens,
            "stream": True}, headers):
        if data == "[DONE]":
            return
        try:
            obj = json.loads(data)
        except json.JSONDecodeError:
            continue
        piece = (obj.get("choices") or [{}])[0].get("delta", {}).get("content")
        if piece:
            yield piece


def _stream_anthropic(rc, messages, temperature, max_tokens):
    headers = {"x-api-key": rc["api_key"], "anthropic-version": "2023-06-01"}
    for data in _sse_data_lines(f"{rc['base_url']}/messages", {
            "model": rc["model"], "messages": messages,
            "temperature": temperature, "max_tokens": max_tokens,
            "stream": True}, headers):
        try:
            obj = json.loads(data)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "content_block_delta":
            piece = obj.get("delta", {}).get("text")
            if piece:
                yield piece


def _stream_litellm(rc, messages, temperature, max_tokens, base_url):
    import litellm
    litellm.suppress_debug_info = True
    kwargs = dict(model=rc["model"], messages=messages, temperature=temperature,
                  max_tokens=max_tokens, stream=True)
    if base_url:
        kwargs["api_base"] = base_url
    for chunk in litellm.completion(**kwargs):
        piece = chunk.choices[0].delta.content
        if piece:
            yield piece


def call_stream(cfg: dict, prompt: str, tag: str, *, classifier: bool = False):
    """Streaming twin of call(): yields text deltas as the model produces
    them, and logs the FULL prompt/response to calls.jsonl once the stream
    ends (the log is the debugging artifact; it must not see fragments)."""
    rc = _resolve(cfg, classifier)
    temperature = cfg["classifier_temperature" if classifier else "temperature"]
    max_tokens = cfg.get("max_tokens", 700)
    messages = [{"role": "user", "content": prompt}]

    if rc["provider"] == "litellm":
        gen = _stream_litellm(rc, messages, temperature, max_tokens, rc.get("base_url"))
    elif rc["style"] == "anthropic":
        gen = _stream_anthropic(rc, messages, temperature, max_tokens)
    else:
        gen = _stream_openai_style(rc, messages, temperature, max_tokens)

    t0 = time.time()
    pieces = []
    try:
        for piece in gen:
            pieces.append(piece)
            yield piece
    except ProviderError:
        raise
    except Exception as e:
        raise ProviderError(f"invalid streaming response from provider: {e}") from None
    finally:
        LOG_PATH.parent.mkdir(exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": time.time(), "tag": tag, "model": rc["model"],
                "latency_s": round(time.time() - t0, 2), "streamed": True,
                "prompt": prompt, "response": "".join(pieces),
            }, ensure_ascii=False) + "\n")


def call(cfg: dict, prompt: str, tag: str, *, classifier: bool = False) -> str:
    rc = _resolve(cfg, classifier)
    temperature = cfg["classifier_temperature" if classifier else "temperature"]
    max_tokens = cfg.get("max_tokens", 700)
    messages = [{"role": "user", "content": prompt}]

    t0 = time.time()
    try:
        if rc["provider"] == "litellm":
            text = _call_litellm(rc, messages, temperature, max_tokens, rc.get("base_url"))
        elif rc["style"] == "anthropic":
            text = _call_anthropic(rc, messages, temperature, max_tokens)
        else:
            text = _call_openai_style(rc, messages, temperature, max_tokens)
    except ProviderError:
        raise
    except Exception as e:
        raise ProviderError(f"invalid response from provider: {e}") from None

    LOG_PATH.parent.mkdir(exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": time.time(), "tag": tag, "model": rc["model"],
            "latency_s": round(time.time() - t0, 2),
            "prompt": prompt, "response": text,
        }, ensure_ascii=False) + "\n")
    return text


def extract_json(text: str) -> dict:
    """Pull the first JSON object out of a response, fenced or bare."""
    fence = re.search(r"```(?:events|json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fence.group(1) if fence else None
    if candidate is None:
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        candidate = brace.group(0) if brace else None
    if candidate is None:
        return {}
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return {}


def strip_events_block(text: str) -> str:
    """Remove the fenced events block so only prose reaches the player."""
    return re.sub(r"```(?:events|json)?\s*\{.*?\}\s*```", "", text, flags=re.DOTALL).strip()
