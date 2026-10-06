"""Integration test for ``generate_wai_judgments.py`` graceful-stop behavior (Task 8.2).

This test exercises the *wiring* of the Session Capacity Monitor into the WAI
judgment generator's standard per-dialogue sync path. Per the design's
*Testing Strategy > Unit / example tests* (R5.1 / R5.2), it uses a **fake
monitor** that returns STOP after ``N`` dialogues and asserts:

  (a) the per-dialogue evaluation (``evaluate_dialogue``) is NOT invoked for
      dialogue ``N+1`` (its call count equals exactly ``N``), and
  (b) the output file contains exactly the judgments for dialogues ``1..N``
      (no more, no fewer), and
  (c) the human-facing stop message is printed.

The judge model (``InferenceEngine``), the per-dialogue evaluator
(``evaluate_dialogue``), and the monitor factory
(``SessionCapacityMonitor.from_config``) are all replaced with in-memory fakes
so no network call or real model invocation ever happens. A tiny real temp
interactions JSONL plus a temp ``config.json`` drive ``main`` end-to-end through
the sync loop.

Validates: Requirements 5.1, 5.2.
"""

import json
from pathlib import Path

import pytest

import mindeval.config as mindeval_config
import mindeval.session_monitor as sm
from mindeval.session_monitor import CapacityDecision
from mindeval.scripts import generate_wai_judgments as gwj
from mindeval.utils import load_jsonl


# --- Test doubles -------------------------------------------------------------


class FakeInferenceEngine:
    """No-op stand-in for ``InferenceEngine`` (constructed from a judge config).

    The real engine opens API clients; the fake records the config it was built
    with and otherwise does nothing. The patched ``evaluate_dialogue`` never
    touches it, so no model call is ever made.
    """

    def __init__(self, judge_config):
        self.judge_config = judge_config


class FakeDialogueEvaluator:
    """Counts ``evaluate_dialogue`` calls and returns a minimal valid result.

    Each call increments ``call_count`` and returns a result dict shaped like a
    real WAI judgment (the generator then attaches ``interaction_id`` /
    ``judge_name`` / ``judge_model`` and appends it to the output file).
    """

    def __init__(self):
        self.call_count = 0

    def __call__(self, *args, **kwargs):
        self.call_count += 1
        return {
            "n_runs": 1,
            "questions": {},
            "dimensions": {"Goal": 1, "Approach": 1, "Affective Bond": 1},
            "total": 1,
        }


_STOP_MESSAGE = "STOP: capacity reached after N dialogues (fake monitor)."


class FakeMonitor:
    """A fake monitor that allows ``stop_after_n`` dialogues, then stops.

    ``should_continue`` is called once before each dialogue. It returns CONTINUE
    for the first ``stop_after_n`` calls and STOP on the next call, mirroring a
    real monitor tripping its threshold just before dialogue ``N+1``.

    ``enabled`` is ``False`` so the generator does not try to rebuild the monitor
    with a concrete HTTP provider (that rebuild branch is gated on ``enabled``).
    The fake is still consulted on every dialogue regardless of ``enabled``.
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
    with open(path, "w", encoding="utf-8") as fh:
        for i in range(count):
            record = {
                "interaction_id": f"rec_{i}",
                "interaction": [
                    {"role": "client", "content": f"hello from interaction {i}"},
                    {"role": "counselor", "content": f"response to interaction {i}"},
                ],
            }
            fh.write(json.dumps(record) + "\n")


def _write_config(path: Path, judge_name: str):
    """Write a temp config.json with a named judge (default sync path).

    ``use_anthropic_batch`` is omitted, so it defaults to ``False`` and the
    generator takes the standard per-dialogue sync path that the monitor hooks
    into.
    """
    config = {
        "judges": {
            judge_name: {
                "model": "fake-model",
                "api_key": "test-key",
                "api_base": "http://localhost:0/v1",
                "temperature": 0.3,
            }
        }
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(config, fh)


def _install_fakes(monkeypatch, fake_engine, fake_eval, fake_monitor):
    """Patch the judge model, the per-dialogue evaluator, and the monitor factory."""
    monkeypatch.setattr(gwj, "InferenceEngine", lambda judge_config: fake_engine)
    monkeypatch.setattr(gwj, "evaluate_dialogue", fake_eval)

    def fake_from_config(judge_name, config_path, *, provider=None):
        return fake_monitor

    # main() imports SessionCapacityMonitor locally from mindeval.session_monitor,
    # so patch the classmethod on that class for the local import to pick it up.
    monkeypatch.setattr(sm.SessionCapacityMonitor, "from_config", fake_from_config)

    # The config layer caches a module-level singleton; reset it so the temp
    # config.json is the one actually loaded for this run.
    monkeypatch.setattr(mindeval_config, "_config_manager", None)


# --- Tests --------------------------------------------------------------------


@pytest.mark.parametrize("total, stop_after_n", [(5, 3), (6, 1), (4, 2)])
def test_stop_after_n_dialogues_halts_before_next_dialogue(
    tmp_path, monkeypatch, capsys, total, stop_after_n
):
    """Evaluation stops at dialogue N+1 and the output holds exactly 1..N.

    Validates: Requirements 5.1, 5.2.
    """
    interactions_path = tmp_path / "interactions.jsonl"
    output_path = tmp_path / "wai_judgments.jsonl"
    config_path = tmp_path / "config.json"
    _write_interactions(interactions_path, total)
    _write_config(config_path, judge_name="claude_9router")

    fake_engine = FakeInferenceEngine({"model": "fake-model"})
    fake_eval = FakeDialogueEvaluator()
    fake_monitor = FakeMonitor(stop_after_n=stop_after_n)
    _install_fakes(monkeypatch, fake_engine, fake_eval, fake_monitor)

    gwj.main(
        interactions_path=str(interactions_path),
        output_path=str(output_path),
        config_path=str(config_path),
        judge_name="claude_9router",
        n_runs=1,
        skip_existing=True,
    )

    # (a) The per-dialogue evaluation ran exactly N times — never for dialogue N+1.
    assert fake_eval.call_count == stop_after_n

    # The monitor was consulted once more than it allowed (the STOP check).
    assert fake_monitor.call_count == stop_after_n + 1

    # (b) The output file holds exactly the judgments for dialogues 1..N.
    outputs = load_jsonl(str(output_path))
    assert len(outputs) == stop_after_n
    expected_ids = [f"rec_{i}" for i in range(stop_after_n)]
    assert [o["interaction_id"] for o in outputs] == expected_ids

    # (c) The graceful-stop message was printed to the user.
    captured = capsys.readouterr()
    assert _STOP_MESSAGE in captured.out


def test_no_stop_processes_all_dialogues(tmp_path, monkeypatch, capsys):
    """Sanity check: when the monitor never stops, every dialogue is processed.

    This guards against the stop logic firing spuriously and confirms the fake
    wiring matches the real generator's loop.

    Validates: Requirements 5.1, 5.2.
    """
    total = 4
    interactions_path = tmp_path / "interactions.jsonl"
    output_path = tmp_path / "wai_judgments.jsonl"
    config_path = tmp_path / "config.json"
    _write_interactions(interactions_path, total)
    _write_config(config_path, judge_name="claude_9router")

    fake_engine = FakeInferenceEngine({"model": "fake-model"})
    fake_eval = FakeDialogueEvaluator()
    fake_monitor = FakeMonitor(stop_after_n=999)  # effectively never stops
    _install_fakes(monkeypatch, fake_engine, fake_eval, fake_monitor)

    gwj.main(
        interactions_path=str(interactions_path),
        output_path=str(output_path),
        config_path=str(config_path),
        judge_name="claude_9router",
        n_runs=1,
        skip_existing=True,
    )

    assert fake_eval.call_count == total
    outputs = load_jsonl(str(output_path))
    assert len(outputs) == total
    assert [o["interaction_id"] for o in outputs] == [f"rec_{i}" for i in range(total)]

    captured = capsys.readouterr()
    assert _STOP_MESSAGE not in captured.out
