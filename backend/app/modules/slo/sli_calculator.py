"""Service Level Indicator (SLI) and Error Budget calculation."""

from __future__ import annotations


def compute_sli_and_budget(
    target_percentage: float,
    total_events: int,
    good_events: int,
) -> tuple[float, float, bool, float]:
    """Compute current SLI percentage, remaining error budget percentage, and burn rate.

    Returns:
        (current_sli, error_budget_remaining, has_sufficient_data, burn_rate)
    """
    if total_events <= 0:
        # Missing telemetry != health: marked as insufficient data
        return 100.0, 100.0, False, 0.0

    bounded_good = max(0, min(good_events, total_events))
    bad_events = total_events - bounded_good

    current_sli = (bounded_good / total_events) * 100.0
    allowed_bad_pct = 100.0 - target_percentage

    if allowed_bad_pct <= 0:
        budget_remaining = 100.0 if bad_events == 0 else 0.0
        burn_rate = 1.0 if bad_events == 0 else 10.0
    else:
        actual_bad_pct = (bad_events / total_events) * 100.0
        burn_rate = actual_bad_pct / allowed_bad_pct
        budget_remaining = max(0.0, (1.0 - (actual_bad_pct / allowed_bad_pct)) * 100.0)

    return (
        round(current_sli, 3),
        round(budget_remaining, 2),
        True,
        round(burn_rate, 2),
    )
