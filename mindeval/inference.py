import time

import litellm
import os

# Suppress litellm logging errors
os.environ["LITELLM_LOG"] = "ERROR"
litellm.suppress_debug_info = True
# Drop params not supported by a model (e.g. temperature for gpt-5 family)
litellm.drop_params = True

from mindeval.utils import separate_thinking_from_response

_RETRY_DELAYS = [10, 30, 60, 120]  # seconds between retries for rate-limit fallback

import re as _re

def _parse_reset_seconds(error_msg: str) -> int | None:
    """Extract reset time from rate-limit error message, e.g. 'reset after 1m 10s' → 70."""
    m = _re.search(r"reset after\s+(?:(\d+)m\s*)?(?:(\d+)s)?", str(error_msg))
    if m:
        minutes = int(m.group(1) or 0)
        seconds = int(m.group(2) or 0)
        total = minutes * 60 + seconds
        return total if total > 0 else None
    return None


class InferenceEngine:
    def __init__(self, api_params: dict[str, str]):
        self.api_params = api_params  # model, api_key, api_base

    # Keys consumed internally and must NOT be forwarded to LiteLLM
    _INTERNAL_KEYS = {"use_anthropic_batch", "thinking_budget_tokens"}

    def _api_params_for_call(self) -> tuple[dict, int]:
        """Return (params_without_max_retries, max_retries).
        Also strips keys not understood by LiteLLM.
        """
        api_params_copy = self.api_params.copy()
        max_retries = api_params_copy.pop("max_retries", 10)
        for key in self._INTERNAL_KEYS:
            api_params_copy.pop(key, None)
        return api_params_copy, max_retries

    def generate(self, messages: list[dict[str, str]]) -> str:
        api_params_copy, max_retries = self._api_params_for_call()
        response = litellm.completion(
            messages=messages, max_retries=max_retries, **api_params_copy
        )
        return response.choices[0].message.content

    def _generate_single_with_retry(
        self, messages: list[dict[str, str]], api_params: dict, max_retries: int
    ) -> str:
        """Call completion on a single message list, retrying on rate-limit errors.

        For rate-limit errors, waits for the reset time specified in the error
        message (e.g. 'reset after 1m 10s') before retrying — no attempt limit.
        For other errors, retries with fixed back-off up to len(_RETRY_DELAYS) times.
        """
        other_failures = 0
        attempt = 0
        while True:
            try:
                response = litellm.completion(
                    messages=messages, max_retries=max_retries, **api_params
                )
                return response.choices[0].message.content
            except litellm.RateLimitError as exc:
                reset_s = _parse_reset_seconds(str(exc)) or 90
                wait_s = reset_s + 5  # small buffer
                print(f"    [rate-limit] reset in {reset_s}s — waiting {wait_s}s before retry…")
                time.sleep(wait_s)
                attempt += 1
            except Exception as exc:
                other_failures += 1
                if other_failures > len(_RETRY_DELAYS):
                    raise
                delay = _RETRY_DELAYS[other_failures - 1]
                print(f"    [warn] attempt {attempt + 1} failed: {exc}")
                print(f"    [rate-limit] waiting {delay}s before retry {other_failures}…")
                time.sleep(delay)
                attempt += 1

    def batch_generate(self, list_of_messages: list[list[dict[str, str]]]) -> list[str]:
        api_params_copy, max_retries = self._api_params_for_call()

        responses = litellm.batch_completion(
            messages=list_of_messages, max_retries=max_retries, **api_params_copy
        )

        results: list[str] = []
        for i, response in enumerate(responses):
            # litellm.batch_completion may return Exception objects inline
            if isinstance(response, Exception):
                print(f"    [warn] batch item {i} returned error ({type(response).__name__}), retrying individually…")
                text = self._generate_single_with_retry(
                    list_of_messages[i], api_params_copy, max_retries
                )
                results.append(text)
            else:
                results.append(response.choices[0].message.content)
        return results

    def generate_with_thinking(self, messages: list[dict[str, str]]) -> tuple[str, str]:
        response = None
        while response is None:
            response = self.generate(messages)
            if response is None:
                print("Retrying generation because response is None...")
        parts = separate_thinking_from_response(response)
        return parts["response"], parts["thinking"]

    def batch_generate_with_thinking(
        self, list_of_messages: list[list[dict[str, str]]]
    ) -> tuple[list[str], list[str]]:
        responses = self.batch_generate(list_of_messages)
        texts = []
        thinking_traces = []
        for response in responses:
            parts = separate_thinking_from_response(response)
            texts.append(parts["response"])
            thinking_traces.append(parts["thinking"])
        return texts, thinking_traces

    # ------------------------------------------------------------------ #
    #  Anthropic Message Batches API  (50 % token discount, async)        #
    # ------------------------------------------------------------------ #

    def _anthropic_model_name(self) -> str:
        """Strip 'anthropic/' prefix for the native Anthropic SDK."""
        model = self.api_params.get("model", "")
        return model.split("/", 1)[-1] if "/" in model else model

    def batch_generate_all_anthropic(
        self, list_of_messages: list[list[dict[str, str]]]
    ) -> list[str]:
        """Submit all messages as one Anthropic Message Batch (50% token discount).

        Polls every 30 s until the batch completes, then returns results in
        the same order as the input list.

        NOTE: Only works with the real Anthropic API (no custom api_base).
        If api_base is set to a non-Anthropic endpoint, falls back to
        standard sync batch_generate.
        """
        api_base = self.api_params.get("api_base", None)
        if api_base and "anthropic.com" not in str(api_base):
            print(f"  [anthropic-batch] WARNING: api_base='{api_base}' is not Anthropic's API. "
                  "Falling back to standard sync calls.")
            return self.batch_generate(list_of_messages)

        import anthropic as _anthropic

        model   = self._anthropic_model_name()
        api_key = self.api_params.get("api_key", "")
        max_tokens  = self.api_params.get("max_tokens") or 1024
        temperature = self.api_params.get("temperature", 0.3)

        client = _anthropic.Anthropic(api_key=api_key)

        # Extended thinking: enable when thinking_budget_tokens is configured.
        # Anthropic requirements when thinking is enabled:
        #   - temperature MUST be 1
        #   - max_tokens must be > budget_tokens
        thinking_budget = self.api_params.get("thinking_budget_tokens")
        thinking_param: dict | None = None
        if thinking_budget:
            thinking_param = {"type": "enabled", "budget_tokens": thinking_budget}
            temperature = 1  # Anthropic hard requirement
            if max_tokens <= thinking_budget:
                max_tokens = thinking_budget + 2048

        def _build_params(msgs: list) -> dict:
            p: dict = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": msgs,
            }
            if thinking_param:
                p["thinking"] = thinking_param
            return p

        requests = [
            {"custom_id": f"req-{i}", "params": _build_params(msgs)}
            for i, msgs in enumerate(list_of_messages)
        ]

        batch = client.beta.messages.batches.create(requests=requests)
        print(f"  [anthropic-batch] Submitted batch {batch.id}  "
              f"({len(requests)} requests) — polling every 30 s …")

        while batch.processing_status != "ended":
            time.sleep(30)
            batch = client.beta.messages.batches.retrieve(batch.id)
            c = batch.request_counts
            print(f"  [anthropic-batch] {batch.processing_status}: "
                  f"processing={c.processing}  "
                  f"succeeded={c.succeeded}  errored={c.errored}")

        results_map: dict[str, str] = {}
        for result in client.beta.messages.batches.results(batch.id):
            if result.result.type == "succeeded":
                thinking_parts: list[str] = []
                text_parts: list[str] = []
                for block in result.result.message.content:
                    btype = getattr(block, "type", None)
                    if btype == "thinking":
                        thinking_parts.append(getattr(block, "thinking", ""))
                    else:
                        text_parts.append(getattr(block, "text", ""))
                # Reconstruct in same format as LiteLLM sync calls so that
                # separate_thinking_from_response() can parse <think> tags.
                thinking_str = "\n".join(thinking_parts)
                text_str = "\n".join(text_parts)
                if thinking_str:
                    text = f"<think>\n{thinking_str}\n</think>\n{text_str}"
                else:
                    text = text_str
            else:
                print(f"  [anthropic-batch] {result.custom_id} failed: "
                      f"{result.result}")
                text = ""
            results_map[result.custom_id] = text

        return [results_map.get(f"req-{i}", "") for i in range(len(list_of_messages))]

    def batch_generate_all_with_thinking_anthropic(
        self, list_of_messages: list[list[dict[str, str]]]
    ) -> tuple[list[str], list[str]]:
        """Anthropic Batch API variant that also extracts thinking traces."""
        responses = self.batch_generate_all_anthropic(list_of_messages)
        texts, thinking_traces = [], []
        for response in responses:
            parts = separate_thinking_from_response(response)
            texts.append(parts["response"])
            thinking_traces.append(parts["thinking"])
        return texts, thinking_traces
