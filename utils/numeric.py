"""Generic numeric helpers used by report generators."""

from typing import Any, Dict, List

import numpy as np

from config import config


def safe_get(data: Dict, key: str, default: Any = None) -> Any:
    return data.get(key, default) if data else default


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    return numerator / denominator if denominator != 0 else default


def format_number(value: Any, decimals: int = 0, thousands_sep: bool = True) -> str:
    if not isinstance(value, (int, float)) or value is None:
        return "N/A"
    fmt = f"{{:,.{decimals}f}}" if thousands_sep else f"{{:.{decimals}f}}"
    return fmt.format(value)


def calculate_statistics(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"mean": 0, "std": 0, "cv": 0, "min": 0, "max": 0}
    arr = np.array(values)
    mean_val = float(np.mean(arr))
    std_val = float(np.std(arr))
    return {
        "mean": mean_val,
        "std": std_val,
        "cv": safe_divide(std_val, mean_val),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


def assess_balance_quality(cv: float) -> str:
    t = config.tool_defaults.territory_report.balance_thresholds
    if cv < t.excellent:
        return "Excellent"
    if cv < t.good:
        return "Good"
    if cv < t.acceptable:
        return "Acceptable"
    return "Needs Improvement"