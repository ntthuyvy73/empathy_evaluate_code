"""Integration test for ``generate_judgments.py`` graceful-stop behavior (Task 7.2).

This test exercises the *wiring* of the Session Capacity Monitor into the
Mind-Eval judgment generator's standard chunked sync path. Per the design's
*Testing Strategy > Unit / example tests* (R5.1 / R5.2), it uses a **fake
monitor** that returns STOP after ``N`` batches and asserts:

  (a) the judge model is NOT invoked for batch ``N+1`` (its per-batch call count
      equals exactly ``N``), and
  (b) the output file contains exactly the judgments completed in batches
      ``1..N`` (no more, no fewer), and
  (c) the human-facing stop message is printed.

The judge model (``InferenceEngine``) and the monitor factory
(``SessionCapacityMonitor.from_config``) are both replaced with in-memory fakes
so no network call or real model invocation ever happens. A tiny real temp
interactions JSONL drives ``main`` end-to-end through the chunked loop.

Validates: Requirements 5.1, 5.2.
"""

import json
from pathlib import Path

import pytest

import mindeval.session_monitor as sm
from mindeval.session_monitor import CapacityDecision
from mindeval.scripts import generate_judgments as gj
from mindeval.utils import load_jsonl


# --- Test doubles -------------------------------------------------------------


class FakeInferenceEngine:
    """Stand-in for ``InferenceEngine`` that counts per-batch invocations.

    ``batch_generate_with_thinking`` returns dummy (judgments, thinking) lists
    matching the size of the submitted batch and increments a call counter so
    the test can assert exactly how many batches were submitted to the judge.
    """

    def __init__(self, api_params):
        self.api_params = api_params
        self.batch_call_count = 0
        self.submitted_batch_sizes = []

    def batch_generate_with_thinking(self, list_of_messages):
        self.batch_call_count += 1
        self.submitted_batch_sizes.append(len(list_of_messages))
        n = len(list_of_messages)
        judgments = [f"judgment for message {i}" for i in range(n)]
        thinking = [f"thinking for message {i}" for i in range(n)]
        return judgments, thinking


_STOP_MESSAGE = "STOP: capacity reached after N batches (fake monitor)."


class FakeMonitor:
    """A fake monitor that allows ``stop_after_n`` batches, then stops.

    ``should_continue`` is called once before each batch. It returns CONTINUE for
    the first ``stop_after_n`` calls and STOP on the next call, mirroring a real
    monitor tripping its threshold just before batch ``N+1``.

    ``enabled`` is ``False`` so the generator does not try to rebuild the monitor
    with a concrete HTTP provider (that rebuild branch is gated on ``enabled``).
    The fake is still consulted on every batch regardless of ``enabled``.
    """

    def __init__(self, stop_after_n):
        self.stop_after_n = stop_after_n
        self.call_count = 0
        self.calls = []  # (completed_count, output_path) per invocation

    @property
    def enabled(self):
        return False

    def should_continue(self, completed_count, output_path):
        self.call_count += 1
        self.calls.append((completed_count, output_path))
        if self.call_count <= self.stop_after_n:
            return CapacityDecision(
                should_continue=True,
                reason="below_threshold",
                usage_percentage=10.0,
                message=None,
            )
        return CapacityDecision(
            should_continue=False,
            reason="at_or_above_threshold",
            usage_percentage=99.0,
            message=_STOP_MESSAGE,
        )


# --- Fixtures / helpers -------------------------------------------------------


def _write_interactions(path: Path, count: int):
    """Write ``count`` interaction records with ids ``rec_0 .. rec_{count-1}``."""
    records = []
    for i in range(count):
        records.append(
            {
                "interaction_id": f"rec_{i}",
                "interaction": [
                    {"role": "client", "content": f"hello from interaction {i}"},
                    {"role": "counselor", "content": f"response to interaction {i}"},
                ],
            }
        )
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def _install_fakes(monkeypatch, fake_engine, fake_monitor):
    """Patch the judge model and the monitor factory used inside ``main``."""
    monkeypatch.setattr(gj, "InferenceEngine", lambda api_params: fake_engine)

    def fake_from_config(judge_name, config_path, *, provider=None):
        return fake_monitor

    # main() imports SessionCapacityMonitor locally from mindeval.session_monitor,
    # so patch the classmethod on that class for the local import to pick it up.
    monkeypatch.setattr(sm.SessionCapacityMonitor, "from_config", fake_from_config)


# --- Tests --------------------------------------------------------------------


@pytest.mark.parametrize(
    "total, max_workers, stop_after_n",
    [
        (5, 1, 3),  # batch size 1: stop before batch 4 → 3 records
        (8, 2, 2),  # batch size 2: stop before batch 3 → 4 records
    ],
)
def test_stop_after_n_batches_halts_before_next_batch(
    tmp_path, monkeypatch, capsys, total, max_workers, stop_after_n
):
    """Judge stops at batch N+1 and the output holds exactly batches 1..N.

    Validates: Requirements 5.1, 5.2.
    """
    interactions_path = tmp_path / "interactions.jsonl"
    output_path = tmp_path / "judgments.jsonl"
    _write_interactions(interactions_path, total)

    fake_engine = FakeInferenceEngine({"model": "fake-model"})
    fake_monitor = FakeMonitor(stop_after_n=stop_after_n)
    _install_fakes(monkeypatch, fake_engine, fake_monitor)

    gj.main(
        interactions_path=str(interactions_path),
        max_workers=max_workers,
        output_path=str(output_path),
        judge_model_api_params={"model": "fake-model"},
        judge_name="claude_9router",
        judge_template_version="v0_1",
        skip_existing=True,
    )

    # (a) The judge model was invoked exactly N times — never for batch N+1.
    assert fake_engine.batch_call_count == stop_after_n
    assert fake_engine.submitted_batch_sizes == [max_workers] * stop_after_n

    # The monitor was consulted once more than it allowed (the STOP check).
    assert fake_monitor.call_count == stop_after_n + 1

    # (b) The output file holds exactly the judgments from batches 1..N.
    expected_record_count = stop_after_n * max_workers
    outputs = load_jsonl(str(output_path))
    assert len(outputs) == expected_record_count

    expected_ids = [f"rec_{i}" for i in range(expected_record_count)]
    assert [o["interaction_id"] for o in outputs] == expected_ids

    # (c) The graceful-stop message was printed to the user.
    captured = capsys.readouterr()
    assert _STOP_MESSAGE in captured.out


def test_no_stop_processes_all_batches(tmp_path, monkeypatch, capsys):
    """Sanity check: when the monitor never stops, every batch is processed.

    This guards against the stop logic firing spuriously and confirms the fake
    wiring matches the real generator's loop. With ``stop_after_n`` larger than
    the number of batches, all interactions are judged and no stop message is
    printed.

    Validates: Requirements 5.1, 5.2.
    """
    total, max_workers = 4, 1
    interactions_path = tmp_path / "interactions.jsonl"
    output_path = tmp_path / "judgments.jsonl"
    _write_interactions(interactions_path, total)

    fake_engine = FakeInferenceEngine({"model": "fake-model"})
    fake_monitor = FakeMonitor(stop_after_n=999)  # effectively never stops
    _install_fakes(monkeypatch, fake_engine, fake_monitor)

    gj.main(
        interactions_path=str(interactions_path),
        max_workers=max_workers,
        output_path=str(output_path),
        judge_model_api_params={"model": "fake-model"},
        judge_name="claude_9router",
        judge_template_version="v0_1",
        skip_existing=True,
    )

    assert fake_engine.batch_call_count == total
    outputs = load_jsonl(str(output_path))
    assert len(outputs) == total
    assert [o["interaction_id"] for o in outputs] == [f"rec_{i}" for i in range(total)]

    captured = capsys.readouterr()
    assert _STOP_MESSAGE not in captured.out
