from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from compras_divididas.application.use_cases.close_month import (
    CloseMonthRequest,
    CloseMonthUseCase,
)


@dataclass(frozen=True, slots=True)
class BenchmarkOutcome:
    name: str
    runs: int
    p95_seconds: float


def _golden_dataset_path() -> Path:
    return (
        Path(__file__).resolve().parent.parent
        / "fixtures"
        / "golden"
        / "monthly_closure_dataset.json"
    )


def _load_targets() -> dict[str, float]:
    payload = json.loads(_golden_dataset_path().read_text(encoding="utf-8"))
    targets = payload["performance_targets_seconds"]
    if not isinstance(targets, dict):
        raise AssertionError("Golden dataset targets must be an object")
    return {key: float(value) for key, value in targets.items()}


def _build_payload(message_count: int) -> dict[str, object]:
    messages: list[dict[str, str]] = []
    for index in range(message_count):
        author_external_id = "elias" if index % 2 == 0 else "esposa"
        author_display_name = "Elias" if index % 2 == 0 else "Esposa"
        amount_brl = 20 + (index % 13)
        sent_at = f"2026-02-{(index % 28) + 1:02d}T12:{index % 60:02d}:00-03:00"
        messages.append(
            {
                "message_id": f"m-{index:04d}",
                "author_external_id": author_external_id,
                "author_display_name": author_display_name,
                "content": f"Mercado item {index} R${amount_brl}",
                "sent_at": sent_at,
            }
        )

    return {
        "period": {"year": 2026, "month": 2},
        "participants": [
            {"external_id": "elias", "display_name": "Elias"},
            {"external_id": "esposa", "display_name": "Esposa"},
        ],
        "messages": messages,
        "source": "manual_copy",
        "reprocess_mode": "new_version",
    }


def _run_benchmark(
    name: str, request: CloseMonthRequest, runs: int
) -> BenchmarkOutcome:
    durations: list[float] = []
    for _ in range(runs):
        start = perf_counter()
        CloseMonthUseCase().execute(request)
        durations.append(perf_counter() - start)

    return BenchmarkOutcome(
        name=name,
        runs=runs,
        p95_seconds=_p95(durations),
    )


def _p95(samples: list[float]) -> float:
    if not samples:
        raise ValueError("p95 requires at least one sample")
    ordered = sorted(samples)
    index = max(0, (len(ordered) * 95 + 99) // 100 - 1)
    return ordered[index]


def _assert_target(outcome: BenchmarkOutcome, target_seconds: float) -> None:
    assert outcome.p95_seconds <= target_seconds, (
        f"{outcome.name} p95 {outcome.p95_seconds:.3f}s exceeds target "
        f"{target_seconds:.3f}s across {outcome.runs} runs"
    )


def test_reconciliation_benchmark_d100() -> None:
    targets = _load_targets()
    request = CloseMonthRequest.model_validate(_build_payload(message_count=100))
    outcome = _run_benchmark("d100", request, runs=7)
    _assert_target(outcome, targets["d100"])


def test_reconciliation_benchmark_d500() -> None:
    targets = _load_targets()
    request = CloseMonthRequest.model_validate(_build_payload(message_count=500))
    outcome = _run_benchmark("d500", request, runs=5)
    _assert_target(outcome, targets["d500"])


def test_reconciliation_benchmark_d2000() -> None:
    targets = _load_targets()
    request = CloseMonthRequest.model_validate(_build_payload(message_count=2000))
    outcome = _run_benchmark("d2000", request, runs=3)
    _assert_target(outcome, targets["d2000"])


def test_reconciliation_benchmark_reprocess_50() -> None:
    targets = _load_targets()
    baseline_payload = _build_payload(message_count=500)
    baseline_request = CloseMonthRequest.model_validate(baseline_payload)
    CloseMonthUseCase().execute(baseline_request)

    updated_payload = _build_payload(message_count=500)
    messages = updated_payload["messages"]
    if not isinstance(messages, list):
        raise AssertionError("Generated payload messages must be a list")

    for index in range(50):
        messages[index]["content"] = f"Mercado atualizado {index} R${35 + (index % 7)}"

    updated_request = CloseMonthRequest.model_validate(updated_payload)
    outcome = _run_benchmark("reprocess_50", updated_request, runs=5)
    _assert_target(outcome, targets["reprocess_50"])
