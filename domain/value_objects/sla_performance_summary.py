"""domain/value_objects/sla_performance_summary.py — SLA performance value object."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SLAPerformanceSummary:
    """Immutable value object summarising SLA performance for a legal process.

    Mirrors the C# ``SLAPerformanceSummary`` value object.

    Attributes:
        provider_name: The name of the legal-process provider/recipient.
        expected_response_days: The contractual SLA window in calendar days.
        actual_response_days: How many days the provider actually took (None if not yet received).
        is_rush_request: Whether this was submitted as an urgent/rush request.
        sla_breach: True when *actual_response_days* > *expected_response_days*.
        days_late: Number of days past the SLA deadline (0 when within SLA).
        performance_rating: Human-readable performance label.
        status: Short status string (``"Pending"``, ``"On Time"``, ``"Breached"``).
    """

    provider_name: str
    expected_response_days: int
    actual_response_days: Optional[int]
    is_rush_request: bool = False
    sla_breach: bool = False
    days_late: int = 0
    performance_rating: str = ""
    status: str = "Pending"

    # ------------------------------------------------------------------ #
    # Factory                                                              #
    # ------------------------------------------------------------------ #

    @classmethod
    def calculate(
        cls,
        provider_name: str,
        expected_response_days: int,
        actual_response_days: Optional[int],
        is_rush_request: bool = False,
    ) -> "SLAPerformanceSummary":
        """Compute all derived fields and return an immutable summary."""
        if actual_response_days is None:
            return cls(
                provider_name=provider_name,
                expected_response_days=expected_response_days,
                actual_response_days=None,
                is_rush_request=is_rush_request,
                sla_breach=False,
                days_late=0,
                performance_rating="Pending",
                status="Pending",
            )

        breach = actual_response_days > expected_response_days
        days_late = max(actual_response_days - expected_response_days, 0)

        if not breach:
            ratio = actual_response_days / max(expected_response_days, 1)
            if ratio <= 0.5:
                rating = "Excellent"
            elif ratio <= 0.8:
                rating = "Good"
            else:
                rating = "Acceptable"
            status = "On Time"
        else:
            if days_late <= 2:
                rating = "Slightly Late"
            elif days_late <= 7:
                rating = "Late"
            else:
                rating = "Significantly Late"
            status = "Breached"

        return cls(
            provider_name=provider_name,
            expected_response_days=expected_response_days,
            actual_response_days=actual_response_days,
            is_rush_request=is_rush_request,
            sla_breach=breach,
            days_late=days_late,
            performance_rating=rating,
            status=status,
        )

    # ------------------------------------------------------------------ #
    # Display                                                              #
    # ------------------------------------------------------------------ #

    def get_formatted_report(self) -> str:
        """Return a multi-line human-readable performance report."""
        lines = [
            f"Provider:         {self.provider_name}",
            f"Expected (days):  {self.expected_response_days}",
            f"Actual (days):    {self.actual_response_days if self.actual_response_days is not None else 'N/A'}",
            f"Rush request:     {'Yes' if self.is_rush_request else 'No'}",
            f"Status:           {self.status}",
            f"Performance:      {self.performance_rating}",
        ]
        if self.sla_breach:
            lines.append(f"Days late:        {self.days_late}")
        return "\n".join(lines)
