"""R164-R168 paired-result analysis for Copernican experiments.

Primary analysis retains every valid preregistered seed with matched operation
budgets. CPU-ratio filtering is secondary diagnostics only; it must not replace
the primary estimate. Sealed outcomes must never influence eligibility.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
from collections.abc import Mapping, Sequence
from typing import Any


PROTOCOL = "TW_R164_PAIRED_PRIMARY_ALL_SEEDS_V1"


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _paired_delta(record: Mapping[str, Any], metric: str) -> float:
    if metric not in ("transfer_pp", "retention_pp"):
        raise ValueError(f"unsupported metric: {metric}")
    value = record.get(metric)
    if not _finite_number(value):
        raise ValueError(f"missing/non-finite {metric}")
    return float(value)


def _bootstrap_ci(values: Sequence[float], *, seed: int, draws: int = 4000) -> dict[str, float | int | None]:
    """Percentile bootstrap CI over paired per-seed deltas, with fixed RNG seed."""
    if not values:
        return {"n": 0, "mean": None, "low_95": None, "high_95": None}
    if draws < 100:
        raise ValueError("draws must be >= 100")
    rng = random.Random(seed)
    n = len(values)
    means = [
        statistics.fmean(values[rng.randrange(n)] for _ in range(n))
        for _ in range(draws)
    ]
    means.sort()
    return {
        "n": n,
        "mean": statistics.fmean(values),
        "low_95": means[int(0.025 * (draws - 1))],
        "high_95": means[int(0.975 * (draws - 1))],
    }


def summarize_paired(
    records: Sequence[Mapping[str, Any]],
    *,
    cpu_tolerance: float = 0.10,
    bootstrap_draws: int = 4000,
    bootstrap_seed: int = 164168,
) -> dict[str, Any]:
    """Summarize a preregistered paired experiment without post-hoc primary filtering.

    Each record must contain a unique seed, equal update/probe counts, transfer
    and retention paired deltas, and a CPU ratio. Invalid/ineligible records are
    retained in the output ledger with explicit reasons, never silently dropped.
    """
    if not 0 <= cpu_tolerance <= 1:
        raise ValueError("cpu_tolerance must be in [0, 1]")
    seen: set[int] = set()
    eligible: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []

    for raw in records:
        row = dict(raw)
        seed = row.get("seed")
        reasons: list[str] = []
        if not isinstance(seed, int) or isinstance(seed, bool):
            reasons.append("INVALID_SEED")
        elif seed in seen:
            reasons.append("DUPLICATE_SEED")
        else:
            seen.add(seed)

        updates = row.get("comparable_updates")
        probes = row.get("comparable_probes")
        if not isinstance(updates, int) or isinstance(updates, bool) or updates <= 0:
            reasons.append("INVALID_UPDATE_BUDGET")
        if not isinstance(probes, int) or isinstance(probes, bool) or probes <= 0:
            reasons.append("INVALID_PROBE_BUDGET")
        if row.get("budget_operations_equal") is not True:
            reasons.append("OPERATION_BUDGET_MISMATCH")

        for metric in ("transfer_pp", "retention_pp"):
            if not _finite_number(row.get(metric)):
                reasons.append(f"INVALID_{metric.upper()}")

        cpu_ratio = row.get("cpu_ratio_inherit_to_reset")
        cpu_known = _finite_number(cpu_ratio) and float(cpu_ratio) > 0
        cpu_fair = cpu_known and (1 - cpu_tolerance <= float(cpu_ratio) <= 1 + cpu_tolerance)

        # This flag is explicitly forbidden from determining primary eligibility.
        row["cpu_ratio_known"] = bool(cpu_known)
        row["cpu_fair_secondary"] = bool(cpu_fair)
        row["eligibility_reasons"] = reasons
        row["primary_eligible"] = not reasons
        ledger.append(row)
        if not reasons:
            eligible.append(row)

    transfer = [float(r["transfer_pp"]) for r in eligible]
    retention = [float(r["retention_pp"]) for r in eligible]
    cpu_fair_rows = [r for r in eligible if r["cpu_fair_secondary"]]

    def fair_summary(metric: str) -> dict[str, Any]:
        vals = [float(r[metric]) for r in cpu_fair_rows]
        return {
            "n": len(vals),
            "mean": statistics.fmean(vals) if vals else None,
            "scope": "SECONDARY_DIAGNOSTIC_ONLY_NOT_PRIMARY_ESTIMATE",
        }

    def canonicalize(value):
        if isinstance(value, float) and not math.isfinite(value):
            return "NON_FINITE"
        if isinstance(value, dict):
            return {str(k): canonicalize(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [canonicalize(v) for v in value]
        return value

    canonical = json.dumps(
        canonicalize(ledger), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return {
        "protocol": PROTOCOL,
        "input_records": len(records),
        "primary_eligible_seeds": len(eligible),
        "primary_excluded_records": len(records) - len(eligible),
        "primary_transfer_pp": _bootstrap_ci(transfer, seed=bootstrap_seed, draws=bootstrap_draws),
        "primary_retention_pp": _bootstrap_ci(retention, seed=bootstrap_seed + 1, draws=bootstrap_draws),
        "cpu_fair_pairs": len(cpu_fair_rows),
        "cpu_mismatched_or_unknown_pairs": len(eligible) - len(cpu_fair_rows),
        "cpu_fair_transfer_secondary": fair_summary("transfer_pp"),
        "cpu_fair_retention_secondary": fair_summary("retention_pp"),
        "positive_transfer_seed_count": sum(x > 0 for x in transfer),
        "positive_retention_seed_count": sum(x > 0 for x in retention),
        "ledger_sha256": hashlib.sha256(canonical).hexdigest(),
        "sealed_outcomes_used_for_eligibility": False,
        "certified_ais": 0,
        "mother_promotion": "LOCKED",
        "limitations": [
            "CPU-ratio filtering is secondary and must not replace the primary all-eligible-seed estimate.",
            "Observed CPU ratios do not constitute a hard equal-CPU budget.",
            "End RSS is not peak RSS; no energy/GPU measurement is implied.",
            "Operation-budget equality must be explicitly true; missing/unknown values fail closed.",
            "Bootstrap intervals quantify seed-level variability only and do not establish general intelligence.",
        ],
        "records": ledger,
    }
